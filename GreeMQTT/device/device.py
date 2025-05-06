import datetime
import json
from typing import Optional, Dict, Self

from GreeMQTT.logger import log
from GreeMQTT.config import MQTT_TOPIC
from GreeMQTT.device.device_encryption import DeviceEncryptor
from GreeMQTT.device.device_param_converter import DeviceParamConverter
from GreeMQTT.device.device_communication import DeviceCommunicator
from GreeMQTT.device.device_command_builder import DeviceCommandBuilder


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
        self.encryptor = DeviceEncryptor(key, is_GCM)

    @property
    def topic(self) -> str:
        return f"{MQTT_TOPIC}/{self.device_id}"

    @property
    def set_topic(self) -> str:
        return f"{self.topic}/set"

    def __str__(self):
        return f"Device(device_ip={self.device_ip}, device_id={self.device_id}, is_GCM={self.is_GCM})"

    def encrypt_request(self, pack: str) -> str:
        request = {"cid": "app", "i": 0, "t": "pack", "uid": 0, "tcid": self.device_id}
        data_encrypted = self.encryptor.encrypt(pack)
        request.update(data_encrypted)
        return json.dumps(request)

    def decrypt_response(self, response: dict) -> Dict[str, str | int]:
        pack_decrypted = self.encryptor.decrypt(response)
        if "cols" not in pack_decrypted:
            return pack_decrypted
        return dict(zip(pack_decrypted["cols"], pack_decrypted["dat"]))

    async def _send_data(self, request: bytes) -> Optional[bytes]:
        return await self.communicator.send_data(request)

    async def bind(self, max_retries: int = 2) -> Optional[Self]:
        log.info("Binding to device", device=self.device_id)
        retries = 0
        while retries < max_retries:
            request = self._bind_request(1)
            result = await self._send_data(request)
            if not result:
                if not self.is_GCM:
                    self.is_GCM = True
                    self.encryptor.update_gcm(True)
                    retries += 1
                    continue
                return None
            response = json.loads(result)
            if response["t"] == "pack":
                decrypted_response = self.encryptor.decrypt(response)
                if (
                    "t" in decrypted_response
                    and decrypted_response["t"].lower() == "bindok"
                ):
                    key = decrypted_response["key"]
                    log.info("Bind succeeded", device_id=self.device_id, key=key)
                    self.key = key
                    self.encryptor.update_key(key)
                    return self
                return None
            return None
        log.error("Bind failed after maximum retries", device_id=self.device_id)
        return None

    def _bind_request(self, i=0) -> bytes:
        pack = DeviceCommandBuilder.bind(self.device_id)
        pack_encrypted = self.encryptor.encrypt(pack)
        request = {"cid": "app", "i": i, "t": "pack", "uid": 0, "tcid": self.device_id}
        request.update(pack_encrypted)
        return json.dumps(request).encode()

    async def get_param(self) -> Optional[Dict]:
        request = self.encrypt_request(DeviceCommandBuilder.status(self.device_id))
        result = await self._send_data(request.encode())
        if not result:
            log.error("Failed to get parameters from device", device_id=self.device_id)
            return None
        response = json.loads(result)
        if response["t"] == "pack":
            params = self.decrypt_response(response)
            return DeviceParamConverter.from_device(params)
        return {}

    async def set_params(self, params: dict) -> dict[str, str | int] | None:
        params = DeviceParamConverter.to_device(params)
        pack = DeviceCommandBuilder.set_params(params)
        request = self.encrypt_request(pack)
        result = await self._send_data(request.encode())
        if result:
            response = json.loads(result)
            if response["t"] == "pack":
                return self.decrypt_response(response)
            return None
        return None

    async def synchronize_time(self) -> None:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        response = await self.set_params({"time": current_time})
        if response is not None:
            log.info(
                "Synchronized time with device",
                device_id=self.device_id,
                opt=response.get("opt"),
                p=response.get("p"),
                val=response.get("val"),
                r=response.get("r"),
            )
        else:
            log.error(
                "Failed to synchronize time with device", device_id=self.device_id
            )

    def _status_request_pack(self) -> str:
        return DeviceCommandBuilder.status(self.device_id)

    @classmethod
    async def search_devices(cls, ip_address=None) -> Optional[Self]:
        log.info("Searching for devices using broadcast address", ip_address=ip_address)
        result = await DeviceCommunicator.broadcast_scan(ip_address)
        if not result:
            return None
        raw_json = result[: result.rfind(b"}") + 1]
        response = json.loads(raw_json)
        is_GCM = "tag" in response
        encryptor = DeviceEncryptor(is_GCM=is_GCM)
        decrypted_response = encryptor.decrypt(response)
        name = decrypted_response.get("name", "Unknown")
        cid = decrypted_response.get("cid", response.get("cid"))
        if not is_GCM and "ver" in decrypted_response:
            import re

            ver = re.search(r"(?<=V)[0-9]+(?<=.)", decrypted_response["ver"])
            if ver and int(ver.group(0)) >= 2:
                log.info(
                    "Set GCM encryption because version in search responce is 2 or later"
                )
                is_GCM = True
        device = cls(
            device_ip=ip_address,
            device_id=cid,
            name=name,
            is_GCM=is_GCM,
        )
        return await device.bind()
