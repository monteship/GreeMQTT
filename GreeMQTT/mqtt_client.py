import aiomqtt
from aiomqtt import Will
from GreeMQTT.config import (
    MQTT_BROKER,
    MQTT_TOPIC,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USER,
    MQTT_QOS,
    MQTT_KEEP_ALIVE,
)


async def create_mqtt_client() -> aiomqtt.Client:
    client = aiomqtt.Client(
        hostname=MQTT_BROKER,
        port=MQTT_PORT,
        keepalive=MQTT_KEEP_ALIVE,
        will=Will(
            topic=f"{MQTT_TOPIC}/status",
            payload="offline",
            qos=MQTT_QOS,
            retain=True,
        ),
        username=MQTT_USER,
        password=MQTT_PASSWORD,
    )
    return client
