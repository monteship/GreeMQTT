import threading

import paho.mqtt.client as paho_mqtt

from GreeMQTT.config import settings
from GreeMQTT.logger import log

_mqtt_client: paho_mqtt.Client | None = None
_mqtt_lock = threading.Lock()

RECONNECT_DELAY_MIN = 1
RECONNECT_DELAY_MAX = 60


def _on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        log.info("MQTT connected", broker=settings.mqtt_broker, port=settings.mqtt_port)
        client.publish(f"{settings.mqtt_topic}/status", "online", qos=settings.mqtt_qos, retain=True)
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
            topic=f"{settings.mqtt_topic}/status",
            payload="offline",
            qos=settings.mqtt_qos,
            retain=True,
        )
        if settings.mqtt_user and settings.mqtt_password:
            client.username_pw_set(settings.mqtt_user, settings.mqtt_password)

        client.reconnect_delay_set(RECONNECT_DELAY_MIN, RECONNECT_DELAY_MAX)
        client.connect(settings.mqtt_broker, settings.mqtt_port, settings.mqtt_keep_alive)
        client.loop_start()
        _mqtt_client = client
        return _mqtt_client


def subscribe_topic(topic: str, qos: int = settings.mqtt_qos):
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
                _mqtt_client.publish(f"{settings.mqtt_topic}/status", "offline", qos=settings.mqtt_qos, retain=True)
                _mqtt_client.loop_stop()
                _mqtt_client.disconnect()
                log.info("MQTT client disconnected gracefully")
            except Exception as e:
                log.error("Error during MQTT shutdown", error=str(e))
            _mqtt_client = None
