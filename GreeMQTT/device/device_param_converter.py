from datetime import UTC, datetime
from typing import Any, Dict

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


class DeviceParamConverter:
    """
    Handles conversion between human-readable and device-specific parameter formats.
    """

    @staticmethod
    def to_device(params: Dict[str, Any]) -> Dict[str, Any]:
        result = params.copy()
        for key, value in params.items():
            if key in CONVERT_PARAMS:
                inv_map = {v: k for k, v in CONVERT_PARAMS[key].items()}
                result[key] = inv_map.get(value, value)
            else:
                result[key] = value
        return result

    @staticmethod
    def from_device(params: Dict[str, Any]) -> Dict[str, Any]:
        result = params.copy()
        for key, value in params.items():
            if key in CONVERT_PARAMS:
                result[key] = CONVERT_PARAMS[key].get(value, value)
            else:
                result[key] = value
        if "SetTem" in result and "TemSen" in result:
            result["TemSen"] = result["TemSen"] - 40
        result["last_seen"] = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        return result
