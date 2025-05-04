import os

from typing import Optional, List
from dotenv import load_dotenv


# Load environment variables
load_dotenv()
NETWORK: List[str] = os.getenv(
    "NETWORK", "192.168.1.40,192.168.1.41,192.168.1.42"
).split(",")

# Set MQTT parameters
MQTT_BROKER: str = os.getenv("MQTT_BROKER", "192.168.1.10")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER: Optional[str] = os.getenv("MQTT_USER")
MQTT_PASSWORD: Optional[str] = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC: str = os.getenv("MQTT_TOPIC", "gree")

# Set update interval
UPDATE_INTERVAL: int = int(os.getenv("UPDATE_INTERVAL", 4))

# Set default tracking parameters
# Pow,Mod,SetTem,TemUn,WdSpd,Air,Blo,Health,SwhSlp,Lig,SwingLfRig,SwUpDn,Quiet,Tur,StHt,HeatCoolType,TemRec,SvSt,TemSen
TRACKING_PARAMS: List[str] = os.getenv(
    "TRACKING_PARAMS",
    "Pow,Mod,SetTem,WdSpd,SwhSlp,Lig,SwUpDn,Quiet,Tur,StHt,TemSen",
).split(",")
