# mqtt_handler.py
from loguru import logger
import json
import time
from device import set_params, get_param

logger.add("logs/app.log", rotation="1 MB", retention="7 days", level="INFO")


def handle_set_params(device, mqtt_client, mqtt_topic):
    """Subscribe to the set topic and handle incoming messages to set parameters."""

    def on_message(client, userdata, msg):
        logger.info(f"Received message on topic {msg.topic}: {msg.payload}")
        try:
            params = json.loads(msg.payload.decode("utf-8"))
            set_params(device, params)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON received on topic {msg.topic}: {msg.payload}")

    set_topic = f"{mqtt_topic}/{device.device_id}/set"
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


def handle_get_params(device, mqtt_client, mqtt_topic, interval):
    """Periodically fetch and publish device parameters."""
    params_topic = f"{mqtt_topic}/{device.device_id}"
    logger.info(f"Publishing device parameters to topic {params_topic}.")
    while True:
        params = get_param(device)
        if params:
            params = json.dumps(params)
            mqtt_client.publish(params_topic, params)
            logger.info(f"Published {params_topic}: {params.replace(' ', '')}")
        else:
            logger.error(f"Failed to get parameters from device {device.device_id}.")
        time.sleep(interval)
