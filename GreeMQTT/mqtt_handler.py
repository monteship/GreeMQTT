import json
import threading
import time

import paho.mqtt.client as paho_mqtt

from GreeMQTT.config import settings
from GreeMQTT.device.device import Device
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import subscribe_topic

_device_registry: dict[str, Device] = {}
_device_threads: dict[str, threading.Thread] = {}
_lock = threading.Lock()

KEEP_ALIVE_INTERVAL = 60.0
ERROR_BACKOFF_BASE = 0.5


def _poll_interval(consecutive_errors: int) -> float:
    if consecutive_errors > 0:
        return min(60.0, ERROR_BACKOFF_BASE * (2 ** min(consecutive_errors, 6)))
    return float(settings.update_interval)


def start_device_tasks(device: Device, mqtt_client: paho_mqtt.Client, stop_event: threading.Event):
    threading.Thread(target=device.synchronize_time, daemon=True).start()
    t = threading.Thread(target=_poll_device_params, args=(device, mqtt_client, stop_event), daemon=True)
    t.start()

    with _lock:
        _device_threads[device.device_id] = t
        _device_registry[device.set_topic] = device

    mqtt_client.on_message = _on_mqtt_message
    subscribe_topic(device.set_topic, qos=settings.mqtt_qos)
    log.info("Started tasks for device", device=str(device), topic=device.set_topic)


def is_device_thread_alive(device_id: str) -> bool:
    with _lock:
        t = _device_threads.get(device_id)
        return t is not None and t.is_alive()


def _poll_device_params(device: Device, mqtt_client: paho_mqtt.Client, stop_event: threading.Event):
    last_params: dict | None = None
    last_publish_time: float = 0.0
    consecutive_errors = 0

    while not stop_event.is_set():
        try:
            params = device.get_param()
            if params:
                comparable = {k: v for k, v in params.items() if k != "last_seen"}
                if comparable != last_params or time.time() - last_publish_time >= KEEP_ALIVE_INTERVAL:
                    params_str = json.dumps(params, separators=(",", ":"))
                    mqtt_client.publish(device.topic, params_str, qos=settings.mqtt_qos, retain=settings.mqtt_retain)
                    last_publish_time = time.time()
                    last_params = comparable
                consecutive_errors = 0
            else:
                consecutive_errors += 1
                log.warning("No params from device", device_id=device.device_id, consecutive_errors=consecutive_errors)
        except Exception as e:
            consecutive_errors += 1
            log.error("Error polling device", device_id=device.device_id, error=str(e))

        if stop_event.wait(timeout=_poll_interval(consecutive_errors)):
            break

    with _lock:
        _device_threads.pop(device.device_id, None)
    log.info("Device polling stopped", device_id=device.device_id)


def _on_mqtt_message(client, _userdata, msg) -> None:
    try:
        with _lock:
            device = _device_registry.get(msg.topic)
        if not device:
            log.debug("Unknown topic", topic=msg.topic)
            return

        payload = msg.payload.decode("utf-8").strip()
        if not payload:
            return

        params = json.loads(payload)
        if not isinstance(params, dict):
            log.error("Payload is not a JSON object", topic=msg.topic)
            return

        device.set_params(params)

        current_params = device.get_param()
        if current_params:
            client.publish(device.topic, json.dumps(current_params, separators=(",", ":")),
                           qos=settings.mqtt_qos, retain=settings.mqtt_retain)

        log.debug("Command processed", device_id=device.device_id, topic=msg.topic)

    except json.JSONDecodeError:
        log.error("Invalid JSON", topic=msg.topic, payload=msg.payload)
    except Exception as e:
        log.error("Error handling message", topic=msg.topic, error=str(e))
