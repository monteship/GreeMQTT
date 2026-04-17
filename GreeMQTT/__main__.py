import ipaddress
import os
import signal
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from ipaddress import IPv4Address
from typing import Generator, List, Optional

from GreeMQTT import device_db
from GreeMQTT.config import EVENT_QUEUE_WORKERS, NETWORK
from GreeMQTT.constants import NETWORK_SCAN_SEMAPHORE_LIMIT, NETWORK_SCAN_LOG_INTERVAL
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_communication import DeviceCommunicator
from GreeMQTT.event_queue import get_event_queue
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.mqtt_handler import start_cleanup_task, start_device_tasks

log.info("GreeMQTT package initialized")


class GreeMQTTApp:
    def __init__(self):
        self.stop_event = threading.Event()
        self.event_queue = get_event_queue(max_workers=EVENT_QUEUE_WORKERS)

    def setup_signal_handlers(self):
        def handle_shutdown(signum, frame):
            log.info(f"Shutdown signal {signum} received")
            self.stop_event.set()

        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, handle_shutdown)

    @staticmethod
    def scan_network_for_devices(device_ips: List[str]) -> Generator[Device, None, None]:
        known_devices = device_db.get_all_devices()
        if not device_ips:
            subnet = os.environ.get("SUBNET", "192.168.1.0/24")
            log.info("Scanning network for devices", subnet=subnet)
            network = ipaddress.IPv4Network(subnet)
            known_devices_ips = [
                IPv4Address(device.device_ip)
                for device in known_devices
                if IPv4Address(device.device_ip) in network.hosts()
            ]

            device_ips = known_devices_ips + [ip for ip in network.hosts() if ip not in known_devices_ips]

            if not device_ips:
                raise ValueError("No valid IPs found in the specified subnet")

        def scan_ip(target_ip: str) -> Optional[Device]:
            try:
                if DeviceCommunicator.broadcast_scan(target_ip):
                    device = next(
                        (d for d in known_devices if d.device_ip == target_ip),
                        None,
                    )
                    if not device:
                        device = Device.search_devices(target_ip)
                        if device and device.key:
                            device_db.save_device(
                                device.device_id,
                                device.device_ip,
                                device.key,
                                device.is_GCM,
                            )
                            log.info("Found new device", ip=target_ip)
                        else:
                            log.warning("Device not found or invalid key", ip=target_ip)
                    return device
            except Exception as e:
                log.error("Error scanning IP", ip=target_ip, error=str(e))
            return None

        with ThreadPoolExecutor(max_workers=NETWORK_SCAN_SEMAPHORE_LIMIT) as executor:
            futures = {executor.submit(scan_ip, str(ip)): str(ip) for ip in device_ips}
            completed = 0
            for future in as_completed(futures):
                completed += 1
                if completed % NETWORK_SCAN_LOG_INTERVAL == 0:
                    log.info("Scanned IPs", scanned_ips=completed)
                try:
                    device = future.result()
                    if isinstance(device, Device) and device is not None:
                        log.info("Device found", ip=device.device_ip, id=device.device_id)
                        yield device
                except Exception as e:
                    log.info(e)

    def discover_and_setup_devices(self):
        network = NETWORK.copy() if NETWORK else []

        for device in self.scan_network_for_devices(network):
            try:
                mqtt_client = create_mqtt_client()

                if device.device_ip in network:
                    network.remove(device.device_ip)
                start_device_tasks(device, mqtt_client, self.stop_event)
                log.info("Started device", ip=device.device_ip)
            except Exception as e:
                log.error("Failed to setup device", ip=device.device_ip, error=str(e))
                continue

        if network:
            log.warning(
                "Some devices were not found in the network",
                missing_devices=network,
            )
            from GreeMQTT.device.device_retry_manager import DeviceRetryManager

            retry_manager = DeviceRetryManager(network, self.stop_event)
            retry_manager.run()

    def run(self):
        self.setup_signal_handlers()

        try:
            log.info("Starting internal event queue for single-container deployment")
            self.event_queue.start()

            self.discover_and_setup_devices()
            start_cleanup_task(self.stop_event)

            log.info("Application running - press Ctrl+C to stop")
            self.stop_event.wait()

        except Exception as e:
            log.error("Application error", error=str(e))
        finally:
            log.info("Shutting down internal event queue")
            self.event_queue.stop()


def main():
    try:
        app = GreeMQTTApp()
        app.run()
    except KeyboardInterrupt:
        log.info("Application interrupted by user")
    except Exception as e:
        log.error("Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
