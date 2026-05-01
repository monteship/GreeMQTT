import datetime
import json
import re
from typing import Self

from GreeMQTT.config import settings
from GreeMQTT.device.device_communication import discover_devices, scan_device, send_udp
from GreeMQTT.device.device_param_converter import DeviceParamConverter
from GreeMQTT.encryptor import decrypt, encrypt
from GreeMQTT.logger import log


class Device:
    def __init__(self, device_ip: str, device_id: str, name: str, is_GCM: bool = False, key: str | None = None):
        self.device_ip = device_ip
        self.device_id = device_id
        self.name = name
        self.is_GCM = is_GCM
        self.key = key

    @property
    def topic(self) -> str:
        return f"{settings.mqtt_topic}/{self.device_id}"

    @property
    def set_topic(self) -> str:
        return f"{self.topic}/set"

    def __str__(self):
        return f"Device(ip={self.device_ip}, id={self.device_id}, name={self.name}, GCM={self.is_GCM})"

    __repr__ = __str__

    def _send_pack(self, pack: str, i: int = 0) -> dict | None:
        """Encrypt, send, and decrypt a pack. Returns the decrypted response dict or None."""
        req = {"cid": "app", "i": i, "t": "pack", "uid": 0, "tcid": self.device_id}
        req.update(encrypt(pack, self.key, self.is_GCM))
        result = send_udp(self.device_ip, json.dumps(req).encode())
        if not result:
            return None
        response = json.loads(result)
        if response.get("t") != "pack":
            return None
        decrypted = decrypt(response, self.key, self.is_GCM)
        return dict(zip(decrypted["cols"], decrypted["dat"])) if "cols" in decrypted else decrypted

    def bind(self) -> Self | None:
        log.info("Binding to device", device_id=self.device_id)
        for gcm in ([self.is_GCM] if self.is_GCM else [False, True]):
            pack = json.dumps({"mac": self.device_id, "t": "bind", "uid": 0})
            req = {"cid": "app", "i": 1, "t": "pack", "uid": 0, "tcid": self.device_id}
            req.update(encrypt(pack, self.key, gcm))
            result = send_udp(self.device_ip, json.dumps(req).encode())
            if not result:
                continue
            decrypted = decrypt(json.loads(result), self.key, gcm)
            if decrypted.get("t", "").lower() == "bindok":
                self.key = decrypted["key"]
                self.is_GCM = gcm
                log.info("Bind succeeded", device_id=self.device_id)
                return self
        log.error("Bind failed", device_id=self.device_id)
        return None

    def get_param(self) -> dict | None:
        pack = json.dumps({"cols": settings.tracking_params_list, "mac": self.device_id, "t": "status"})
        result = self._send_pack(pack)
        return DeviceParamConverter.from_device(result) if result else None

    def set_params(self, params: dict) -> dict | None:
        converted = DeviceParamConverter.to_device(params)
        pack = json.dumps({"opt": list(converted.keys()), "p": list(converted.values()), "t": "cmd"})
        return self._send_pack(pack)

    def synchronize_time(self) -> None:
        response = self.set_params({"time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")})
        if response is not None:
            log.info("Time synchronized", device_id=self.device_id)
        else:
            log.warning("Failed to synchronize time", device_id=self.device_id)

    @classmethod
    def from_scan_response(cls, raw_data: bytes, ip: str, skip_bind_ids: set[str] | None = None) -> Self | None:
        try:
            response = json.loads(raw_data[: raw_data.rfind(b"}") + 1])
        except json.JSONDecodeError as e:
            log.error("Failed to parse scan response", ip=ip, error=str(e))
            return None

        is_GCM = "tag" in response
        decrypted = decrypt(response, is_GCM=is_GCM)
        cid = decrypted.get("cid") or response.get("cid") or decrypted.get("mac")
        if not cid or not isinstance(cid, str):
            log.error("Device ID not found in scan response", ip=ip)
            return None
        if skip_bind_ids and cid in skip_bind_ids:
            return None

        if not is_GCM and "ver" in decrypted:
            ver = re.search(r"(?<=V)\d+", decrypted["ver"])
            if ver and int(ver.group()) >= 2:
                is_GCM = True

        return cls(device_ip=ip, device_id=cid, name=decrypted.get("name", "Unknown"), is_GCM=is_GCM).bind()

    @classmethod
    def search_devices(cls, ip: str) -> Self | None:
        result = scan_device(ip)
        return cls.from_scan_response(result, ip) if result else None

    @classmethod
    def discover_all(cls, broadcast_address: str, skip_bind_ids: set[str] | None = None) -> list[Self]:
        devices = [cls.from_scan_response(raw, ip, skip_bind_ids=skip_bind_ids)
                   for raw, ip in discover_devices(broadcast_address)]
        return [d for d in devices if d is not None]
