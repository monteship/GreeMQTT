import asyncio
import json
import traceback
from functools import wraps
from typing import Callable

from aiomqtt import Client

from GreeMQTT.adaptive_polling_manager import AdaptivePollingManager
from GreeMQTT.config import (
    MQTT_QOS,
    MQTT_RETAIN,
    ADAPTIVE_POLLING_TIMEOUT,
    ADAPTIVE_FAST_INTERVAL,
)
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_registry import DeviceRegistry
from GreeMQTT.logger import log

device_registry = DeviceRegistry()
adaptive_polling_manager = AdaptivePollingManager(
    ADAPTIVE_POLLING_TIMEOUT, ADAPTIVE_FAST_INTERVAL
)


async def start_device_tasks(
    device: Device,
    mqtt_client,
    stop_event: asyncio.Event,
):
    """
    Start async tasks for handling device parameters.
    :param device:
    :param mqtt_client:
    :param stop_event:
    :return:
    """
    asyncio.create_task(device.synchronize_time())
    asyncio.create_task(
        get_params(device, mqtt_client, stop_event, MQTT_QOS, MQTT_RETAIN)
    )
    asyncio.create_task(subscribe(device, mqtt_client, MQTT_QOS))
    log.info("Started tasks for device", device=str(device))


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
        await asyncio.sleep(1)  # Clean up every 5 minutes
        await adaptive_polling_manager.cleanup_expired_states()


def async_safe_handle(func: Callable) -> Callable:
    """Decorator to safely handle async functions with stop_event and log errors with traceback."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        stop_event = kwargs.get("stop_event") or (args[2] if len(args) > 2 else None)
        while not (stop_event and stop_event.is_set()):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                log.error(
                    "Error",
                    func=func.__name__,
                    e=e,
                    traceback=traceback.format_exc(),
                )
                await asyncio.sleep(1)
        log.info("Exiting gracefully...", func=func.__name__)
        return None

    return wrapper


def with_retries(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to add retry logic with exponential backoff to async functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            while attempt < retries:
                try:
                    return await func(*args, **kwargs)
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
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            return None

        return wrapper

    return decorator


@async_safe_handle
@with_retries()
async def subscribe(device: Device, mqtt_client: Client, qos: int):
    set_topic = device.set_topic
    await mqtt_client.subscribe(set_topic, qos=qos)
    device_registry.register(set_topic, device)
    log.info("Subscribed to topic", topic=set_topic, qos=qos)


@async_safe_handle
@with_retries()
async def set_params(mqtt_client: Client, stop_event: asyncio.Event):
    async for message in mqtt_client.messages:
        if stop_event.is_set():
            break
        device = device_registry.get(str(message.topic))
        if not device:
            log.debug("Unknown topic", topic=str(message.topic))
            continue  # Skip unknown topics silently for performance
        try:
            params = json.loads(message.payload.decode("utf-8"))
            response = await device.set_params(params)

            # Trigger adaptive polling when a command is received
            await adaptive_polling_manager.trigger_adaptive_polling(device.device_id)

            log.debug(
                "Set parameters for device",
                device_id=device.device_id,
                opt=response.get("opt"),
                p=response.get("p"),
                val=response.get("val"),
                r=response.get("r"),
            )
            log.info("Set params for topic", topic=str(message.topic))
        except json.JSONDecodeError:
            log.error("Invalid JSON", topic=str(message.topic), payload=message.payload)


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

    def filter_volatile_fields(_params):
        """Remove fields that always change (like timestamps) for comparison."""
        if not isinstance(_params, dict):
            return params
        filtered = _params.copy()
        # Remove timestamp fields that should not affect change detection
        filtered.pop("last_seen", None)
        return filtered

    while not stop_event.is_set():
        polling_interval = await adaptive_polling_manager.get_polling_interval(
            device.device_id
        )
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
        await asyncio.sleep(polling_interval)
