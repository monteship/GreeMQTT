import json

from GreeMQTT.config import TRACKING_PARAMS


class DeviceCommandBuilder:
    @staticmethod
    def bind(device_id: str) -> str:
        data = {"mac": device_id, "t": "bind", "uid": 0}
        return json.dumps(data)

    @staticmethod
    def status(device_id: str) -> str:
        cols = ",".join(f'"{i}"' for i in TRACKING_PARAMS)
        return f'{{"cols":[{cols}],"mac":"{device_id}","t":"status"}}'

    @staticmethod
    def set_params(params: dict) -> str:
        data = {
            "opt": list(params.keys()),
            "p": list(params.values()),
            "t": "cmd",
        }
        return json.dumps(data)
