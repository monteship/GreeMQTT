import os
from typing import List

from dotenv import load_dotenv

from GreeMQTT.logger import log

load_dotenv()

NETWORK: List[str] | str = os.getenv("NETWORK")
if isinstance(NETWORK, str):
    NETWORK = [net.strip() for net in NETWORK.split(",") if net.strip()]

MQTT_BROKER: str = os.getenv("MQTT_BROKER")
MQTT_PORT: int = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER: str = os.getenv("MQTT_USER")
MQTT_PASSWORD: str = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "gree")
MQTT_QOS: int = int(os.getenv("MQTT_QOS", 0))
if MQTT_QOS not in [0, 1, 2]:
    raise ValueError("MQTT_QOS environment variable must be 0, 1, or 2.")
MQTT_RETAIN: bool = os.getenv("MQTT_RETAIN", 'False').lower() in ['true', '1', 'yes']
MQTT_KEEP_ALIVE: int = int(os.getenv("MQTT_KEEP_ALIVE", 60))

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

UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", 3))
ADAPTIVE_POLLING_TIMEOUT: int = int(os.getenv("ADAPTIVE_POLLING_TIMEOUT", 45))
ADAPTIVE_FAST_INTERVAL: float = float(os.getenv("ADAPTIVE_FAST_INTERVAL", 0.8))

EVENT_QUEUE_WORKERS: int = int(os.getenv("EVENT_QUEUE_WORKERS", 5))
IMMEDIATE_RESPONSE_TIMEOUT: float = float(os.getenv("IMMEDIATE_RESPONSE_TIMEOUT", 5.0))

DEFAULT_PARAMS = (
    "Pow,Mod,SetTem,TemUn,WdSpd,Air,Blo,Health,SwhSlp,Lig,SwingLfRig,"
    "SwUpDn,Quiet,Tur,StHt,HeatCoolType,TemRec,SvSt,TemSen"
)
TRACKING_PARAMS: List[str] | str = os.getenv("TRACKING_PARAMS", DEFAULT_PARAMS)
if isinstance(TRACKING_PARAMS, str):
    TRACKING_PARAMS = [param.strip() for param in TRACKING_PARAMS.split(",") if param.strip()]

log.debug(
    "Initialized GreeMQTT with",
    network=NETWORK,
    update_interval=UPDATE_INTERVAL,
    params=TRACKING_PARAMS,
)
