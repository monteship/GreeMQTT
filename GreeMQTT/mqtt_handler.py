import json
import threading
import time

import paho.mqtt.client as paho_mqtt

from GreeMQTT.adaptive_polling_manager import AdaptivePollingManager
from GreeMQTT.config import settings
from GreeMQTT.device.device import Device
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import subscribe_topic

# Thread-safe device registry
_device_registry: dict[str, Device] = {}
_registry_lock = threading.Lock()

adaptive_polling_manager = AdaptivePollingManager(settings.adaptive_polling_timeout, settings.adaptive_fast_interval)

_on_message_set = False
ERROR_BACKOFF_BASE = 0.5
ERROR_BACKOFF_MAX_EXPONENT = 4


def interruptible_sleep(duration: float, stop_event: threading.Event) -> bool:
    return stop_event.wait(timeout=duration)


def start_device_tasks(
    device: Device,
    mqtt_client: paho_mqtt.Client,
    stop_event: threading.Event,
):
    threading.Thread(target=device.synchronize_time, daemon=True).start()
    threading.Thread(
        target=_poll_device_params,
        args=(device, mqtt_client, stop_event),
        daemon=True,
    ).start()

    set_topic = device.set_topic
    with _registry_lock:
        _device_registry[set_topic] = device

    subscribe_topic(set_topic, qos=settings.mqtt_qos)

    global _on_message_set
    if not _on_message_set:
        mqtt_client.on_message = _on_mqtt_message
        _on_message_set = True

    log.info("Started tasks for device", device=str(device), topic=set_topic)


def start_cleanup_task(stop_event: threading.Event):
    threading.Thread(target=_cleanup_loop, args=(stop_event,), daemon=True).start()


def _cleanup_loop(stop_event: threading.Event):
    while not stop_event.is_set():
        interruptible_sleep(1, stop_event)
        adaptive_polling_manager.cleanup_expired_states()


def _poll_device_params(
    device: Device,
    mqtt_client: paho_mqtt.Client,
    stop_event: threading.Event,
):
    params_topic = device.topic
    last_params: dict | None = None
    last_publish_time: float = 0.0
    consecutive_errors = 0
    keep_alive_interval = 60.0

    while not stop_event.is_set():
        polling_interval = adaptive_polling_manager.get_polling_interval(device.device_id)


        try:
            params = device.get_param()
            if params:
                comparable = {k: v for k, v in params.items() if k != "last_seen"}
                changed = comparable != last_params
                elapsed = time.time() - last_publish_time
                should_publish = changed or elapsed >= keep_alive_interval

                if should_publish:
                    params_str = json.dumps(params, separators=(",", ":"))
                    mqtt_client.publish(params_topic, params_str, qos=settings.mqtt_qos, retain=settings.mqtt_retain)
                    last_publish_time = time.time()
                    if changed:
                        log.debug("Publishing params (changed)", topic=params_topic, params=params_str)
                        last_params = comparable
                    else:
                        log.debug("Publishing params (keep-alive)", topic=params_topic)
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                log.warning("No params returned from device", device_id=device.device_id,
                            consecutive_errors=consecutive_errors)

        except Exception as e:
            consecutive_errors += 1
            log.error("Error getting device params", device_id=device.device_id,
                      error=str(e), consecutive_errors=consecutive_errors)
            error_delay = min(
                polling_interval,
                ERROR_BACKOFF_BASE * (2 ** min(consecutive_errors, ERROR_BACKOFF_MAX_EXPONENT)),
            )
            if interruptible_sleep(error_delay, stop_event):
                break
            continue

        if interruptible_sleep(polling_interval, stop_event):
            log.info("Device polling stopped", device_id=device.device_id)
            break


def _on_mqtt_message(client, userdata, msg) -> None:
    try:
        with _registry_lock:
            device = _device_registry.get(msg.topic)
        if not device:
            log.debug("Unknown topic", topic=msg.topic)
            return

        payload = msg.payload.decode("utf-8").strip()
        if not payload:
            log.debug("Empty payload ignored", topic=msg.topic)
            return

        params = json.loads(payload)
        if not isinstance(params, dict):
            log.error("Payload is not a JSON object", topic=msg.topic)
            return

        adaptive_polling_manager.trigger_adaptive_polling(device.device_id)
        device.set_params(params)
        adaptive_polling_manager.force_immediate_polling(device.device_id, settings.immediate_response_timeout)

        current_params = device.get_param()
        if current_params:
            params_str = json.dumps(current_params, separators=(",", ":"))
            client.publish(device.topic, params_str, qos=settings.mqtt_qos, retain=settings.mqtt_retain)

        log.debug("Command processed", device_id=device.device_id, topic=msg.topic)

    except json.JSONDecodeError:
        log.error("Invalid JSON", topic=msg.topic, payload=msg.payload)
    except Exception as e:
        log.error("Error handling message", topic=msg.topic, error=str(e))
