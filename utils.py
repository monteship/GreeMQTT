from datetime import datetime, UTC

CONVERT_PARAMS = {
    "Pow": {
        0: "off",
        1: "on",
    },
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
    "Air": {
        0: "off",
        1: "on",
    },
    "Blo": {
        0: "off",
        1: "on",
    },
    "Health": {
        0: "off",
        1: "on",
    },
    "SwhSlp": {
        0: "off",
        1: "on",
    },
    "Lig": {
        0: "off",
        1: "on",
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
    "Quiet": {
        0: "off",
        1: "on",
    },
    "Tur": {
        0: "off",
        1: "on",
    },
    "StHt": {
        0: "off",
        1: "on",
    },
}


def params_convert(params: dict, back=False) -> dict:
    """Convert parameters to a dictionary."""
    params_dict = {}
    if back:
        for key, value in params.items():
            if key in CONVERT_PARAMS:
                for k, v in CONVERT_PARAMS[key].items():
                    if v == value:
                        params_dict[key] = k
                        break
            else:
                params_dict[key] = value
        return params_dict

    for key, value in params.items():
        if key in CONVERT_PARAMS:
            params_dict[key] = CONVERT_PARAMS[key].get(value, value)
        else:
            params_dict[key] = value

    if "SetTem" in params_dict:
        params_dict["TemSen"] = params_dict["TemSen"] - 40

    params_dict["last_seen"] = (
        datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    )

    return params_dict
