from loguru import logger

import time
import threading


from config import MQTT_USER, MQTT_PASSWORD, MQTT_BROKER, MQTT_PORT, NETWORK
from device import search_devices
from mqtt_handler import handle_set_params, handle_get_params
import paho.mqtt.client as mqtt


def version():
    return open("VERSION", "r").read().strip()


# Configure loguru
logger.add(
    "logs/app.log",
    rotation="1 MB",
    retention="7 days",
    level="INFO",
)

# Initialize MQTT client
mqtt_client = mqtt.Client(
    callback_api_version=2,  # type: ignore
    client_id="gree_mqtt_client",
)
if MQTT_USER and MQTT_PASSWORD:
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()


if __name__ == "__main__":
    logger.info(f"Starting GreeMQTT v{version()}...")
    threads = []
    for device_ip in NETWORK:
        d = search_devices(device_ip)
        if d:
            logger.info(f"Device found: {d}")
            # Start a thread for periodic updates
            thread = threading.Thread(
                target=handle_get_params,
                args=(d, mqtt_client),
            )
            thread.daemon = True
            threads.append(thread)
            thread.start()

            # Start a thread to handle set_params
            set_thread = threading.Thread(
                target=handle_set_params,
                args=(d, mqtt_client),
            )
            set_thread.daemon = True
            threads.append(set_thread)
            set_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exiting...")
