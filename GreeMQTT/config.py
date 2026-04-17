import os
from typing import Callable, TypeVar

from dotenv import load_dotenv

from GreeMQTT.logger import log

load_dotenv()

T = TypeVar("T")


def env(key: str, default: T = None, cast: Callable[[str], T] = str) -> T:
    """Read an environment variable and cast it to the expected type."""
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return cast(value)
    except (ValueError, TypeError):
        log.warning("Invalid value for env var, using default", key=key, value=value, default=default)
        return default


def env_bool(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.strip().lower() in ("true", "1", "yes")


def env_list(key: str, default: list | None = None, sep: str = ",") -> list[str]:
    value = os.getenv(key)
    if value is None:
        return default or []
    return [item.strip() for item in value.split(sep) if item.strip()]


# --- Network ---
NETWORK: list[str] = env_list("NETWORK")

# --- MQTT ---
MQTT_BROKER: str = env("MQTT_BROKER")
if not MQTT_BROKER:
    raise ValueError("MQTT_BROKER environment variable is required.")
MQTT_PORT: int = env("MQTT_PORT", default=1883, cast=int)
MQTT_USER: str | None = env("MQTT_USER")
MQTT_PASSWORD: str | None = env("MQTT_PASSWORD")
MQTT_TOPIC: str = env("MQTT_TOPIC", default="gree")
MQTT_QOS: int = env("MQTT_QOS", default=0, cast=int)
if MQTT_QOS not in (0, 1, 2):
    raise ValueError("MQTT_QOS must be 0, 1, or 2.")
MQTT_RETAIN: bool = env_bool("MQTT_RETAIN", default=False)
MQTT_KEEP_ALIVE: int = env("MQTT_KEEP_ALIVE", default=60, cast=int)

# --- Polling ---
UPDATE_INTERVAL: int = env("UPDATE_INTERVAL", default=3, cast=int)
ADAPTIVE_POLLING_TIMEOUT: int = env("ADAPTIVE_POLLING_TIMEOUT", default=45, cast=int)
ADAPTIVE_FAST_INTERVAL: float = env("ADAPTIVE_FAST_INTERVAL", default=0.8, cast=float)

# --- Event queue ---
EVENT_QUEUE_WORKERS: int = env("EVENT_QUEUE_WORKERS", default=5, cast=int)
IMMEDIATE_RESPONSE_TIMEOUT: float = env("IMMEDIATE_RESPONSE_TIMEOUT", default=5.0, cast=float)

# --- Tracking params ---
DEFAULT_PARAMS = (
    "Pow,Mod,SetTem,TemUn,WdSpd,Air,Blo,Health,SwhSlp,Lig,SwingLfRig,"
    "SwUpDn,Quiet,Tur,StHt,HeatCoolType,TemRec,SvSt,TemSen"
)
TRACKING_PARAMS: list[str] = env_list("TRACKING_PARAMS") or [
    p.strip() for p in DEFAULT_PARAMS.split(",") if p.strip()
]

# --- Logging ---
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


log.debug(
    "Initialized GreeMQTT with",
    network=NETWORK,
    update_interval=UPDATE_INTERVAL,
    params=TRACKING_PARAMS,
)
