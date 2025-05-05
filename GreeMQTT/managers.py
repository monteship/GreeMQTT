import asyncio

from GreeMQTT import logger
from GreeMQTT.config import MQTT_QOS, MQTT_RETAIN
from GreeMQTT.device import Device
from GreeMQTT.device_db import device_db
from GreeMQTT.mqtt_handler import get_params, subscribe


async def start_device_tasks(
    device: Device,
    mqtt_client,
    stop_event: asyncio.Event,
):
    """
    Start async tasks for handling device parameters.
    :param device:
    :param mqtt_client:
    :param stop_event:
    :return:
    """
    asyncio.create_task(
        get_params(device, mqtt_client, stop_event, MQTT_QOS, MQTT_RETAIN)
    )
    asyncio.create_task(subscribe(device, mqtt_client, MQTT_QOS))


class DeviceRetryManager:
    def __init__(self, missing_devices, mqtt_client, stop_event):
        self.missing_devices = missing_devices
        self.mqtt_client = mqtt_client
        self.stop_event = stop_event

    async def run(self):
        while not self.stop_event.is_set():
            for device_ip in list(self.missing_devices):
                device = await Device.search_devices(device_ip)
                if device and device.key:
                    logger.info(f"Device found on retry: {device}")
                    device_db.save_device(
                        device.device_id, device.device_ip, device.key, device.is_GCM
                    )
                    await start_device_tasks(device, self.mqtt_client, self.stop_event)
                    self.missing_devices.remove(device_ip)
            if not self.missing_devices:
                logger.info("All devices found.")
                break
            logger.info(f"Retrying to find devices: {self.missing_devices}")
            await asyncio.sleep(300)  # 5 minutes
