import asyncio
from loguru import logger
from functools import wraps
import json

from GreeMQTT.config import UPDATE_INTERVAL
from GreeMQTT.device import Device

from typing import Callable


def async_safe_handle(func: Callable) -> Callable:
    @wraps(func)
    async def wrapper(*args, **kwargs):
        stop_event = args[2] if len(args) > 2 else kwargs.get("stop_event")
        while not (stop_event and stop_event.is_set()):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                await asyncio.sleep(1)
        logger.info(f"{func.__name__} stopped due to stop_event.")
        return None

    return wrapper


@async_safe_handle
async def handle_set_params(
    device: Device,
    mqtt_client,
    stop_event: asyncio.Event,
    qos: int,
):
    set_topic = f"{device.topic}/set"
    messages = mqtt_client.messages
    await mqtt_client.subscribe(set_topic, qos=qos)
    logger.info(f"Subscribed to topic {set_topic} with QoS {qos}")
    async for message in messages:
        if stop_event.is_set():
            break
        if message.topic == set_topic:
            logger.info(f"Received message on topic {message.topic}: {message.payload}")
            try:
                params = json.loads(message.payload.decode("utf-8"))
                await device.set_params(params)
            except json.JSONDecodeError:
                logger.error(
                    f"Invalid JSON received on topic {message.topic}: {message.payload}"
                )


@async_safe_handle
async def handle_get_params(
    device: Device,
    mqtt_client,
    stop_event: asyncio.Event,
    qos: int,
    retain: bool,
):
    params_topic = device.topic
    logger.info(f"Publishing device parameters to topic {params_topic}.")
    while not stop_event.is_set():
        params = await device.get_param()
        if params:
            params_str = json.dumps(params)
            await mqtt_client.publish(params_topic, params_str, qos=qos, retain=retain)
            logger.info(
                f"{params_topic}: {params_str.replace(' ', '')} (QoS {qos}, Retain {retain})"
            )
        else:
            logger.error(f"Failed to get parameters from device {device.device_id}.")
        await asyncio.sleep(UPDATE_INTERVAL)
