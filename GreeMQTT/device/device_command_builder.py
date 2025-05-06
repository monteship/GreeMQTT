import json
from GreeMQTT.config import TRACKING_PARAMS


class DeviceCommandBuilder:
    @staticmethod
    def bind(device_id: str) -> str:
        return json.dumps({"mac": device_id, "t": "bind", "uid": 0})

    @staticmethod
    def status(device_id: str) -> str:
        cols = ",".join(f'"{i}"' for i in TRACKING_PARAMS)
        return f'{{"cols":[{cols}],"mac":"{device_id}","t":"status"}}'

    @staticmethod
    def set_params(params: dict) -> str:
        opts, ps = zip(*[(f'"{k}"', str(v)) for k, v in params.items()])
        return f'{{"opt":[{",".join(opts)}],"p":[{",".join(ps)}],"t":"cmd"}}'
