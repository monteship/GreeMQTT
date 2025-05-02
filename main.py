import threading
import time

import paho.mqtt.client as mqtt
from loguru import logger

from config import MQTT_BROKER, MQTT_PASSWORD, MQTT_PORT, MQTT_USER, NETWORK
from device import search_devices
from mqtt_handler import handle_get_params, handle_set_params

from typing import Callable, Tuple, List

# Initialize MQTT client
mqtt_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="gree_mqtt_client",
)
if MQTT_USER and MQTT_PASSWORD:
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()


def run_thread(target: Callable, args: Tuple):
    """
    Run a function in a separate thread.
    :param target:
    :param args:
    :return:
    """
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    return thread


if __name__ == "__main__":
    threads: List[threading.Thread,] = []
    stop_event = threading.Event()

    for device_ip in NETWORK:
        d = search_devices(device_ip)
        if d:
            logger.info(f"Device found: {d}")
            # Start a thread for periodic updates
            threads.append(
                run_thread(
                    handle_get_params,
                    (d, mqtt_client, stop_event),
                ),
            )

            # Start a thread to handle set_params
            threads.append(
                run_thread(
                    handle_set_params,
                    (d, mqtt_client, stop_event),
                ),
            )

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exiting...")
        stop_event.set()
        for t in threads:
            t.join()
