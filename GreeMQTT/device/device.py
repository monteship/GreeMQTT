import datetime
import json
import re
from typing import Self

from GreeMQTT.config import settings
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
        key: str | None = None,
    ):
        self.device_ip = device_ip
        self.device_id = device_id
        self.name = name
        self.is_GCM = is_GCM
        self.key = key
        self.communicator = DeviceCommunicator(device_ip)

    @property
    def topic(self) -> str:
        return f"{settings.mqtt_topic}/{self.device_id}"

    @property
    def set_topic(self) -> str:
        return f"{self.topic}/set"

    def __str__(self):
        return f"Device(ip={self.device_ip}, id={self.device_id}, name={self.name}, GCM={self.is_GCM})"

    def __repr__(self):
        return self.__str__()

    def _encrypt(self, pack: str) -> dict:
        return encrypt(pack, self.key, self.is_GCM)

    def _decrypt(self, response: dict) -> dict:
        return decrypt(response, self.key, self.is_GCM)

    def _encrypt_request(self, pack: str) -> str:
        request = {"cid": "app", "i": 0, "t": "pack", "uid": 0, "tcid": self.device_id}
        request.update(self._encrypt(pack))
        return json.dumps(request)

    def _decrypt_response(self, response: dict) -> dict[str, str | int]:
        decrypted = self._decrypt(response)
        if "cols" not in decrypted:
            return decrypted
        return dict(zip(decrypted["cols"], decrypted["dat"]))

    def _send(self, request: bytes) -> bytes | None:
        return self.communicator.send_data(request)

    def bind(self, max_retries: int = DEVICE_BIND_MAX_RETRIES) -> Self | None:
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

    def get_param(self) -> dict | None:
        cols = ",".join(f'"{p}"' for p in settings.tracking_params_list)
        status_pack = f'{{"cols":[{cols}],"mac":"{self.device_id}","t":"status"}}'
        request = self._encrypt_request(status_pack)
        result = self._send(request.encode())
        if not result:
            log.error("Failed to get parameters from device", device_id=self.device_id)
            return None
        response = json.loads(result)
        if response.get("t") == "pack":
            params = self._decrypt_response(response)
            return DeviceParamConverter.from_device(params)
        return {}

    def set_params(self, params: dict) -> dict[str, str | int] | None:

        converted = DeviceParamConverter.to_device(params)
        pack = json.dumps({"opt": list(converted.keys()), "p": list(converted.values()), "t": "cmd"})
        request = self._encrypt_request(pack)
        result = self._send(request.encode())
        if not result:
            return None
        response = json.loads(result)
        if response.get("t") == "pack":
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
    def from_scan_response(cls, raw_data: bytes, ip_address: str, skip_bind_ids: set[str] | None = None) -> Self | None:
        """Create and bind a Device from a raw broadcast scan response.

        If skip_bind_ids is provided, devices with those IDs will not be bound (returns None).
        """
        raw_json = raw_data[: raw_data.rfind(b"}") + 1]
        try:
            response = json.loads(raw_json)
        except json.JSONDecodeError as e:
            log.error("Failed to parse scan response", ip_address=ip_address, error=str(e))
            return None

        is_GCM = "tag" in response
        decrypted = decrypt(response, is_GCM=is_GCM)
        name = decrypted.get("name", "Unknown")
        cid: str | None = decrypted.get("cid", response.get("cid")) or decrypted.get("mac")
        if not cid:
            log.error("Device ID (cid) not found in response", response=decrypted)
            return None

        if skip_bind_ids and cid in skip_bind_ids:
            log.debug("Skipping bind for already active device", device_id=cid)
            return None

        if not is_GCM and "ver" in decrypted:
            ver = re.search(r"(?<=V)[0-9]+(?<=.)", decrypted["ver"])
            if ver and int(ver.group(0)) >= 2:
                log.info("Set GCM encryption because version in search response is 2 or later")
                is_GCM = True

        device = cls(device_ip=ip_address, device_id=cid, name=name, is_GCM=is_GCM)
        return device.bind()

    @classmethod
    def search_devices(cls, ip_address: str) -> Self | None:
        log.info("Searching for device", ip_address=ip_address)
        result = DeviceCommunicator.broadcast_scan(ip_address)
        if not result:
            return None
        return cls.from_scan_response(result, ip_address)

    @classmethod
    def discover_all(cls, broadcast_address: str = "192.168.1.255", skip_bind_ids: set[str] | None = None) -> list[Self]:
        """Discover all Gree devices on the network via a single UDP broadcast."""
        responses = DeviceCommunicator.broadcast_discovery(broadcast_address)
        devices: list[Self] = []
        for raw_data, ip in responses:
            device = cls.from_scan_response(raw_data, ip, skip_bind_ids=skip_bind_ids)
            if device:
                devices.append(device)
        return devices

