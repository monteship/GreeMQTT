import json
import threading
import time
import traceback
from functools import wraps
from typing import Callable

import paho.mqtt.client as paho_mqtt

from GreeMQTT.adaptive_polling_manager import AdaptivePollingManager
from GreeMQTT.config import (
    ADAPTIVE_FAST_INTERVAL,
    ADAPTIVE_POLLING_TIMEOUT,
    IMMEDIATE_RESPONSE_TIMEOUT,
    MQTT_QOS,
    MQTT_RETAIN,
    UPDATE_INTERVAL,
)
from GreeMQTT.constants import DEFAULT_RETRY_ATTEMPTS, DEFAULT_RETRY_DELAY, DEFAULT_RETRY_BACKOFF, \
    ERROR_BACKOFF_MAX_ATTEMPTS, ERROR_BACKOFF_BASE_DELAY, CONSECUTIVE_ERROR_RESET_VALUE
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_registry import DeviceRegistry
from GreeMQTT.event_queue import get_event_queue
from GreeMQTT.logger import log

device_registry = DeviceRegistry()
adaptive_polling_manager = AdaptivePollingManager(ADAPTIVE_POLLING_TIMEOUT, ADAPTIVE_FAST_INTERVAL)
event_queue = get_event_queue()


def interruptible_sleep(duration: float, stop_event: threading.Event) -> bool:
    return stop_event.wait(timeout=duration)


def start_device_tasks(
        device: Device,
        mqtt_client: paho_mqtt.Client,
        stop_event: threading.Event,
):
    threading.Thread(target=device.synchronize_time, daemon=True).start()
    threading.Thread(target=get_params, args=(device, mqtt_client, stop_event, MQTT_QOS, MQTT_RETAIN), daemon=True).start()
    subscribe_with_instant_callback(device, mqtt_client, MQTT_QOS)
    log.info("Started tasks for device with instant callbacks", device=str(device))


def start_cleanup_task(stop_event: threading.Event):
    threading.Thread(target=cleanup_adaptive_polling_states, args=(stop_event,), daemon=True).start()


def cleanup_adaptive_polling_states(stop_event: threading.Event):
    while not stop_event.is_set():
        interruptible_sleep(1, stop_event)
        adaptive_polling_manager.cleanup_expired_states()


def log_event_queue_stats(stop_event: threading.Event):
    while not stop_event.is_set():
        interruptible_sleep(60, stop_event)
        if not stop_event.is_set():
            stats = event_queue.get_stats()
            log.info("Event queue statistics", **stats)


def safe_handle(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args, **kwargs):
        stop_event = kwargs.get("stop_event") or (args[2] if len(args) > 2 else None)

        if stop_event and stop_event.is_set():
            log.info("Not starting function, shutdown already requested", func=func.__name__)
            return None

        try:
            return func(*args, **kwargs)
        except (ConnectionError, OSError) as e:
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
            if stop_event and stop_event.is_set():
                log.info("Error during shutdown, exiting gracefully", func=func.__name__)
                return None
            raise
        finally:
            if stop_event and stop_event.is_set():
                log.info("Exiting gracefully...", func=func.__name__)

    return wrapper


def with_retries(retries: int = DEFAULT_RETRY_ATTEMPTS, delay: float = DEFAULT_RETRY_DELAY,
                 backoff: float = DEFAULT_RETRY_BACKOFF):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            stop_event = kwargs.get("stop_event") or (
                args[-1] if len(args) > 0 and hasattr(args[-1], "is_set") else None
            )

            attempt = 0
            current_delay = delay
            while attempt < retries:
                if stop_event and stop_event.is_set():
                    log.info("Shutdown requested, stopping retries", func=func.__name__)
                    return None

                try:
                    return func(*args, **kwargs)
                except (ConnectionError, OSError) as e:
                    if stop_event and stop_event.is_set():
                        log.info(
                            "Shutdown requested during error, stopping retries",
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
                        interrupted = interruptible_sleep(current_delay, stop_event)
                        if interrupted:
                            log.info(
                                "Retry sleep interrupted, stopping retries",
                                func=func.__name__,
                            )
                            return None
                    else:
                        time.sleep(current_delay)
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
                        interrupted = interruptible_sleep(current_delay, stop_event)
                        if interrupted:
                            log.info(
                                "Retry sleep interrupted, stopping retries",
                                func=func.__name__,
                            )
                            return None
                    else:
                        time.sleep(current_delay)
                    current_delay *= backoff
            return None

        return wrapper

    return decorator


@safe_handle
@with_retries()
def get_params(
        device: Device,
        mqtt_client: paho_mqtt.Client,
        stop_event: threading.Event,
        qos: int,
        retain: bool,
):
    params_topic = device.topic
    last_params = None
    consecutive_errors = 0

    def filter_volatile_fields(_params):
        if not isinstance(_params, dict):
            return _params
        filtered = _params.copy()
        filtered.pop("last_seen", None)
        return filtered

    while not stop_event.is_set():
        polling_interval = UPDATE_INTERVAL
        try:
            polling_interval = adaptive_polling_manager.get_polling_interval(device.device_id)

            if adaptive_polling_manager.is_adaptive_polling_active(device.device_id):
                elapsed_time = time.time() - (adaptive_polling_manager._device_states.get(device.device_id, 0))
                if elapsed_time < 10:
                    polling_interval = min(polling_interval, 0.5)

            params = device.get_param()
            if params:
                params_for_comparison = filter_volatile_fields(params)

                if params_for_comparison != last_params:
                    params_str = json.dumps(params, separators=(",", ":"))
                    mqtt_client.publish(params_topic, params_str, qos=qos, retain=retain)
                    log.debug(
                        "Publishing params",
                        topic=params_topic,
                        params=params_str,
                        qos=qos,
                        retain=retain,
                    )
                    last_params = params_for_comparison
                    consecutive_errors = CONSECUTIVE_ERROR_RESET_VALUE

            interrupted = interruptible_sleep(polling_interval, stop_event)
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

            error_delay = min(polling_interval,
                              ERROR_BACKOFF_BASE_DELAY * (2 ** min(consecutive_errors, ERROR_BACKOFF_MAX_ATTEMPTS)))
            interrupted = interruptible_sleep(error_delay, stop_event)
            if interrupted:
                log.info(
                    "Device parameter error delay interrupted",
                    device_id=device.device_id,
                )
                break


def instant_message_handler(client, userdata, msg) -> None:
    start_time = time.time()
    mqtt_client = client

    try:
        device = device_registry.get(msg.topic)
        if not device:
            log.debug("Unknown topic for instant handler", topic=msg.topic)
            return

        params = json.loads(msg.payload.decode("utf-8"))

        adaptive_polling_manager.trigger_adaptive_polling(device.device_id)

        device.set_params(params)

        adaptive_polling_manager.force_immediate_polling(device.device_id, IMMEDIATE_RESPONSE_TIMEOUT)

        current_params = device.get_param()
        if current_params:
            params_str = json.dumps(current_params, separators=(",", ":"))
            mqtt_client.publish(device.topic, params_str, qos=MQTT_QOS, retain=MQTT_RETAIN)

        processing_time = time.time() - start_time

        log.debug(
            "Instant message processed",
            device_id=device.device_id,
            topic=msg.topic,
            processing_time_ms=round(processing_time * 1000, 2),
        )

    except json.JSONDecodeError:
        log.error(
            "Invalid JSON in instant handler",
            topic=msg.topic,
            payload=msg.payload,
        )
    except Exception as e:
        log.error("Error in instant message handler", topic=msg.topic, error=str(e))


def subscribe_with_instant_callback(device: Device, mqtt_client: paho_mqtt.Client, qos: int):
    set_topic = device.set_topic
    mqtt_client.subscribe(set_topic, qos=qos)
    device_registry.register(set_topic, device)
    mqtt_client.on_message = instant_message_handler

    log.info("Subscribed with instant callback", topic=set_topic, qos=qos)

