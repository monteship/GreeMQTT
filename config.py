import os

from dotenv import load_dotenv


# Load environment variables
load_dotenv()
NETWORK = os.getenv("NETWORK", "localhost").split(",")

# Set MQTT parameters
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_USER = os.getenv("MQTT_USER", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "gree")

# Set update interval
UPDATE_INTERVAL = int(os.getenv("UPDATE_INTERVAL", 4))

# Set default tracking parameters
# Pow,Mod,SetTem,TemUn,WdSpd,Air,Blo,Health,SwhSlp,Lig,SwingLfRig,SwUpDn,Quiet,Tur,StHt,HeatCoolType,TemRec,SvSt,TemSen
TRACKING_PARAMS = os.getenv(
    "TRACKING_PARAMS",
    "Pow,Mod,SetTem,WdSpd,SwhSlp,Lig,SwUpDn,Quiet,Tur,StHt,TemSen",
).split(",")
