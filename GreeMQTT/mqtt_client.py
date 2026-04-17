import paho.mqtt.client as paho_mqtt

from GreeMQTT.config import (
    MQTT_BROKER,
    MQTT_KEEP_ALIVE,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_QOS,
    MQTT_TOPIC,
    MQTT_USER,
)


def create_mqtt_client() -> paho_mqtt.Client:
    client = paho_mqtt.Client(paho_mqtt.CallbackAPIVersion.VERSION2)
    client.will_set(
        topic=f"{MQTT_TOPIC}/status",
        payload="offline",
        qos=MQTT_QOS,
        retain=True,
    )
    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEP_ALIVE)
    client.loop_start()
    return client
