import asyncio
import ipaddress
import os
from typing import List

from tqdm.asyncio import tqdm_asyncio

from GreeMQTT import device_db
from GreeMQTT.config import NETWORK
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_communication import DeviceCommunicator
from GreeMQTT.device.device_retry_manager import DeviceRetryManager
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.mqtt_handler import set_params, start_cleanup_task, start_device_tasks

log.info("GreeMQTT package initialized")


async def scan_port_7000_on_subnet() -> List[str]:
    subnet = os.environ.get("SUBNET", "192.168.1.0/24")
    result = await DeviceCommunicator.broadcast_scan(subnet.replace("0/24", "255"))
    if not result:
        log.error(
            "No devices found on the subnet with open port 7000",
            subnet=subnet,
        )

        return []
    else:
        log.info("1 or more devices found on the subnet", subnet=subnet)
        log.debug("Initial scan", result=result)

    open_ips = []
    log.info("Scanning subnet", subnet=subnet)

    async def check_ip(ip):
        async with sem:
            try:
                response = await DeviceCommunicator.broadcast_scan(str(ip))
                if response:
                    open_ips.append(str(ip))
            except Exception as e:
                log.error("Error scanning IP", ip=str(ip), error=str(e))
                pass

    ip_list = [
        ip
        for ip in ipaddress.IPv4Network(subnet)
        if not (str(ip).endswith(".0") or str(ip).endswith(".255"))
    ]
    # Limit concurrency to avoid overwhelming the network
    sem = asyncio.Semaphore(len(ip_list) // 2)

    tasks = [asyncio.create_task(check_ip(ip)) for ip in ip_list]
    await tqdm_asyncio.gather(*tasks, desc="Scanning IPs", total=len(ip_list))
    return open_ips


class GreeMQTTApp:
    def __init__(self):
        self.stop_event = asyncio.Event()
        self.known_devices: List[Device] = []
        self.missing_devices: List[str] = []
        self.mqtt_client = None
        self.retry_manager = None
        self.network = NETWORK.copy()

    async def scan_network(self):
        log.info("NETWORK not provided, scanning for devices on port 7000...")
        self.network = await scan_port_7000_on_subnet()
        log.info("Discovered devices:", network=self.network)

    async def load_devices(self):
        if not self.network:
            await self.scan_network()
        self.known_devices = device_db.get_all_devices()
        known_ips = [d.device_ip for d in self.known_devices]
        self.missing_devices = [ip for ip in self.network if ip not in known_ips]

    async def start_devices(self):
        for device in self.known_devices:
            if self.network and device.device_ip not in self.network:
                log.info("Device not in network, skipping", device=str(device))
                continue
            await start_device_tasks(device, self.mqtt_client, self.stop_event)

    async def add_missing_devices(self):
        for ip in self.missing_devices[:]:
            device = await Device.search_devices(ip)
            if device and device.key:
                log.info("New device found", device=str(device))
                device_db.save_device(
                    device.device_id, device.device_ip, device.key, device.is_GCM
                )
                self.missing_devices.remove(ip)
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
        async with await create_mqtt_client() as mqtt_client:
            self.mqtt_client = mqtt_client
            await self.load_devices()
            await self.start_devices()
            await self.add_missing_devices()
            await self.start_retry_manager()
            await start_cleanup_task(self.stop_event)
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
