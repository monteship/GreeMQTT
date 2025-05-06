import datetime
import json
from typing import Optional, Dict, Self

from GreeMQTT.logger import log
from GreeMQTT.config import TRACKING_PARAMS, MQTT_TOPIC
from GreeMQTT.encryptor import encrypt, decrypt
from GreeMQTT.utils import params_convert
from GreeMQTT.device_communication import DeviceCommunicator

# Constants
SOCKET_TIMEOUT = 5
BUFFER_SIZE = 1024
UDP_PORT = 7000


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

    def encrypt_request(self, pack: str) -> str:
        request = {"cid": "app", "i": 0, "t": "pack", "uid": 0, "tcid": self.device_id}
        data_encrypted = encrypt(pack, self.key, self.is_GCM)
        request.update(data_encrypted)
        return json.dumps(request)

    def decrypt_response(self, response: dict) -> Dict[str, str | int]:
        pack_decrypted = decrypt(response, self.key, self.is_GCM)
        if "cols" not in pack_decrypted:
            return pack_decrypted
        return dict(zip(pack_decrypted["cols"], pack_decrypted["dat"]))

    async def _send_data(self, request: bytes) -> Optional[bytes]:
        # Now uses DeviceCommunicator
        return await self.communicator.send_data(request)

    async def bind(self) -> Optional[Self]:
        log.info("Binding to device", device=self.device_id)
        request = self._bind_request(1)
        result = await self._send_data(request)
        if not result:
            if not self.is_GCM:
                self.is_GCM = True
                return await self.bind()
            return None
        response = json.loads(result)
        if response["t"] == "pack":
            decrypted_response = decrypt(response, is_GCM=self.is_GCM)
            if (
                "t" in decrypted_response
                and decrypted_response["t"].lower() == "bindok"
            ):
                key = decrypted_response["key"]
                log.info("Bind succeeded", device_id=self.device_id, key=key)
                self.key = key
                return self
            return None
        return None

    def _bind_request(self, i=0) -> bytes:
        pack = f'{{"mac":"{self.device_id}","t":"bind","uid":0}}'
        pack_encrypted = encrypt(pack, is_GCM=self.is_GCM)
        request = {"cid": "app", "i": i, "t": "pack", "uid": 0, "tcid": self.device_id}
        request.update(pack_encrypted)
        return json.dumps(request).encode()

    async def get_param(self) -> Optional[Dict]:
        request = self.encrypt_request(self._status_request_pack())
        result = await self._send_data(request.encode())
        if not result:
            log.error("Failed to get parameters from device", device_id=self.device_id)
            return None
        response = json.loads(result)
        if response["t"] == "pack":
            params = self.decrypt_response(response)
            return params_convert(params)
        return {}

    async def set_params(self, params: dict) -> dict[str, str | int] | None:
        params = params_convert(params, back=True)
        opts, ps = zip(*[(f'"{k}"', f"{v}") for k, v in params.items()])
        pack = f'{{"opt":[{",".join(opts)}],"p":[{",".join(ps)}],"t":"cmd"}}'
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
        cols = ",".join(f'"{i}"' for i in TRACKING_PARAMS)
        return f'{{"cols":[{cols}],"mac":"{self.device_id}","t":"status"}}'

    @classmethod
    async def search_devices(cls, ip_address=None) -> Optional["Device"]:
        log.info("Searching for devices using broadcast address", ip_address=ip_address)
        result = await DeviceCommunicator.broadcast_scan(ip_address)
        if not result:
            return None
        raw_json = result[: result.rfind(b"}") + 1]
        response = json.loads(raw_json)
        is_GCM = "tag" in response
        decrypted_response = decrypt(response, is_GCM=is_GCM)
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
