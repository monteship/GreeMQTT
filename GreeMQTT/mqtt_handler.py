import threading

from loguru import logger
from functools import wraps

import json
import time

from GreeMQTT.config import MQTT_TOPIC, UPDATE_INTERVAL
from GreeMQTT.device import ScanResult, set_params, get_param

import paho.mqtt.client as mqtt

from typing import Callable


def safe_handle(func: Callable) -> Callable:
    """Decorator to safely handle exceptions in functions."""

    @wraps(func)
    def wrapper(*args, **kwargs) -> None:
        stop_event = args[2] if len(args) > 2 else kwargs.get("stop_event")
        while not (stop_event and stop_event.is_set()):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                time.sleep(1)
        logger.info(f"{func.__name__} stopped due to stop_event.")
        return None

    return wrapper


@safe_handle
def handle_set_params(
    device: ScanResult,
    mqtt_client: mqtt.Client,
    stop_event: threading.Event,
):
    """Subscribe to the set topic and handle incoming messages to set parameters."""

    def on_message(client, userdata, msg):
        logger.info(f"Received message on topic {msg.topic}: {msg.payload}")
        try:
            params = json.loads(msg.payload.decode("utf-8"))
            set_params(device, params)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received on topic {msg.topic}: {msg.payload}")

    set_topic = f"{MQTT_TOPIC}/{device.device_id}/set"
    result, mid = mqtt_client.subscribe(set_topic)
    if result == 0:
        logger.info(f"Successfully subscribed to topic {set_topic}")
        mqtt_client.message_callback_add(set_topic, on_message)
        logger.info(f"Callback added for topic {set_topic}")
    else:
        logger.error(f"Failed to subscribe to topic {set_topic}, result code: {result}")
        return

    while not stop_event.is_set():
        stop_event.wait(0.5)  # Check if the stop event is set


@safe_handle
def handle_get_params(
    device: ScanResult,
    mqtt_client: mqtt.Client,
    stop_event: threading.Event,
):
    """Periodically fetch and publish device parameters."""
    params_topic = f"{MQTT_TOPIC}/{device.device_id}"
    logger.info(f"Publishing device parameters to topic {params_topic}.")
    while not stop_event.is_set():
        params = get_param(device)
        if params:
            params_str = json.dumps(params)
            mqtt_client.publish(params_topic, params_str)
            logger.info(f"{params_topic}: {params_str.replace(' ', '')}")
        else:
            logger.error(f"Failed to get parameters from device {device.device_id}.")
        stop_event.wait(UPDATE_INTERVAL)
