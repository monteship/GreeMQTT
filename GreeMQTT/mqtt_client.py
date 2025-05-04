import paho.mqtt.client as mqtt
from GreeMQTT.config import (
    MQTT_BROKER,
    MQTT_PASSWORD,
    MQTT_PORT,
    MQTT_USER,
)

LWT_TOPIC = "gree/status"
LWT_PAYLOAD = "offline"
LWT_QOS = 1
LWT_RETAIN = True


def create_mqtt_client() -> mqtt.Client:
    client = mqtt.Client(
        callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        client_id="gree_mqtt_client",
    )
    # Set Last Will and Testament (LWT)
    client.will_set(LWT_TOPIC, payload=LWT_PAYLOAD, qos=LWT_QOS, retain=LWT_RETAIN)
    if MQTT_USER and MQTT_PASSWORD:
        client.username_pw_set(MQTT_USER, MQTT_PASSWORD)
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_start()
    return client
