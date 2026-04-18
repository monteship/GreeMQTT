import ipaddress
import signal
import sys
import threading
from typing import Optional

from GreeMQTT import device_db
from GreeMQTT.config import settings
from GreeMQTT.device.device import Device
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import create_mqtt_client, shutdown_mqtt
from GreeMQTT.mqtt_handler import start_cleanup_task, start_device_tasks

RETRY_SLEEP = 300


class GreeMQTTApp:
    def __init__(self):
        self.stop_event = threading.Event()

    def setup_signal_handlers(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: self.stop_event.set())

    @staticmethod
    def _get_broadcast_address() -> str:
        """Derive the broadcast address from the configured network/subnet."""
        network_list = settings.network_list
        if network_list:
            # If specific IPs are given, we can't broadcast — return empty
            # But if a subnet is given (e.g. "192.168.1.0/24"), use its broadcast
            for item in network_list:
                if "/" in item:
                    return str(ipaddress.IPv4Network(item, strict=False).broadcast_address)
            return ""

        import os
        subnet = os.environ.get("SUBNET", "192.168.1.0/24")
        return str(ipaddress.IPv4Network(subnet, strict=False).broadcast_address)

    def discover_devices(self) -> list[Device]:
        """Discover devices via broadcast, falling back to known DB devices."""
        known_devices = device_db.get_all_devices()
        known_by_id = {d.device_id: d for d in known_devices}

        broadcast_addr = self._get_broadcast_address()
        discovered: list[Device] = []

        if broadcast_addr:
            log.info("Discovering devices via broadcast", broadcast=broadcast_addr)
            for device in Device.discover_all(broadcast_addr):
                if device.device_id not in known_by_id:
                    device_db.save_device(device.device_id, device.device_ip, device.key, device.is_GCM)
                    log.info("Found new device", ip=device.device_ip, id=device.device_id)
                else:
                    # Use stored key but update IP if changed
                    known = known_by_id[device.device_id]
                    if known.device_ip != device.device_ip:
                        device_db.save_device(device.device_id, device.device_ip, known.key, known.is_GCM)
                        log.info("Device IP updated", id=device.device_id, old_ip=known.device_ip, new_ip=device.device_ip)
                discovered.append(device)

        # Also try specific IPs from NETWORK config that weren't found via broadcast
        discovered_ips = {d.device_ip for d in discovered}
        specific_ips = [ip for ip in settings.network_list if "/" not in ip and ip not in discovered_ips]
        for ip in specific_ips:
            device = self._try_connect_ip(ip, known_by_id)
            if device:
                discovered.append(device)

        # Add known DB devices that weren't discovered (they may still be reachable)
        discovered_ids = {d.device_id for d in discovered}
        for known in known_devices:
            if known.device_id not in discovered_ids:
                log.info("Using known device from DB", id=known.device_id, ip=known.device_ip)
                discovered.append(known)

        return discovered

    @staticmethod
    def _try_connect_ip(ip: str, known_by_id: dict[str, Device]) -> Optional[Device]:
        """Try to discover a device at a specific IP."""
        try:
            device = Device.search_devices(ip)
            if device and device.key:
                if device.device_id not in known_by_id:
                    device_db.save_device(device.device_id, device.device_ip, device.key, device.is_GCM)
                    log.info("Found new device at specific IP", ip=ip, id=device.device_id)
                return device
        except Exception as e:
            log.error("Error scanning IP", ip=ip, error=str(e))
        return None

    def discover_and_setup_devices(self):
        mqtt_client = create_mqtt_client()
        devices = self.discover_devices()

        if not devices:
            log.warning("No devices found")
            return

        for device in devices:
            try:
                start_device_tasks(device, mqtt_client, self.stop_event)
                log.info("Started device", ip=device.device_ip, id=device.device_id)
            except Exception as e:
                log.error("Failed to setup device", ip=device.device_ip, error=str(e))


    def run(self):
        self.setup_signal_handlers()
        try:
            self.discover_and_setup_devices()
            start_cleanup_task(self.stop_event)
            log.info("Application running - press Ctrl+C to stop")
            self.stop_event.wait()
        except Exception as e:
            log.error("Application error", error=str(e))
        finally:
            log.info("Shutting down...")
            self.stop_event.set()
            shutdown_mqtt()
            log.info("Shutdown complete")


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
