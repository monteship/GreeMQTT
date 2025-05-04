import asyncio

from GreeMQTT import logger
from GreeMQTT.config import MQTT_QOS, MQTT_RETAIN
from GreeMQTT.device import Device
from GreeMQTT.device_db import device_db
from GreeMQTT.mqtt_handler import handle_get_params, handle_set_params


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
    get_task = asyncio.create_task(
        handle_get_params(device, mqtt_client, stop_event, MQTT_QOS, MQTT_RETAIN)
    )
    set_task = asyncio.create_task(
        handle_set_params(device, mqtt_client, stop_event, MQTT_QOS)
    )
    return [get_task, set_task]


class DeviceRetryManager:
    def __init__(self, missing_devices, mqtt_client, stop_event):
        self.missing_devices = missing_devices
        self.mqtt_client = mqtt_client
        self.stop_event = stop_event
        self.tasks = []

    async def run(self):
        while not self.stop_event.is_set():
            for device_ip in list(self.missing_devices):
                device = await Device.search_devices(device_ip)
                if device and device.key:
                    logger.info(f"Device found on retry: {device}")
                    device_db.save_device(
                        device.device_id, device.ip, device.key, device.is_GCM
                    )
                    self.tasks.extend(
                        await start_device_tasks(
                            device, self.mqtt_client, self.stop_event
                        )
                    )
                    self.missing_devices.remove(device_ip)
            await asyncio.sleep(300)  # 5 minutes
