import asyncio
from typing import List
from GreeMQTT import device_db
from GreeMQTT.device.device_retry_manager import DeviceRetryManager
from GreeMQTT.logger import log
from GreeMQTT.config import NETWORK
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.device.device import Device
from GreeMQTT.mqtt_handler import set_params, start_device_tasks

log.info("GreeMQTT package initialized")


class GreeMQTTApp:
    def __init__(self):
        self.stop_event = asyncio.Event()
        self.known_devices: List[Device] = []
        self.missing_devices: List[str] = []
        self.mqtt_client = None
        self.retry_manager = None

    async def load_devices(self):
        self.known_devices = device_db.get_all_devices()
        known_ips = [device.device_ip for device in self.known_devices]
        self.missing_devices = [ip for ip in NETWORK if ip not in known_ips]

    async def start_known_devices(self):
        for device in self.known_devices:
            if device.device_ip not in NETWORK:
                log.info("Device not in network, skipping", device=str(device))
                continue
            await start_device_tasks(device, self.mqtt_client, self.stop_event)

    async def search_and_add_missing_devices(self):
        for device_ip in self.missing_devices[:]:
            device = await Device.search_devices(device_ip)
            if device and device.key:
                log.info("New device found", device=str(device))
                device_db.save_device(
                    device.device_id, device.device_ip, device.key, device.is_GCM
                )
                self.missing_devices.remove(device_ip)
                await start_device_tasks(device, self.mqtt_client, self.stop_event)

    async def start_retry_manager(self):
        if self.missing_devices:
            log.info(
                "Starting retry manager for missing devices",
                missing_devices=self.missing_devices,
            )
            self.retry_manager = DeviceRetryManager(
                self.missing_devices, self.mqtt_client, self.stop_event
            )
            asyncio.create_task(self.retry_manager.run())
        else:
            log.info("All devices found, no retry needed.")

    async def run(self):
        await self.load_devices()
        async with await create_mqtt_client() as mqtt_client:
            self.mqtt_client = mqtt_client
            await self.start_known_devices()
            await self.search_and_add_missing_devices()
            await self.start_retry_manager()
            await asyncio.create_task(set_params(self.mqtt_client, self.stop_event))
            try:
                while True:
                    await asyncio.sleep(0.1)
            except KeyboardInterrupt:
                log.info("Exiting...")
                self.stop_event.set()


def main():
    app = GreeMQTTApp()
    try:
        asyncio.run(app.run())
    except KeyboardInterrupt:
        log.info("Exiting...")


if __name__ == "__main__":
    main()
