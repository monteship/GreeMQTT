import os
from loguru import logger

import time
import threading

from dotenv import load_dotenv

from device import search_devices
from mqtt_handler import handle_set_params, handle_get_params
import paho.mqtt.client as mqtt

# Load environment variables
load_dotenv()
NETWORK = os.getenv("NETWORK").split(",")
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "gree")
# Configure loguru
logger.add("logs/app.log", rotation="1 MB", retention="7 days", level="INFO")
# Initialize MQTT client
mqtt_client = mqtt.Client(client_id="gree_mqtt_client", callback_api_version=2)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)

if __name__ == "__main__":
    threads = []
    for device_ip in NETWORK:
        device = search_devices(device_ip)
        if device:
            logger.info(f"Device found: {device}")
            # Start a thread for periodic updates
            thread = threading.Thread(
                target=handle_get_params, args=(device, mqtt_client, MQTT_TOPIC)
            )
            thread.daemon = True
            threads.append(thread)
            thread.start()

            # Start a thread to handle set_params
            set_thread = threading.Thread(
                target=handle_set_params, args=(device, mqtt_client, MQTT_TOPIC)
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
