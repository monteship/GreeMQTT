import asyncio
import json
import traceback
from functools import wraps
from typing import Callable
import time

from aiomqtt import Client, Message
from aiomqtt.exceptions import MqttError

from GreeMQTT.adaptive_polling_manager import AdaptivePollingManager
from GreeMQTT.config import (
    MQTT_QOS,
    MQTT_RETAIN,
    ADAPTIVE_POLLING_TIMEOUT,
    ADAPTIVE_FAST_INTERVAL,
    IMMEDIATE_RESPONSE_TIMEOUT,
    UPDATE_INTERVAL,
)
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_registry import DeviceRegistry
from GreeMQTT.logger import log

device_registry = DeviceRegistry()
adaptive_polling_manager = AdaptivePollingManager(
    ADAPTIVE_POLLING_TIMEOUT, ADAPTIVE_FAST_INTERVAL
)


async def interruptible_sleep(duration: float, stop_event: asyncio.Event) -> bool:
    """Sleep that can be interrupted by stop_event. Returns True if interrupted."""
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=duration)
        return True  # Interrupted by stop_event
    except asyncio.TimeoutError:
        return False  # Normal timeout


async def start_device_tasks(
    device: Device,
    mqtt_client,
    stop_event: asyncio.Event,
):
    """
    Start async tasks for handling device parameters with instant callback system.
    """
    asyncio.create_task(device.synchronize_time())
    asyncio.create_task(
        get_params(device, mqtt_client, stop_event, MQTT_QOS, MQTT_RETAIN)
    )
    asyncio.create_task(
        subscribe_with_instant_callback(device, mqtt_client, MQTT_QOS),
    )
    log.info("Started tasks for device with instant callbacks", device=str(device))


async def start_cleanup_task(stop_event: asyncio.Event):
    """
    Start cleanup task for adaptive polling manager.
    """
    asyncio.create_task(cleanup_adaptive_polling_states(stop_event))


async def cleanup_adaptive_polling_states(stop_event: asyncio.Event):
    """
    Periodically clean up expired adaptive polling states.
    """
    while not stop_event.is_set():
        await interruptible_sleep(1, stop_event)
        await adaptive_polling_manager.cleanup_expired_states()


def async_safe_handle(func: Callable) -> Callable:
    """Decorator to safely handle async functions with stop_event and log errors with traceback."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        stop_event = kwargs.get("stop_event") or (args[2] if len(args) > 2 else None)

        # Don't start if already shutting down
        if stop_event and stop_event.is_set():
            log.info(
                "Not starting function, shutdown already requested", func=func.__name__
            )
            return None

        try:
            return await func(*args, **kwargs)
        except (MqttError, ConnectionError, OSError) as e:
            # Don't retry connection errors during shutdown
            if stop_event and stop_event.is_set():
                log.info(
                    "Connection error during shutdown, exiting gracefully",
                    func=func.__name__,
                )
                return None
            else:
                log.error(
                    "Connection error",
                    func=func.__name__,
                    e=e,
                    traceback=traceback.format_exc(),
                )
                raise
        except Exception as e:
            log.error(
                "Error",
                func=func.__name__,
                e=e,
                traceback=traceback.format_exc(),
            )
            # Don't retry during shutdown
            if stop_event and stop_event.is_set():
                log.info(
                    "Error during shutdown, exiting gracefully", func=func.__name__
                )
                return None
            raise
        finally:
            log.info("Exiting gracefully...", func=func.__name__)

    return wrapper


def with_retries(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to add retry logic with exponential backoff to async functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Check if stop_event is provided and if it's set
            stop_event = kwargs.get("stop_event") or (
                args[-1] if len(args) > 0 and hasattr(args[-1], "is_set") else None
            )

            attempt = 0
            current_delay = delay
            while attempt < retries:
                # Don't retry if we're shutting down
                if stop_event and stop_event.is_set():
                    log.info("Shutdown requested, stopping retries", func=func.__name__)
                    return None

                try:
                    return await func(*args, **kwargs)
                except (MqttError, ConnectionError, OSError) as e:
                    # Don't retry MQTT disconnection errors during shutdown
                    if stop_event and stop_event.is_set():
                        log.info(
                            "Shutdown requested during MQTT error, stopping retries",
                            func=func.__name__,
                        )
                        return None

                    attempt += 1
                    if attempt >= retries:
                        log.error(
                            "Retry limit reached for function",
                            func=func.__name__,
                            e=e,
                        )
                        raise
                    log.warning(
                        "Retrying",
                        func=func.__name__,
                        attempt=attempt,
                        delay=current_delay,
                    )
                    if stop_event:
                        interrupted = await interruptible_sleep(
                            current_delay, stop_event
                        )
                        if interrupted:
                            log.info(
                                "Retry sleep interrupted, stopping retries",
                                func=func.__name__,
                            )
                            return None
                    else:
                        await asyncio.sleep(current_delay)
                    current_delay *= backoff
                except Exception as e:
                    attempt += 1
                    if attempt >= retries:
                        log.error(
                            "Retry limit reached for function",
                            func=func.__name__,
                            e=e,
                        )
                        raise
                    log.warning(
                        "Retrying",
                        func=func.__name__,
                        attempt=attempt,
                        delay=current_delay,
                    )
                    if stop_event:
                        interrupted = await interruptible_sleep(
                            current_delay, stop_event
                        )
                        if interrupted:
                            log.info(
                                "Retry sleep interrupted, stopping retries",
                                func=func.__name__,
                            )
                            return None
                    else:
                        await asyncio.sleep(current_delay)
                    current_delay *= backoff
            return None

        return wrapper

    return decorator


@async_safe_handle
@with_retries()
async def get_params(
    device: Device,
    mqtt_client: Client,
    stop_event: asyncio.Event,
    qos: int,
    retain: bool,
):
    """Periodically publishes device parameters to the MQTT topic when they change."""
    params_topic = device.topic
    last_params = None
    consecutive_errors = 0

    def filter_volatile_fields(_params):
        """Remove fields that always change (like timestamps) for comparison."""
        if not isinstance(_params, dict):
            return _params
        filtered = _params.copy()
        # Remove timestamp fields that should not affect change detection
        filtered.pop("last_seen", None)
        return filtered

    while not stop_event.is_set():
        polling_interval = UPDATE_INTERVAL  # Initialize with default value
        try:
            polling_interval = await adaptive_polling_manager.get_polling_interval(
                device.device_id
            )

            # Use shorter polling when adaptive polling is active
            if await adaptive_polling_manager.is_adaptive_polling_active(
                device.device_id
            ):
                # Even faster polling during first few seconds of adaptive mode
                elapsed_time = time.time() - (
                    adaptive_polling_manager._device_states.get(device.device_id, 0)
                )
                if elapsed_time < 10:  # First 10 seconds - ultra-fast polling
                    polling_interval = min(polling_interval, 0.5)

            params = await device.get_param()
            if params:
                # Compare only stable parameters, excluding volatile fields
                params_for_comparison = filter_volatile_fields(params)

                if params_for_comparison != last_params:
                    params_str = json.dumps(params, separators=(",", ":"))
                    await mqtt_client.publish(
                        params_topic, params_str, qos=qos, retain=retain
                    )
                    log.debug(
                        "Publishing params",
                        topic=params_topic,
                        params=params_str,
                        qos=qos,
                        retain=retain,
                    )
                    last_params = params_for_comparison
                    consecutive_errors = 0  # Reset error counter on success

            interrupted = await interruptible_sleep(polling_interval, stop_event)
            if interrupted:
                log.info(
                    "Device parameter polling interrupted during sleep",
                    device_id=device.device_id,
                )
                break

        except Exception as e:
            consecutive_errors += 1
            log.error(
                "Error getting device params",
                device_id=device.device_id,
                error=str(e),
                consecutive_errors=consecutive_errors,
            )

            # Exponential backoff on repeated errors, but cap at normal interval
            error_delay = min(polling_interval, 0.5 * (2 ** min(consecutive_errors, 4)))
            interrupted = await interruptible_sleep(error_delay, stop_event)
            if interrupted:
                log.info(
                    "Device parameter error delay interrupted",
                    device_id=device.device_id,
                )
                break


async def instant_message_handler(message: Message, mqtt_client: Client) -> None:
    """Instant callback handler that processes messages immediately without queuing."""
    start_time = time.time()

    try:
        # Get device immediately
        device = device_registry.get(str(message.topic))
        if not device:
            log.debug("Unknown topic for instant handler", topic=str(message.topic))
            return

        # Parse JSON payload
        params = json.loads(message.payload.decode("utf-8"))

        # Immediately trigger adaptive polling before device communication
        await adaptive_polling_manager.trigger_adaptive_polling(device.device_id)

        # Set parameters with ultra-low latency
        await device.set_params(params)

        # Force immediate polling for instant feedback
        await adaptive_polling_manager.force_immediate_polling(
            device.device_id, IMMEDIATE_RESPONSE_TIMEOUT
        )

        # Get and publish updated state immediately
        current_params = await device.get_param()
        if current_params:
            params_str = json.dumps(current_params, separators=(",", ":"))
            await mqtt_client.publish(
                device.topic, params_str, qos=MQTT_QOS, retain=MQTT_RETAIN
            )

        processing_time = time.time() - start_time

        log.debug(
            "Instant message processed",
            device_id=device.device_id,
            topic=str(message.topic),
            processing_time_ms=round(processing_time * 1000, 2),
        )

    except json.JSONDecodeError:
        log.error(
            "Invalid JSON in instant handler",
            topic=str(message.topic),
            payload=message.payload,
        )
    except Exception as e:
        log.error(
            "Error in instant message handler", topic=str(message.topic), error=str(e)
        )


@async_safe_handle
@with_retries()
async def subscribe_with_instant_callback(
    device: Device, mqtt_client: Client, qos: int
):
    """Enhanced subscription with instant callback registration."""
    set_topic = device.set_topic

    # Subscribe to MQTT topic
    await mqtt_client.subscribe(set_topic, qos=qos)
    device_registry.register(set_topic, device)

    # Start instant message processing for this device
    asyncio.create_task(process_device_messages(device, mqtt_client))

    log.info("Subscribed with instant callback", topic=set_topic, qos=qos)


async def process_device_messages(device: Device, mqtt_client: Client):
    """Process messages for a specific device instantly."""
    try:
        async for message in mqtt_client.messages:
            # Check if message is for this device
            if str(message.topic) == device.set_topic:
                await instant_message_handler(message, mqtt_client)
    except Exception as e:
        log.error(
            "Error processing device messages", device_id=device.device_id, error=str(e)
        )
