import asyncio
import ipaddress
import os
import signal
import sys
from typing import List

from GreeMQTT import device_db
from GreeMQTT.config import NETWORK
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_communication import DeviceCommunicator
from GreeMQTT.device.device_retry_manager import DeviceRetryManager
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.mqtt_handler import set_params, start_cleanup_task, start_device_tasks

log.info("GreeMQTT package initialized")


async def scan_network_for_devices() -> List[str]:
    """Scan network for devices on port 7000."""
    subnet = os.environ.get("SUBNET", "192.168.1.0/24")
    log.info("Scanning network for devices", subnet=subnet)

    # Get all valid IPs (exclude network and broadcast addresses)
    network = ipaddress.IPv4Network(subnet)
    ip_list = list(network.hosts())

    if not ip_list:
        log.error("No valid IPs in subnet", subnet=subnet)
        return []

    # Scan IPs concurrently with reasonable limits
    semaphore = asyncio.Semaphore(20)  # Limit concurrent scans
    found_devices = []

    async def scan_ip(ip):
        async with semaphore:
            try:
                if await DeviceCommunicator.broadcast_scan(str(ip)):
                    found_devices.append(str(ip))
            except Exception:
                pass  # Ignore scan errors

    # Run all scans
    await asyncio.gather(*[scan_ip(ip) for ip in ip_list], return_exceptions=True)

    log.info("Network scan complete", found_count=len(found_devices))
    return found_devices


class GreeMQTTApp:
    def __init__(self):
        self.stop_event = asyncio.Event()
        self.mqtt_client = None
        self.tasks = []

    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def handle_shutdown(signum, frame):
            log.info(f"Shutdown signal {signum} received")
            self.stop_event.set()

        for sig in [signal.SIGTERM, signal.SIGINT]:
            signal.signal(sig, handle_shutdown)

    async def discover_and_setup_devices(self):
        """Discover devices and set them up for MQTT communication."""
        # Get network to scan (from config or scan automatically)
        network_ips = NETWORK if NETWORK else await scan_network_for_devices()
        if not network_ips:
            log.warning("No devices found on network")
            return

        # Load known devices from database
        known_devices = device_db.get_all_devices()
        known_ips = {device.device_ip for device in known_devices}

        # Start tasks for known devices that are online
        for device in known_devices:
            if device.device_ip in network_ips:
                await start_device_tasks(device, self.mqtt_client, self.stop_event)
                log.info("Started device", ip=device.device_ip)

        # Find and add new devices
        new_ips = [ip for ip in network_ips if ip not in known_ips]
        for ip in new_ips:
            try:
                device = await Device.search_devices(ip)
                if device and device.key:
                    device_db.save_device(device.device_id, device.device_ip, device.key, device.is_GCM)
                    await start_device_tasks(device, self.mqtt_client, self.stop_event)
                    log.info("Added new device", ip=ip)
            except Exception as e:
                log.error("Failed to add device", ip=ip, error=str(e))

        # Start retry manager for any remaining missing devices
        missing_ips = [ip for ip in network_ips if ip not in known_ips and ip not in new_ips]
        if missing_ips:
            retry_manager = DeviceRetryManager(missing_ips, self.mqtt_client, self.stop_event)
            self.tasks.append(asyncio.create_task(retry_manager.run()))

    async def cleanup(self):
        """Cancel all running tasks."""
        log.info("Cleaning up tasks")
        for task in self.tasks:
            if not task.done():
                task.cancel()

        if self.tasks:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        log.info("Cleanup complete")

    async def run(self):
        """Main application entry point."""
        self.setup_signal_handlers()

        try:
            async with await create_mqtt_client() as mqtt_client:
                self.mqtt_client = mqtt_client

                # Setup devices and start MQTT communication
                await self.discover_and_setup_devices()
                await start_cleanup_task(self.stop_event)

                # Start main MQTT parameter handling
                mqtt_task = asyncio.create_task(set_params(mqtt_client, self.stop_event))
                self.tasks.append(mqtt_task)

                # Wait for shutdown signal
                log.info("Application running - press Ctrl+C to stop")
                await self.stop_event.wait()

        except Exception as e:
            log.error("Application error", error=str(e))
        finally:
            await self.cleanup()
            log.info("Application stopped")


def main():
    """Simple main function entry point."""
    try:
        app = GreeMQTTApp()
        asyncio.run(app.run())
    except KeyboardInterrupt:
        log.info("Application interrupted by user")
    except Exception as e:
        log.error("Fatal error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
