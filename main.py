import threading
import time

import paho.mqtt.client as mqtt
from loguru import logger

from config import MQTT_BROKER, MQTT_PASSWORD, MQTT_PORT, MQTT_USER, NETWORK
from device import search_devices
from device_db import init_db, get_all_devices, save_device
from device import ScanResult
from managers import DeviceRetryManager, start_device_threads

from typing import List

# Initialize MQTT client
mqtt_client = mqtt.Client(
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
    client_id="gree_mqtt_client",
)
if MQTT_USER and MQTT_PASSWORD:
    mqtt_client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()


if __name__ == "__main__":
    init_db()
    threads: List[threading.Thread,] = []
    stop_event = threading.Event()

    # Load known devices from DB
    known_devices = {
        mac: (ip, key, is_gcm) for mac, ip, key, is_gcm in get_all_devices()
    }
    missing_devices = []

    for device_ip in NETWORK:
        device = False
        # Try to use known device from DB
        for mac, (ip, key, is_gcm) in known_devices.items():
            if ip == device_ip:
                device = ScanResult(
                    (ip, 7000), mac, name="Load from DB", is_GCM=is_gcm == 1
                )
                device.key = key
                logger.info(f"Loaded device from DB: {device}")
                break
        # If not found in DB, search for the device
        if not device:
            device = search_devices(device_ip)
            if device and device.key:
                logger.info(f"Device found: {device}")
                save_device(device.device_id, device.ip, device.key, device.is_GCM)
            else:
                logger.warning(f"Device not found: {device_ip}")
                missing_devices.append(device_ip)
        if device:
            # Start a thread for periodic updates
            threads.extend(start_device_threads(device, mqtt_client, stop_event))

    # Start retry thread
    if missing_devices:
        retry_manager = DeviceRetryManager(
            missing_devices, mqtt_client, stop_event
        )
        retry_manager.start()
        # ...
        retry_manager.join()
    else:
        logger.info("All devices found.")

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Exiting...")
        stop_event.set()
        for t in threads:
            t.join()
