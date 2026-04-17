import ipaddress
import os
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from ipaddress import IPv4Address
from typing import Optional

from GreeMQTT import device_db
from GreeMQTT.config import NETWORK
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_communication import DeviceCommunicator
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.mqtt_handler import start_cleanup_task, start_device_tasks

SCAN_WORKERS = 20
SCAN_LOG_INTERVAL = 20
RETRY_SLEEP = 300


class GreeMQTTApp:
    def __init__(self):
        self.stop_event = threading.Event()

    def setup_signal_handlers(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: self.stop_event.set())

    def scan_for_devices(self, device_ips: list[str]):
        known_devices = device_db.get_all_devices()

        if not device_ips:
            subnet = os.environ.get("SUBNET", "192.168.1.0/24")
            log.info("Scanning network for devices", subnet=subnet)
            network = ipaddress.IPv4Network(subnet)
            known_ips = [IPv4Address(d.device_ip) for d in known_devices if IPv4Address(d.device_ip) in network.hosts()]
            device_ips = [str(ip) for ip in known_ips + [ip for ip in network.hosts() if ip not in known_ips]]
            if not device_ips:
                raise ValueError("No valid IPs found in the specified subnet")

        def scan_ip(target_ip: str) -> Optional[Device]:
            try:
                if not DeviceCommunicator.broadcast_scan(target_ip):
                    return None
                device = next((d for d in known_devices if d.device_ip == target_ip), None)
                if not device:
                    device = Device.search_devices(target_ip)
                    if device and device.key:
                        device_db.save_device(device.device_id, device.device_ip, device.key, device.is_GCM)
                        log.info("Found new device", ip=target_ip)
                    else:
                        log.warning("Device not found or invalid key", ip=target_ip)
                return device
            except Exception as e:
                log.error("Error scanning IP", ip=target_ip, error=str(e))
            return None

        with ThreadPoolExecutor(max_workers=SCAN_WORKERS) as executor:
            futures = {executor.submit(scan_ip, str(ip)): str(ip) for ip in device_ips}
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % SCAN_LOG_INTERVAL == 0:
                    log.info("Scanned IPs", scanned=completed)
                try:
                    device = future.result()
                    if isinstance(device, Device):
                        log.info("Device found", ip=device.device_ip, id=device.device_id)
                        yield device
                except Exception as e:
                    log.error("Scan error", error=str(e))

    def discover_and_setup_devices(self):
        remaining = NETWORK.copy() if NETWORK else []

        for device in self.scan_for_devices(remaining):
            try:
                mqtt_client = create_mqtt_client()
                if device.device_ip in remaining:
                    remaining.remove(device.device_ip)
                start_device_tasks(device, mqtt_client, self.stop_event)
                log.info("Started device", ip=device.device_ip)
            except Exception as e:
                log.error("Failed to setup device", ip=device.device_ip, error=str(e))

        if remaining:
            log.warning("Some devices were not found", missing=remaining)
            self._retry_missing(remaining)

    def _retry_missing(self, missing: list[str]):
        from GreeMQTT.mqtt_handler import interruptible_sleep

        while not self.stop_event.is_set() and missing:
            for ip in missing.copy():
                try:
                    device = Device.search_devices(ip)
                    if device and device.key:
                        log.info("New device found", device=str(device))
                        device_db.save_device(device.device_id, device.device_ip, device.key, device.is_GCM)
                        mqtt_client = create_mqtt_client()
                        start_device_tasks(device, mqtt_client, self.stop_event)
                        missing.remove(ip)
                except Exception as e:
                    log.error("Error during device retry", device_ip=ip, error=str(e))

            if not missing:
                log.info("All devices found")
                break
            if interruptible_sleep(RETRY_SLEEP, self.stop_event):
                break
            log.info("Retrying missing devices", missing=missing)

    def run(self):
        self.setup_signal_handlers()
        try:
            self.discover_and_setup_devices()
            start_cleanup_task(self.stop_event)
            log.info("Application running - press Ctrl+C to stop")
            self.stop_event.wait()
        except Exception as e:
            log.error("Application error", error=str(e))


def main():
    try:
        GreeMQTTApp().run()
    except KeyboardInterrupt:
        log.info("Application interrupted by user")
    except Exception as e:
        log.error("Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
