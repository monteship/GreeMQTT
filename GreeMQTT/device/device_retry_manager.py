import asyncio

from aiomqtt import Client

from GreeMQTT import device_db
from GreeMQTT.device.device import Device
from GreeMQTT.logger import log
from GreeMQTT.mqtt_handler import start_device_tasks


class DeviceRetryManager:
    def __init__(self, missing_devices: list, mqtt_client: Client, stop_event):
        self.missing_devices = missing_devices
        self.mqtt_client = mqtt_client
        self.stop_event = stop_event

    async def run(self):
        while not self.stop_event.is_set():
            for device_ip in self.missing_devices.copy():
                device = await Device.search_devices(device_ip)
                if device and device.key:
                    log.info("New device found", device=str(device))
                    device_db.save_device(
                        device.device_id, device.device_ip, device.key, device.is_GCM
                    )
                    await start_device_tasks(device, self.mqtt_client, self.stop_event)
                    self.missing_devices.remove(device_ip)
            if not self.missing_devices:
                log.info("Retry manager finished, all devices found.")
                break
            await asyncio.sleep(300)  # 5 minutes
            log.info("Retrying missing devices", missing_devices=self.missing_devices)
