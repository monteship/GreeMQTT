import asyncio
import ipaddress
import os
import signal
import sys
from ipaddress import IPv4Address
from typing import AsyncGenerator, List, Optional

from GreeMQTT import device_db
from GreeMQTT.config import NETWORK
from GreeMQTT.device.device import Device
from GreeMQTT.device.device_communication import DeviceCommunicator
from GreeMQTT.device.device_retry_manager import DeviceRetryManager
from GreeMQTT.logger import log
from GreeMQTT.mqtt_client import create_mqtt_client
from GreeMQTT.mqtt_handler import set_params, start_cleanup_task, start_device_tasks

log.info("GreeMQTT package initialized")


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

    async def scan_network_for_devices(
        self, device_ips: List[str]
    ) -> AsyncGenerator[Device, None]:
        """Scan network for devices on port 7000."""
        if not device_ips:
            subnet = os.environ.get("SUBNET", "192.168.1.0/24")
            log.info("Scanning network for devices", subnet=subnet)

            # Get all valid IPs (exclude network and broadcast addresses)
            network = ipaddress.IPv4Network(subnet)
            known_devices = device_db.get_all_devices()
            known_devices_ips = [
                IPv4Address(device.device_ip)
                for device in known_devices
                if IPv4Address(device.device_ip) in network.hosts()
            ]

            device_ips = known_devices_ips + [
                ip for ip in network.hosts() if ip not in known_devices_ips
            ]

            if not device_ips:
                raise ValueError("No valid IPs found in the specified subnet")

        # Scan IPs concurrently with reasonable limits
        semaphore = asyncio.Semaphore(20)  # Limit concurrent scans

        async def scan_ip(ip) -> Optional[Device]:
            async with semaphore:
                try:
                    if await DeviceCommunicator.broadcast_scan(str(ip)):
                        device = next(
                            (d for d in known_devices if d.device_ip == str(ip)),
                            None,
                        )
                        if not device:
                            device = await Device.search_devices(str(ip))
                            if device and device.key:
                                device_db.save_device(
                                    device.device_id,
                                    device.device_ip,
                                    device.key,
                                    device.is_GCM,
                                )
                                log.info("Found new device", ip=str(ip))
                            else:
                                log.warning(
                                    "Device not found or invalid key", ip=str(ip)
                                )
                        return device
                except Exception:
                    pass  # Ignore scan errors
                return None

        # Create all scan tasks
        scan_tasks = [asyncio.create_task(scan_ip(ip)) for ip in device_ips]

        # Yield devices as they complete
        for task in asyncio.as_completed(scan_tasks):
            try:
                device = await task
                if isinstance(device, Device) and device is not None:
                    log.info("Device found", ip=device.device_ip, id=device.device_id)
                    yield device
            except Exception:
                pass  # Ignore exceptions from individual scans

    async def discover_and_setup_devices(self):
        """Discover devices and set them up for MQTT communication."""
        # Get network to scan (from config or scan automatically)
        network = NETWORK
        async for device in self.scan_network_for_devices(network):
            device_ip = device.device_ip
            if device_ip in network:
                network.remove(device_ip)
            await start_device_tasks(device, self.mqtt_client, self.stop_event)
            log.info("Started device", ip=device.device_ip)

        # Start retry manager for any remaining missing devices
        if network:
            retry_manager = DeviceRetryManager(
                network, self.mqtt_client, self.stop_event
            )
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
                mqtt_task = asyncio.create_task(
                    set_params(mqtt_client, self.stop_event)
                )
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
