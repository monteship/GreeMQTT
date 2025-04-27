# mqtt_handler.py
from loguru import logger
from functools import wraps

import json
import time

from config import MQTT_TOPIC, UPDATE_INTERVAL
from device import set_params, get_param

logger.add("logs/app.log", rotation="1 MB", retention="7 days", level="INFO")


def safe_handle(func):
    """Decorator to safely handle exceptions in functions."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        while True:  # Keep the thread running
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                time.sleep(1)  # Optional: Add a delay before retrying

    return wrapper


@safe_handle
def handle_set_params(device, mqtt_client):
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

    while True:
        time.sleep(1)  # Keep the thread alive


@safe_handle
def handle_get_params(device, mqtt_client):
    """Periodically fetch and publish device parameters."""
    params_topic = f"{MQTT_TOPIC}/{device.device_id}"
    logger.info(f"Publishing device parameters to topic {params_topic}.")
    while True:
        params = get_param(device)
        if params:
            params["last_seen"] = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime())
            params = json.dumps(params)
            mqtt_client.publish(params_topic, params)
            logger.info(f"{params_topic}: {params.replace(' ', '')}")
        else:
            logger.error(f"Failed to get parameters from device {device.device_id}.")
        time.sleep(UPDATE_INTERVAL)
