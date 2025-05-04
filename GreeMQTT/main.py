import threading
import time

from GreeMQTT import logger
from GreeMQTT.config import NETWORK
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.device import Device
from GreeMQTT.device_db import device_db
from GreeMQTT.managers import DeviceRetryManager, start_device_threads

from typing import List

mqtt_client = create_mqtt_client()


def main():
    threads: List[threading.Thread,] = []
    stop_event = threading.Event()

    # Load known devices from DB
    known_devices = {
        mac: (ip, key, is_gcm) for mac, ip, key, is_gcm in device_db.get_all_devices()
    }
    missing_devices = []

    for device_ip in NETWORK:
        device = False
        # Try to use known device from DB
        for mac, (ip, key, is_gcm) in known_devices.items():
            if ip == device_ip:
                device = Device(
                    device_ip=ip,
                    device_id=mac,
                    name="Load from DB",
                    is_GCM=is_gcm == 1,
                    key=key,
                )
                logger.info(f"Loaded device from DB: {device}")
                break
        # If not found in DB, search for the device
        if not device:
            device = Device.search_devices(device_ip)
            if device and device.key:
                logger.info(f"Device found: {device}")
                device_db.save_device(
                    device.device_id, device.ip, device.key, device.is_GCM
                )
            else:
                logger.warning(f"Device not found: {device_ip}")
                missing_devices.append(device_ip)
        if device:
            # Start a thread for periodic updates
            threads.extend(start_device_threads(device, mqtt_client, stop_event))

    # Start retry thread
    if missing_devices:
        retry_manager = DeviceRetryManager(missing_devices, mqtt_client, stop_event)
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
