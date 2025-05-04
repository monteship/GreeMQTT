from datetime import datetime, UTC
from typing import Dict, Any

CONVERT_PARAMS: Dict[str, Dict[int, str]] = {
    "Mod": {
        0: "auto",
        1: "cool",
        2: "dry",
        3: "fan_only",
        4: "heat",
    },
    "TemUn": {
        0: "celsius",
        1: "fahrenheit",
    },
    "WdSpd": {
        0: "auto",
        1: "low",
        2: "medium-low",
        3: "medium",
        4: "medium-high",
        5: "high",
    },
    "SwingLfRig": {
        0: "default",
        1: "full_swing",
        2: "fixed_leftmost",
        3: "fixed_middle_left",
        4: "fixed_middle",
        5: "fixed_middle_right",
        6: "fixed_rightmost",
    },
    "SwUpDn": {
        0: "default",
        1: "full_swing",
        2: "fixed_upmost",
        3: "fixed_middle_up",
        4: "fixed_middle",
        5: "fixed_middle_low",
        6: "fixed_lowest",
        7: "swing_downmost",
        8: "swing_middle_low",
        9: "swing_middle",
        10: "swing_middle_up",
        11: "swing_upmost",
    },
}
SIMPLE_STATE = ["Pow", "Air", "Blo", "Health", "SwhSlp", "Lig", "Quiet", "Tur", "StHt"]
for KEY in SIMPLE_STATE:
    CONVERT_PARAMS[KEY] = {0: "off", 1: "on"}


def params_convert(params: Dict[str, Any], back: bool = False) -> Dict[str, Any]:
    """
    Convert parameters between human-readable format and device format.
    :param params: Parameters to convert
    :param back: If True, convert from human-readable to device format
    :return: Converted parameters
    """
    result = params.copy()
    if back:
        for key, value in params.items():
            if key in CONVERT_PARAMS:
                inv_map = {v: k for k, v in CONVERT_PARAMS[key].items()}
                result[key] = inv_map.get(value, value)
            else:
                result[key] = value
        return result

    for key, value in params.items():
        if key in CONVERT_PARAMS:
            result[key] = CONVERT_PARAMS[key].get(value, value)
        else:
            result[key] = value

    if "SetTem" in result and "TemSen" in result:
        result["TemSen"] = result["TemSen"] - 40

    result["last_seen"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    return result


class DeviceRegistry:
    """
    Manages device topic-to-instance mapping.

    This class provides methods to register, retrieve, and unregister devices based on their MQTT topics.
    It acts as a central registry for devices, allowing other components to interact with devices
    by their associated topics.

    Usage:
        - Use `register(topic, device)` to add a device to the registry.
        - Use `get(topic)` to retrieve a device by its topic.
        - Use `unregister(topic)` to remove a device from the registry.

    Concurrency Considerations:
        - This class is not thread-safe. If accessed from multiple coroutines, external synchronization
          (e.g., using asyncio locks) is required to ensure thread safety.

    Device Lifecycle:
        - Devices should be registered when they are initialized and ready to handle MQTT messages.
        - Devices should be unregistered when they are no longer active or when the application shuts down.
    """

    def __init__(self):
        self._devices = {}

    def register(self, topic: str, device: "Device"):  # noqa: F821
        self._devices[topic] = device

    def get(self, topic: str):
        return self._devices.get(topic)

    def unregister(self, topic: str):
        if topic in self._devices:
            del self._devices[topic]
