import asyncio
from functools import wraps
import json
import traceback

from aiomqtt import Client

from GreeMQTT import logger
from GreeMQTT.config import UPDATE_INTERVAL
from GreeMQTT.device import Device

from typing import Callable

from GreeMQTT.utils import DeviceRegistry

device_registry = DeviceRegistry()


def async_safe_handle(func: Callable) -> Callable:
    """Decorator to safely handle async functions with stop_event and log errors with traceback."""

    @wraps(func)
    async def wrapper(*args, **kwargs):
        stop_event = kwargs.get("stop_event") or (args[2] if len(args) > 2 else None)
        while not (stop_event and stop_event.is_set()):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}\n{traceback.format_exc()}")
                await asyncio.sleep(1)
        logger.info(f"{func.__name__} stopped due to stop_event.")
        return None

    return wrapper


def with_retries(retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorator to add retry logic with exponential backoff to async functions."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempt = 0
            current_delay = delay
            while attempt < retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    if attempt >= retries:
                        logger.error(
                            f"{func.__name__} failed after {retries} attempts: {e}"
                        )
                        raise
                    logger.warning(
                        f"Retrying {func.__name__} in {current_delay} seconds (attempt {attempt}/{retries})..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff

        return wrapper

    return decorator


@async_safe_handle
@with_retries()
async def subscribe(device: Device, mqtt_client: Client, qos: int):
    set_topic = device.set_topic
    await mqtt_client.subscribe(set_topic, qos=qos)
    device_registry.register(set_topic, device)
    logger.info(f"Subscribed to topic {set_topic} with QoS {qos}")


@async_safe_handle
@with_retries()
async def set_params(mqtt_client: Client, stop_event: asyncio.Event):
    async for message in mqtt_client.messages:
        if stop_event.is_set():
            break
        device = device_registry.get(str(message.topic))
        if not device:
            logger.debug(f"Unknown topic received: {message.topic}")
            continue  # Skip unknown topics silently for performance
        try:
            params = json.loads(message.payload.decode("utf-8"))
            await device.set_params(params)
            logger.info(f"Set params for {message.topic}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON on {message.topic}: {message.payload}")


@async_safe_handle
@with_retries()
async def get_params(
    device: Device,
    mqtt_client: Client,
    stop_event: asyncio.Event,
    qos: int,
    retain: bool,
):
    """Periodically publishes device parameters to the MQTT topic."""
    params_topic = device.topic
    logger.info(f"Publishing device parameters to topic {params_topic}.")
    while not stop_event.is_set():
        params = await device.get_param()
        if params:
            params_str = json.dumps(params, separators=(",", ":"))
            await mqtt_client.publish(params_topic, params_str, qos=qos, retain=retain)
            logger.debug(f"{params_topic}: {params_str} (QoS {qos}, Retain {retain})")
        await asyncio.sleep(UPDATE_INTERVAL)
