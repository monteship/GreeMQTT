import os

from typing import Optional, List, Union
from dotenv import load_dotenv
from GreeMQTT.logger import log

# Load environment variables
load_dotenv()
NETWORK: Union[Optional[str], List[str]] = os.getenv("NETWORK")
if not NETWORK:
    raise ValueError(
        "NETWORK environment variable is not set. Please set it to a comma-separated list of IP addresses."
    )
else:
    NETWORK = NETWORK.split(",")

# Set MQTT parameters
MQTT_BROKER: Optional[str] = os.getenv("MQTT_BROKER")
if not MQTT_BROKER:
    raise ValueError(
        "MQTT_BROKER environment variable is not set. Please set it to the MQTT broker address."
    )

MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER: Optional[str] = os.getenv("MQTT_USER")
MQTT_PASSWORD: Optional[str] = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "gree")
MQTT_QOS: int = int(os.getenv("MQTT_QOS", 0))
if MQTT_QOS not in [0, 1, 2]:
    raise ValueError(
        "MQTT_QOS environment variable must be 0, 1, or 2. Please set it to a valid QoS level."
    )
MQTT_RETAIN: bool = os.getenv("MQTT_RETAIN", "false").lower() == "true"
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


# Set update interval
UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", 4))

# Set default tracking parameters
DEFAULT_PARAMS = (
    "Pow,Mod,SetTem,TemUn,WdSpd,Air,Blo,Health,SwhSlp,Lig,SwingLfRig,"
    "SwUpDn,Quiet,Tur,StHt,HeatCoolType,TemRec,SvSt,TemSen"
)
TRACKING_PARAMS: Union[Optional[str], List[str]] = os.getenv(
    "TRACKING_PARAMS", DEFAULT_PARAMS
)

TRACKING_PARAMS = TRACKING_PARAMS.split(",")
log.debug(
    "Initialized GreeMQTT with",
    network=NETWORK,
    update_interval=UPDATE_INTERVAL,
    params=TRACKING_PARAMS,
)
