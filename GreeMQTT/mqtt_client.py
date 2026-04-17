import threading

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
from GreeMQTT.logger import log

_mqtt_client: paho_mqtt.Client | None = None
_mqtt_lock = threading.Lock()

RECONNECT_DELAY_MIN = 1
RECONNECT_DELAY_MAX = 60


def _on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log.info("MQTT connected", broker=MQTT_BROKER, port=MQTT_PORT)
        client.publish(f"{MQTT_TOPIC}/status", "online", qos=MQTT_QOS, retain=True)
        # Re-subscribe to all previously subscribed topics
        for topic, qos in getattr(client, "_subscribed_topics", {}).items():
            client.subscribe(topic, qos=qos)
            log.debug("Re-subscribed after reconnect", topic=topic)
    else:
        log.error("MQTT connection failed", rc=rc)


def _on_disconnect(client, userdata, flags, rc, properties=None):
    if rc != 0:
        log.warning("MQTT disconnected unexpectedly, will auto-reconnect", rc=rc)


def create_mqtt_client() -> paho_mqtt.Client:
    """Return a shared MQTT client, creating it on first call."""
    global _mqtt_client
    with _mqtt_lock:
        if _mqtt_client is not None:
            return _mqtt_client

        client = paho_mqtt.Client(paho_mqtt.CallbackAPIVersion.VERSION2)
        client._subscribed_topics = {}  # track subscriptions for re-subscribe on reconnect

        client.on_connect = _on_connect
        client.on_disconnect = _on_disconnect

        client.will_set(
            topic=f"{MQTT_TOPIC}/status",
            payload="offline",
            qos=MQTT_QOS,
            retain=True,
        )
        if MQTT_USER and MQTT_PASSWORD:
            client.username_pw_set(MQTT_USER, MQTT_PASSWORD)

        client.reconnect_delay_set(RECONNECT_DELAY_MIN, RECONNECT_DELAY_MAX)
        client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEP_ALIVE)
        client.loop_start()
        _mqtt_client = client
        return _mqtt_client


def subscribe_topic(topic: str, qos: int = MQTT_QOS):
    """Subscribe and track the topic for automatic re-subscription on reconnect."""
    client = create_mqtt_client()
    client._subscribed_topics[topic] = qos
    client.subscribe(topic, qos=qos)


def shutdown_mqtt():
    """Gracefully disconnect the shared MQTT client."""
    global _mqtt_client
    with _mqtt_lock:
        if _mqtt_client is not None:
            try:
                _mqtt_client.publish(f"{MQTT_TOPIC}/status", "offline", qos=MQTT_QOS, retain=True)
                _mqtt_client.loop_stop()
                _mqtt_client.disconnect()
                log.info("MQTT client disconnected gracefully")
            except Exception as e:
                log.error("Error during MQTT shutdown", error=str(e))
            _mqtt_client = None
