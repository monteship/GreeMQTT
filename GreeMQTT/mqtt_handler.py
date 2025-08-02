import asyncio
import json
import traceback
from functools import wraps
from typing import Callable
import time

from aiomqtt import Client

from GreeMQTT.adaptive_polling_manager import AdaptivePollingManager
from GreeMQTT.config import (
    MQTT_QOS,
    MQTT_RETAIN,
    ADAPTIVE_POLLING_TIMEOUT,
    ADAPTIVE_FAST_INTERVAL,
    MQTT_MESSAGE_WORKERS,
    IMMEDIATE_RESPONSE_TIMEOUT,
)
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_registry import DeviceRegistry
from GreeMQTT.logger import log

device_registry = DeviceRegistry()
adaptive_polling_manager = AdaptivePollingManager(
    ADAPTIVE_POLLING_TIMEOUT, ADAPTIVE_FAST_INTERVAL
)

# Enhanced message processing queue with priority for better responsiveness
message_queue = asyncio.Queue(maxsize=100)  # Prevent memory issues with backlog
processing_tasks = set()
performance_metrics = {
    "messages_processed": 0,
    "average_processing_time": 0.0,
    "last_reset": time.time(),
}


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


async def update_performance_metrics(processing_time: float):
    """Update performance metrics for monitoring."""
    global performance_metrics

    performance_metrics["messages_processed"] += 1

    # Calculate rolling average processing time
    if performance_metrics["messages_processed"] == 1:
        performance_metrics["average_processing_time"] = processing_time
    else:
        # Exponential moving average with alpha = 0.1
        alpha = 0.1
        performance_metrics["average_processing_time"] = (
            alpha * processing_time +
            (1 - alpha) * performance_metrics["average_processing_time"]
        )

    # Reset metrics every hour to prevent overflow
    current_time = time.time()
    if current_time - performance_metrics["last_reset"] > 3600:
        performance_metrics["messages_processed"] = 0
        performance_metrics["average_processing_time"] = 0.0
        performance_metrics["last_reset"] = current_time


async def process_single_message(message, mqtt_client: Client):
    """Process a single MQTT message with immediate response publishing and performance tracking."""
    device = device_registry.get(str(message.topic))
    if not device:
        log.debug("Unknown topic", topic=str(message.topic))
        return

    try:
        params = json.loads(message.payload.decode("utf-8"))

        # Record start time for performance monitoring
        start_time = time.time()

        # Set parameters on device
        response = await device.set_params(params)

        # Trigger adaptive polling immediately for ultra-fast response
        await adaptive_polling_manager.trigger_adaptive_polling(device.device_id)

        # Force immediate polling for critical responsiveness
        await adaptive_polling_manager.force_immediate_polling(
            device.device_id, IMMEDIATE_RESPONSE_TIMEOUT
        )

        # Immediately publish updated device state for faster feedback
        current_params = await device.get_param()
        if current_params:
            params_str = json.dumps(current_params, separators=(",", ":"))
            await mqtt_client.publish(
                device.topic, params_str, qos=MQTT_QOS, retain=MQTT_RETAIN
            )

        processing_time = time.time() - start_time
        await update_performance_metrics(processing_time)

        log.debug(
            "Set parameters for device",
            device_id=device.device_id,
            opt=response.get("opt"),
            p=response.get("p"),
            val=response.get("val"),
            r=response.get("r"),
            processing_time_ms=round(processing_time * 1000, 2),
            avg_processing_time_ms=round(performance_metrics["average_processing_time"] * 1000, 2),
        )
        log.info("Set params for topic", topic=str(message.topic))

    except json.JSONDecodeError:
        log.error("Invalid JSON", topic=str(message.topic), payload=message.payload)
    except Exception as e:
        log.error("Error processing message", topic=str(message.topic), error=str(e))


async def message_processor_worker(mqtt_client: Client, stop_event: asyncio.Event):
    """Worker that processes messages from the queue concurrently."""
    while not stop_event.is_set():
        try:
            # Wait for message with timeout to allow periodic stop_event checking
            message = await asyncio.wait_for(message_queue.get(), timeout=1.0)

            # Process message in a separate task for concurrency
            task = asyncio.create_task(process_single_message(message, mqtt_client))
            processing_tasks.add(task)

            # Clean up completed tasks
            processing_tasks.discard(task)

            # Mark message as processed
            message_queue.task_done()

        except asyncio.TimeoutError:
            # Normal timeout, continue checking stop_event
            continue
        except Exception as e:
            log.error("Error in message processor worker", error=str(e))


@async_safe_handle
@with_retries()
async def set_params(mqtt_client: Client, stop_event: asyncio.Event):
    """Enhanced message handling with concurrent processing and immediate responses."""

    # Use configurable number of workers for concurrent message processing
    num_workers = MQTT_MESSAGE_WORKERS
    workers = []
    for i in range(num_workers):
        worker = asyncio.create_task(
            message_processor_worker(mqtt_client, stop_event)
        )
        workers.append(worker)

    log.info(f"Started {num_workers} message processor workers for enhanced responsiveness")

    try:
        async for message in mqtt_client.messages:
            if stop_event.is_set():
                break

            # Add message to queue for processing with non-blocking put
            try:
                message_queue.put_nowait(message)
            except asyncio.QueueFull:
                log.warning("Message queue full, dropping oldest message")
                # Remove oldest message and add new one
                try:
                    message_queue.get_nowait()
                    message_queue.put_nowait(message)
                except asyncio.QueueEmpty:
                    pass

    finally:
        # Clean up workers
        log.info("Shutting down message processor workers")
        for worker in workers:
            worker.cancel()

        # Wait for any remaining processing tasks to complete
        if processing_tasks:
            await asyncio.gather(*processing_tasks, return_exceptions=True)


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
        try:
            polling_interval = await adaptive_polling_manager.get_polling_interval(
                device.device_id
            )

            # Use shorter polling when adaptive polling is active
            if await adaptive_polling_manager.is_adaptive_polling_active(device.device_id):
                # Even faster polling during first few seconds of adaptive mode
                elapsed_time = time.time() - (adaptive_polling_manager._device_states.get(device.device_id, 0))
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

            await asyncio.sleep(polling_interval)

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
            await asyncio.sleep(error_delay)
