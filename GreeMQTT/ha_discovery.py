"""Home Assistant MQTT Auto-Discovery for Gree devices.

Publishes discovery configs so HA automatically creates climate entities.
See: https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery
"""

import json

import paho.mqtt.client as paho_mqtt

from GreeMQTT.config import settings
from GreeMQTT.device.device import Device
from GreeMQTT.logger import log

HA_DISCOVERY_PREFIX = "homeassistant"


def publish_ha_discovery(device: Device, mqtt_client: paho_mqtt.Client) -> None:
    """Publish MQTT discovery configs for a Gree device as a climate + sensors."""
    device_info = {
        "identifiers": [device.device_id],
        "name": device.name or device.device_id,
        "manufacturer": "Gree",
        "model": "Smart AC",
        "sw_version": "GreeMQTT",
    }

    node_id = device.device_id.replace(":", "_").replace("-", "_")
    state_topic = device.topic
    set_topic = device.set_topic

    # --- Climate entity ---
    climate_config = {
        "name": None,  # Use device name
        "unique_id": f"gree_{node_id}_climate",
        "device": device_info,
        "availability_topic": f"{settings.mqtt_topic}/status",
        "payload_available": "online",
        "payload_not_available": "offline",
        # Topics
        "current_temperature_topic": state_topic,
        "current_temperature_template": "{{ value_json.TemSen }}",
        "temperature_command_topic": set_topic,
        "temperature_command_template": '{"SetTem": {{ value }} }',
        "temperature_state_topic": state_topic,
        "temperature_state_template": "{{ value_json.SetTem }}",
        # Mode
        "mode_command_topic": set_topic,
        "mode_command_template": '{"Pow": {% if value == "off" %}0, "Mod": 0{% else %}1, "Mod": "{{ value }}"{% endif %} }',
        "mode_state_topic": state_topic,
        "mode_state_template": "{% if value_json.Pow == 'off' %}off{% else %}{{ value_json.Mod }}{% endif %}",
        "modes": ["off", "auto", "cool", "heat", "dry", "fan_only"],
        # Fan
        "fan_mode_command_topic": set_topic,
        "fan_mode_command_template": '{"WdSpd": "{{ value }}" }',
        "fan_mode_state_topic": state_topic,
        "fan_mode_state_template": "{{ value_json.WdSpd }}",
        "fan_modes": ["auto", "low", "medium-low", "medium", "medium-high", "high"],
        # Swing
        "swing_mode_command_topic": set_topic,
        "swing_mode_command_template": '{"SwUpDn": "{{ value }}" }',
        "swing_mode_state_topic": state_topic,
        "swing_mode_state_template": "{{ value_json.SwUpDn }}",
        "swing_modes": ["default", "full_swing", "fixed_upmost", "fixed_middle_up",
                        "fixed_middle", "fixed_middle_low", "fixed_lowest"],
        # Temp range
        "min_temp": 16,
        "max_temp": 30,
        "temp_step": 1,
        "temperature_unit": "C",
    }

    climate_topic = f"{HA_DISCOVERY_PREFIX}/climate/{node_id}/config"
    mqtt_client.publish(
        climate_topic,
        json.dumps(climate_config, separators=(",", ":")),
        qos=settings.mqtt_qos,
        retain=True,
    )
    log.info("Published HA discovery config", device_id=device.device_id, topic=climate_topic)

    # --- Binary sensors for simple on/off states ---
    binary_sensors = {
        "Tur": "Turbo",
        "Quiet": "Quiet Mode",
        "Health": "Health Mode",
        "Lig": "Display Light",
        "SwhSlp": "Sleep Mode",
    }

    for param, friendly_name in binary_sensors.items():
        sensor_config = {
            "name": friendly_name,
            "unique_id": f"gree_{node_id}_{param.lower()}",
            "device": device_info,
            "state_topic": state_topic,
            "value_template": f"{{{{ value_json.{param} }}}}",
            "payload_on": "on",
            "payload_off": "off",
            "availability_topic": f"{settings.mqtt_topic}/status",
            "payload_available": "online",
            "payload_not_available": "offline",
        }
        sensor_topic = f"{HA_DISCOVERY_PREFIX}/binary_sensor/{node_id}_{param.lower()}/config"
        mqtt_client.publish(
            sensor_topic,
            json.dumps(sensor_config, separators=(",", ":")),
            qos=settings.mqtt_qos,
            retain=True,
        )

    log.debug("Published HA binary sensor configs", device_id=device.device_id, count=len(binary_sensors))

