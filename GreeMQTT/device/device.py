import datetime
import json
import re
from typing import Dict, Optional, Self

from GreeMQTT.config import MQTT_TOPIC, TRACKING_PARAMS
from GreeMQTT.device.device_communication import DeviceCommunicator
from GreeMQTT.device.device_param_converter import DeviceParamConverter
from GreeMQTT.encryptor import decrypt, encrypt
from GreeMQTT.logger import log

DEVICE_BIND_MAX_RETRIES = 2


class Device:
    def __init__(
        self,
        device_ip: str,
        device_id: str,
        name: str,
        is_GCM: bool = False,
        key: Optional[str] = None,
    ):
        self.device_ip = device_ip
        self.device_id = device_id
        self.name = name
        self.is_GCM = is_GCM
        self.key = key
        self.communicator = DeviceCommunicator(device_ip)

    @property
    def topic(self) -> str:
        return f"{MQTT_TOPIC}/{self.device_id}"

    @property
    def set_topic(self) -> str:
        return f"{self.topic}/set"

    def __str__(self):
        return f"Device(device_ip={self.device_ip}, device_id={self.device_id}, is_GCM={self.is_GCM})"

    def _encrypt(self, pack: str) -> dict:
        return encrypt(pack, self.key, self.is_GCM)

    def _decrypt(self, response: dict) -> dict:
        return decrypt(response, self.key, self.is_GCM)

    def _encrypt_request(self, pack: str) -> str:
        request = {"cid": "app", "i": 0, "t": "pack", "uid": 0, "tcid": self.device_id}
        request.update(self._encrypt(pack))
        return json.dumps(request)

    def _decrypt_response(self, response: dict) -> Dict[str, str | int]:
        decrypted = self._decrypt(response)
        if "cols" not in decrypted:
            return decrypted
        return dict(zip(decrypted["cols"], decrypted["dat"]))

    def _send(self, request: bytes) -> Optional[bytes]:
        return self.communicator.send_data(request)

    def bind(self, max_retries: int = DEVICE_BIND_MAX_RETRIES) -> Optional[Self]:
        log.info("Binding to device", device=self.device_id)
        for retry in range(max_retries):
            pack = json.dumps({"mac": self.device_id, "t": "bind", "uid": 0})
            encrypted = self._encrypt(pack)
            request = {"cid": "app", "i": 1, "t": "pack", "uid": 0, "tcid": self.device_id}
            request.update(encrypted)
            data = json.dumps(request).encode()

            log.debug("Bind request sent", device_id=self.device_id, request=data.decode(), retry=retry)
            result = self._send(data)

            if not result:
                if not self.is_GCM:
                    self.is_GCM = True
                    log.info("Retrying bind with GCM encryption", device_id=self.device_id)
                    continue
                log.error("Failed to bind to device", device_id=self.device_id)
                return None

            response = json.loads(result)
            if response.get("t") != "pack":
                log.error("Unexpected response during bind", device_id=self.device_id, response=response)
                return None

            decrypted = self._decrypt(response)
            if decrypted.get("t", "").lower() == "bindok":
                self.key = decrypted["key"]
                log.info("Bind succeeded", device_id=self.device_id, key=self.key)
                return self

            log.error("Bind failed", device_id=self.device_id, response=decrypted)
            return None

        log.error("Bind failed after maximum retries", device_id=self.device_id)
        return None

    def get_param(self) -> Optional[Dict]:
        from GreeMQTT import device_db

        cols = ",".join(f'"{p}"' for p in TRACKING_PARAMS)
        status_pack = f'{{"cols":[{cols}],"mac":"{self.device_id}","t":"status"}}'
        request = self._encrypt_request(status_pack)
        result = self._send(request.encode())
        if not result:
            log.error("Failed to get parameters from device", device_id=self.device_id)
            return None
        response = json.loads(result)
        if response.get("t") == "pack":
            params = self._decrypt_response(response)
            device_db.update_seen_at(self.device_id)
            return DeviceParamConverter.from_device(params)
        return {}

    def set_params(self, params: dict) -> dict[str, str | int] | None:
        from GreeMQTT import device_db

        converted = DeviceParamConverter.to_device(params)
        pack = json.dumps({"opt": list(converted.keys()), "p": list(converted.values()), "t": "cmd"})
        request = self._encrypt_request(pack)
        result = self._send(request.encode())
        if not result:
            return None
        response = json.loads(result)
        if response.get("t") == "pack":
            device_db.update_seen_at(self.device_id)
            return self._decrypt_response(response)
        return None

    def synchronize_time(self) -> None:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response = self.set_params({"time": current_time})
        if response is not None:
            log.info("Synchronized time with device", device_id=self.device_id,
                     opt=response.get("opt"), p=response.get("p"),
                     val=response.get("val"), r=response.get("r"))
        else:
            log.error("Failed to synchronize time with device", device_id=self.device_id)

    @classmethod
    def search_devices(cls, ip_address: str) -> Optional[Self]:
        log.info("Searching for devices using broadcast address", ip_address=ip_address)
        result = DeviceCommunicator.broadcast_scan(ip_address)
        if not result:
            return None
        raw_json = result[: result.rfind(b"}") + 1]
        try:
            response = json.loads(raw_json)
        except json.JSONDecodeError as e:
            log.error("Failed to parse search response", ip_address=ip_address, error=str(e))
            return None

        is_GCM = "tag" in response
        decrypted = decrypt(response, is_GCM=is_GCM)
        name = decrypted.get("name", "Unknown")
        cid = decrypted.get("cid", response.get("cid")) or decrypted.get("mac")
        if not cid:
            log.error("Device ID (cid) not found in response", response=decrypted)
            return None

        if not is_GCM and "ver" in decrypted:
            ver = re.search(r"(?<=V)[0-9]+(?<=.)", decrypted["ver"])
            if ver and int(ver.group(0)) >= 2:
                log.info("Set GCM encryption because version in search responce is 2 or later")
                is_GCM = True

        device = cls(device_ip=ip_address, device_id=cid, name=name, is_GCM=is_GCM)
        return device.bind()
