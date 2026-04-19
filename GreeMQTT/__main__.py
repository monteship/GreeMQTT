import ipaddress
import signal
import sys
import threading

from GreeMQTT.config import settings
from GreeMQTT.device.device import Device
from GreeMQTT.ha_discovery import publish_ha_discovery
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import create_mqtt_client, shutdown_mqtt
from GreeMQTT.mqtt_handler import start_cleanup_task, start_device_tasks

REDISCOVERY_INTERVAL = 300


class GreeMQTTApp:
    def __init__(self):
        self.stop_event = threading.Event()
        self._known_device_ids: set[str] = set()
        self._mqtt_client = None

    def setup_signal_handlers(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: self.stop_event.set())

    @staticmethod
    def _get_broadcast_address() -> str:
        """Derive the broadcast address from the configured network/subnet."""
        network_list = settings.network_list
        if network_list:
            for item in network_list:
                if "/" in item:
                    return str(ipaddress.IPv4Network(item, strict=False).broadcast_address)
            return ""

        import os
        subnet = os.environ.get("SUBNET", "192.168.1.0/24")
        return str(ipaddress.IPv4Network(subnet, strict=False).broadcast_address)

    def discover_devices(self) -> list[Device]:
        """Discover devices via broadcast and/or specific IPs."""
        broadcast_addr = self._get_broadcast_address()
        discovered: list[Device] = []

        if broadcast_addr:
            log.info("Discovering devices via broadcast", broadcast=broadcast_addr)
            discovered.extend(Device.discover_all(broadcast_addr))

        # Also try specific IPs from NETWORK config that weren't found via broadcast
        discovered_ips = {d.device_ip for d in discovered}
        specific_ips = [ip for ip in settings.network_list if "/" not in ip and ip not in discovered_ips]
        for ip in specific_ips:
            try:
                device = Device.search_devices(ip)
                if device and device.key:
                    log.info("Found device at specific IP", ip=ip, id=device.device_id)
                    discovered.append(device)
            except Exception as e:
                log.error("Error scanning IP", ip=ip, error=str(e))

        return discovered

    def _setup_device(self, device: Device) -> bool:
        """Set up a single device: start tasks, publish HA discovery. Returns True on success."""
        if device.device_id in self._known_device_ids:
            return False
        try:
            start_device_tasks(device, self._mqtt_client, self.stop_event)
            publish_ha_discovery(device, self._mqtt_client)
            self._known_device_ids.add(device.device_id)
            log.info("Started device", ip=device.device_ip, id=device.device_id, name=device.name)
            return True
        except Exception as e:
            log.error("Failed to setup device", ip=device.device_ip, error=str(e))
            return False

    def discover_and_setup_devices(self) -> int:
        """Discover and set up new devices. Returns count of newly added devices."""
        devices = self.discover_devices()
        if not devices:
            log.warning("No devices found")
            return 0
        added = sum(1 for d in devices if self._setup_device(d))
        return added

    def _rediscovery_loop(self):
        """Periodically scan for new devices that may have come online."""
        while not self.stop_event.is_set():
            if self.stop_event.wait(timeout=REDISCOVERY_INTERVAL):
                break
            log.debug("Running periodic device rediscovery")
            try:
                added = self.discover_and_setup_devices()
                if added:
                    log.info("Rediscovery found new devices", count=added)
            except Exception as e:
                log.error("Rediscovery error", error=str(e))

    def run(self):
        self.setup_signal_handlers()
        try:
            self._mqtt_client = create_mqtt_client()
            self.discover_and_setup_devices()
            start_cleanup_task(self.stop_event)

            threading.Thread(target=self._rediscovery_loop, daemon=True).start()

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
