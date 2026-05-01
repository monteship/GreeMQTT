import ipaddress
import signal
import sys
import threading

from GreeMQTT.config import settings
from GreeMQTT.device.device import Device
from GreeMQTT.ha_discovery import publish_ha_discovery
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import create_mqtt_client, shutdown_mqtt
from GreeMQTT.mqtt_handler import is_device_thread_alive, start_device_tasks

REDISCOVERY_INTERVAL = 300
FAST_RECONNECT_DELAY = 10  # seconds to wait before fast reconnect attempt


class GreeMQTTApp:
    def __init__(self):
        self.stop_event = threading.Event()
        self._rediscovery_trigger = threading.Event()
        self._known_device_ids: set[str] = set()
        self._known_devices: dict[str, Device] = {}
        self._mqtt_client = None

    def setup_signal_handlers(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda s, f: self.stop_event.set())

    def _on_device_thread_dead(self, device_id: str) -> None:
        log.info("Device thread dead, triggering fast reconnect", device_id=device_id)
        self._rediscovery_trigger.set()

    @staticmethod
    def _get_broadcast_address() -> str:
        for item in settings.network_list:
            if "/" in item:
                return str(ipaddress.IPv4Network(item, strict=False).broadcast_address)
        return ""


    def discover_devices(self) -> list[Device]:
        """Discover devices via broadcast and/or specific IPs."""
        broadcast_addr = self._get_broadcast_address()
        discovered: list[Device] = []

        active_ids = {
            did for did in self._known_device_ids
            if is_device_thread_alive(did)
        }

        if broadcast_addr:
            log.info("Discovering devices via broadcast", broadcast=broadcast_addr)
            discovered.extend(Device.discover_all(broadcast_addr, skip_bind_ids=active_ids))

        discovered_ips = {d.device_ip for d in discovered}
        specific_ips = [ip for ip in settings.network_list if "/" not in ip and ip not in discovered_ips]
        for ip in specific_ips:
            try:
                device = Device.search_devices(ip)
                if device and device.key:
                    if device.device_id not in active_ids:
                        log.info("Found device at specific IP", ip=ip, id=device.device_id)
                        discovered.append(device)
            except Exception as e:
                log.error("Error scanning IP", ip=ip, error=str(e))

        return discovered

    def _setup_device(self, device: Device) -> bool:
        if device.device_id in self._known_device_ids:
            if is_device_thread_alive(device.device_id):
                return False
            log.info("Device thread dead, restarting", device_id=device.device_id)
        try:
            if not self._mqtt_client:
                raise RuntimeError("MQTT client not initialized")
            start_device_tasks(device, self._mqtt_client, self.stop_event,
                                on_thread_dead=self._on_device_thread_dead)
            publish_ha_discovery(device, self._mqtt_client)
            self._known_device_ids.add(device.device_id)
            self._known_devices[device.device_id] = device
            log.info("Started device", ip=device.device_ip, id=device.device_id, name=device.name)
            return True
        except Exception as e:
            log.error("Failed to setup device", ip=device.device_ip, error=str(e))
            return False

    def discover_and_setup_devices(self) -> int:
        dead_device_ids = {
            did for did in self._known_device_ids
            if not is_device_thread_alive(did)
        }
        if self._known_device_ids and not dead_device_ids:
            log.debug("All device threads alive, skipping rediscovery")
            return 0

        devices = self.discover_devices()
        if not devices:
            log.warning("No devices found")
            return 0
        added = sum(1 for d in devices if self._setup_device(d))
        return added

    def _fast_reconnect_dead_devices(self) -> int:
        dead_device_ids = {
            did for did in self._known_device_ids
            if not is_device_thread_alive(did)
        }
        if not dead_device_ids:
            return 0

        added = 0
        for did in dead_device_ids:
            known_device = self._known_devices.get(did)
            if not known_device:
                continue
            try:
                log.info("Fast reconnect: unicast probe", device_id=did, ip=known_device.device_ip)
                device = Device.search_devices(known_device.device_ip)
                if device and device.key:
                    if self._setup_device(device):
                        added += 1
                else:
                    log.warning("Fast reconnect failed, will retry on next periodic scan",
                                device_id=did, ip=known_device.device_ip)
            except Exception as e:
                log.error("Fast reconnect error", device_id=did, error=str(e))
        return added

    def _rediscovery_loop(self):
        while not self.stop_event.is_set():
            triggered = self._rediscovery_trigger.wait(timeout=REDISCOVERY_INTERVAL)
            if self.stop_event.is_set():
                break
            self._rediscovery_trigger.clear()
            try:
                if triggered:
                    if self.stop_event.wait(timeout=FAST_RECONNECT_DELAY):
                        break
                    log.info("Running fast reconnect for dead device(s)")
                    added = self._fast_reconnect_dead_devices()
                    if added:
                        log.info("Fast reconnect restored device(s)", count=added)
                else:
                    log.debug("Running periodic device rediscovery")
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
