import os
from typing import List

from dotenv import load_dotenv

from GreeMQTT.logger import log

# Load environment variables from .env file
load_dotenv()


def get_env_list(var_name: str, default: str = None) -> List[str]:
    """
    Retrieves a list of values from an environment variable.

    Args:
        var_name (str): The name of the environment variable.
        default (str, optional): A default comma-separated string to use if the environment variable is not set. Defaults to None.

    Returns:
        List[str]: A list of non-empty, stripped values. Returns an empty list if the environment variable is unset or empty.
    """
    value = os.getenv(var_name, default)
    if value is None or value.strip() == "":
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def get_env_int(var_name: str, default: int = None) -> int:
    value = os.getenv(var_name)
    if value is None:
        if default is not None:
            return default
        raise ValueError(f"{var_name} environment variable is not set.")
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"{var_name} must be an integer.")


def get_env_bool(var_name: str, default: bool = False) -> bool:
    value = os.getenv(var_name)
    if value is None:
        return default
    return value.strip().lower() == "true"


def get_env_str(var_name: str, default: str = None, required: bool = False) -> str:
    value = os.getenv(var_name, default)
    if required and not value:
        raise ValueError(f"{var_name} environment variable is required.")
    return value


# Network configuration
NETWORK: List[str] = get_env_list("NETWORK")

# MQTT configuration
MQTT_BROKER: str = get_env_str("MQTT_BROKER", required=True)
MQTT_PORT: int = get_env_int("MQTT_PORT", 1883)
MQTT_USER: str = get_env_str("MQTT_USER")
MQTT_PASSWORD: str = get_env_str("MQTT_PASSWORD")
MQTT_TOPIC: str = get_env_str("MQTT_TOPIC", "gree")
MQTT_QOS: int = get_env_int("MQTT_QOS", 0)
if MQTT_QOS not in [0, 1, 2]:
    raise ValueError("MQTT_QOS environment variable must be 0, 1, or 2.")
MQTT_RETAIN: bool = get_env_bool("MQTT_RETAIN", False)
MQTT_KEEP_ALIVE: int = get_env_int("MQTT_KEEP_ALIVE", 60)

log.debug(
    "Initialized MQTT with",
    broker=MQTT_BROKER,
    port=MQTT_PORT,
    user=MQTT_USER,
    password="*" * len(MQTT_PASSWORD) if MQTT_PASSWORD else None,
    topic=MQTT_TOPIC,
    qos=MQTT_QOS,
    retain=MQTT_RETAIN,
    keep_alive=MQTT_KEEP_ALIVE,
)

# Update interval
UPDATE_INTERVAL: int = get_env_int("UPDATE_INTERVAL", 3)  # Reduced from 4 to 3 seconds
ADAPTIVE_POLLING_TIMEOUT: int = get_env_int(
    "ADAPTIVE_POLLING_TIMEOUT", 45
)  # Reduced from 60 to 45 seconds
ADAPTIVE_FAST_INTERVAL: int = get_env_int(
    "ADAPTIVE_FAST_INTERVAL", 0.8
)  # Reduced from 1 to 0.8 seconds

# Enhanced responsiveness settings
MQTT_MESSAGE_WORKERS: int = get_env_int(
    "MQTT_MESSAGE_WORKERS", 3
)  # Number of concurrent message processors
IMMEDIATE_RESPONSE_TIMEOUT: float = get_env_int(
    "IMMEDIATE_RESPONSE_TIMEOUT", 5
)  # Ultra-fast polling duration

# Tracking parameters
DEFAULT_PARAMS = (
    "Pow,Mod,SetTem,TemUn,WdSpd,Air,Blo,Health,SwhSlp,Lig,SwingLfRig,"
    "SwUpDn,Quiet,Tur,StHt,HeatCoolType,TemRec,SvSt,TemSen"
)
TRACKING_PARAMS: List[str] = get_env_list("TRACKING_PARAMS", DEFAULT_PARAMS)

log.debug(
    "Initialized GreeMQTT with",
    network=NETWORK,
    update_interval=UPDATE_INTERVAL,
    params=TRACKING_PARAMS,
)
