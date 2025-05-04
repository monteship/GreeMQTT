import threading

from loguru import logger
from functools import wraps

import json
import time

from GreeMQTT.config import UPDATE_INTERVAL
from GreeMQTT.device import Device

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
    device: Device,
    mqtt_client: mqtt.Client,
    stop_event: threading.Event,
    qos: int = 0,
):
    """
    Subscribe to the set topic and handle incoming messages to set parameters.

    Args:
        device (Device): The device instance to set parameters for.
        mqtt_client (mqtt.Client): The MQTT client used for communication.
        stop_event (threading.Event): Event to signal when to stop the handler.
        qos (int, optional): Quality of Service level for MQTT message delivery.
            Valid values are:
            - 0: At most once (default).
            - 1: At least once.
            - 2: Exactly once.
    """
    def on_message(client, userdata, msg):
        logger.info(f"Received message on topic {msg.topic}: {msg.payload}")
        try:
            params = json.loads(msg.payload.decode("utf-8"))
            device.set_params(params)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received on topic {msg.topic}: {msg.payload}")

    set_topic = f"{device.topic}/set"

    result, mid = mqtt_client.subscribe(set_topic, qos=qos)
    if result == 0:
        logger.info(f"Successfully subscribed to topic {set_topic} with QoS {qos}")
        mqtt_client.message_callback_add(set_topic, on_message)
        logger.info(f"Callback added for topic {set_topic}")
    else:
        logger.error(f"Failed to subscribe to topic {set_topic}, result code: {result}")
        return

    while not stop_event.is_set():
        stop_event.wait(0.5)  # Check if the stop event is set


@safe_handle
def handle_get_params(
    device: Device,
    mqtt_client: mqtt.Client,
    stop_event: threading.Event,
    qos: int = 0,
):
    """Periodically fetch and publish device parameters."""
    params_topic = device.topic
    logger.info(f"Publishing device parameters to topic {params_topic}.")
    while not stop_event.is_set():
        params = device.get_param()
        if params:
            params_str = json.dumps(params)
            mqtt_client.publish(params_topic, params_str, qos=qos)
            logger.info(f"{params_topic}: {params_str.replace(' ', '')} (QoS {qos})")
        else:
            logger.error(f"Failed to get parameters from device {device.device_id}.")
        stop_event.wait(UPDATE_INTERVAL)
