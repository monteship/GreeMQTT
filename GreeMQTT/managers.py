import threading
import time
from typing import Callable, Tuple

from loguru import logger
import paho.mqtt.client as mqtt

from GreeMQTT.device import search_devices, ScanResult
from GreeMQTT.device_db import device_db

from GreeMQTT.mqtt_handler import handle_get_params, handle_set_params


def run_thread(target: Callable, args: Tuple):
    """
    Run a function in a separate thread.
    :param target:
    :param args:
    :return:
    """
    thread = threading.Thread(target=target, args=args)
    thread.daemon = True
    thread.start()
    return thread


def start_device_threads(
    device: ScanResult,
    mqtt_client: mqtt.Client,
    stop_event: threading.Event,
) -> Tuple[threading.Thread, threading.Thread]:
    """
    Start threads for handling device parameters.
    :param device:
    :param mqtt_client:
    :param stop_event:
    :return:
    """
    get_thread = run_thread(handle_get_params, (device, mqtt_client, stop_event))
    set_thread = run_thread(handle_set_params, (device, mqtt_client, stop_event))
    return get_thread, set_thread


class DeviceRetryManager:
    def __init__(self, missing_devices, mqtt_client, stop_event):
        self.missing_devices = missing_devices
        self.mqtt_client = mqtt_client
        self.stop_event = stop_event
        self.threads = []
        self.thread = threading.Thread(target=self._retry_loop, daemon=True)

    def start(self):
        self.thread.start()

    def join(self):
        self.thread.join()

    def _retry_loop(self):
        while not self.stop_event.is_set():
            for device_ip in list(self.missing_devices):
                device = search_devices(device_ip)
                if device and device.key:
                    logger.info(f"Device found on retry: {device}")
                    device_db.save_device(
                        device.device_id, device.ip, device.key, device.is_GCM
                    )
                    self.threads.extend(
                        start_device_threads(device, self.mqtt_client, self.stop_event)
                    )
                    self.missing_devices.remove(device_ip)
            time.sleep(300)  # 5 minutes
