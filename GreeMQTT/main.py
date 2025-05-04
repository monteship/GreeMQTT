import asyncio

from typing import List

from GreeMQTT import logger
from GreeMQTT.config import NETWORK
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.device import Device
from GreeMQTT.device_db import device_db
from GreeMQTT.managers import DeviceRetryManager, start_device_tasks
from GreeMQTT.mqtt_handler import set_params


async def main():
    stop_event = asyncio.Event()

    # Load known devices from DB
    known_devices: List[Device] = device_db.get_all_devices()
    known_ips = [device.device_ip for device in known_devices]
    missing_devices = [ip for ip in NETWORK if ip not in known_ips]

    async with await create_mqtt_client() as mqtt_client:
        # Start tasks for known devices
        for device in known_devices:
            await start_device_tasks(device, mqtt_client, stop_event)

        # If not found in DB, search for the device
        for device_ip in missing_devices:
            device = await Device.search_devices(device_ip)
            if device and device.key:
                logger.info(f"Device found: {device}")
                device_db.save_device(
                    device.device_id, device.device_ip, device.key, device.is_GCM
                )
                missing_devices.remove(device_ip)
                await start_device_tasks(device, mqtt_client, stop_event)
        # Start retry task
        if missing_devices:
            retry_manager = DeviceRetryManager(missing_devices, mqtt_client, stop_event)
            asyncio.create_task(retry_manager.run())
        else:
            logger.info("All devices found.")

        await asyncio.create_task(set_params(mqtt_client, stop_event))

        # Keep the main task alive
        try:
            while True:
                await asyncio.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("Exiting...")
            stop_event.set()
