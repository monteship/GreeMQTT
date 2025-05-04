import asyncio

from GreeMQTT import logger
from GreeMQTT.config import NETWORK
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.device import Device
from GreeMQTT.device_db import device_db
from GreeMQTT.managers import DeviceRetryManager, start_device_tasks


async def main():
    tasks = []
    stop_event = asyncio.Event()

    # Load known devices from DB
    known_devices = {
        mac: (ip, key, is_gcm) for mac, ip, key, is_gcm in device_db.get_all_devices()
    }
    missing_devices = []

    async with await create_mqtt_client() as mqtt_client:
        for device_ip in NETWORK:
            device = None
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
                device = await Device.search_devices(device_ip)
                if device and device.key:
                    logger.info(f"Device found: {device}")
                    device_db.save_device(
                        device.device_id, device.ip, device.key, device.is_GCM
                    )
                else:
                    logger.warning(f"Device not found: {device_ip}")
                    missing_devices.append(device_ip)
            if device:
                # Start async tasks for periodic updates
                tasks.extend(await start_device_tasks(device, mqtt_client, stop_event))

        # Start retry task
        if missing_devices:
            retry_manager = DeviceRetryManager(missing_devices, mqtt_client, stop_event)
            retry_task = asyncio.create_task(retry_manager.run())
            await retry_task
        else:
            logger.info("All devices found.")

        # Keep the main task alive
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("Exiting...")
            stop_event.set()
            await asyncio.gather(*tasks, return_exceptions=True)
