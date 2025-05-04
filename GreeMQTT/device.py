import json
import re
import socket
from typing import Optional, Dict

from loguru import logger

from GreeMQTT.config import TRACKING_PARAMS
from GreeMQTT.encryptor import encrypt, decrypt
from GreeMQTT.utils import params_convert

# Constants
SOCKET_TIMEOUT = 5
BUFFER_SIZE = 1024
UDP_PORT = 7000


class Device:
    def __init__(
        self,
        device_ip: int,
        device_id: str,
        name: str,
        is_GCM: bool = False,
        key: Optional[str] = None,
    ):
        self.ip = device_ip
        self.device_id = device_id
        self.name = name
        self.is_GCM = is_GCM
        self.key = key

    @property
    def topic(self) -> str:
        return f"device/{self.device_id}"

    def __str__(self):
        return f"Device(ip={self.ip}, device_id={self.device_id}, GCM={self.is_GCM})"

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

    def _send_data(self, request: bytes) -> Optional[bytes]:
        with socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP) as s:
            s.settimeout(SOCKET_TIMEOUT)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.sendto(request, (self.ip, UDP_PORT))
            return s.recv(BUFFER_SIZE)

    def bind(self) -> Optional["Device"]:
        logger.info(f"Binding device: {self})")
        request = self._bind_request(1)
        result = self._send_data(request)
        if not result:
            if not self.is_GCM:
                self.is_GCM = True
                return self.bind()
            return None
        response = json.loads(result)
        if response["t"] == "pack":
            decrypted_response = decrypt(response, is_GCM=self.is_GCM)
            if (
                "t" in decrypted_response
                and decrypted_response["t"].lower() == "bindok"
            ):
                key = decrypted_response["key"]
                logger.info("Bind to %s succeeded: %s" % (self.device_id, key))
                self.key = key
                return self
            return None
        return None

    def _bind_request(self, i=0) -> bytes:
        request = {"cid": "app", "i": i, "t": "pack", "uid": 0, "tcid": self.device_id}
        pack_encrypted = encrypt(
            f'{{"mac":"{self.device_id}","t":"bind","uid":0}}',
            is_GCM=self.is_GCM,
        )
        request.update(pack_encrypted)
        return json.dumps(request).encode()

    def get_param(self) -> Optional[Dict]:
        request = self.encrypt_request(self._status_request_pack())
        result = self._send_data(request.encode())
        if not result:
            logger.error(f"Failed to get parameters from device {self.device_id}")
            return None
        response = json.loads(result)
        if response["t"] == "pack":
            params = self.decrypt_response(response)
            return params_convert(params)
        return {}

    def set_params(self, params: dict) -> None:
        params = params_convert(params, back=True)
        opts, ps = zip(*[(f'"{k}"', f"{v}") for k, v in params.items()])
        pack = f'{{"opt":[{",".join(opts)}],"p":[{",".join(ps)}],"t":"cmd"}}'
        request = self.encrypt_request(pack)
        result = self._send_data(request.encode())
        if result:
            response = json.loads(result)
            if response["t"] == "pack":
                decrypt_response = self.decrypt_response(response)
                opt = decrypt_response.get("opt")
                val = decrypt_response.get("val")
                logger.debug(
                    f"Set parameters for device {self.device_id}: {opt} = {val}"
                )

    def _status_request_pack(self) -> str:
        cols = ",".join(f'"{i}"' for i in TRACKING_PARAMS)
        return f'{{"cols":[{cols}],"mac":"{self.device_id}","t":"status"}}'

    @classmethod
    def search_devices(cls, ip_address=None) -> Optional["Device"]:
        logger.info(f"Searching for devices using broadcast address: {ip_address}")
        with socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP) as s:
            s.settimeout(5)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.sendto(b'{"t":"scan"}', (ip_address, UDP_PORT))
            try:
                data, (ip, port) = s.recvfrom(1024)
                raw_json = data[: data.rfind(b"}") + 1]
                response = json.loads(raw_json)
                is_GCM = "tag" in response
                decrypted_response = decrypt(response, is_GCM=is_GCM)
                name = decrypted_response.get("name", "Unknown")
                cid = decrypted_response.get("cid", response.get("cid"))
                if not is_GCM and "ver" in decrypted_response:
                    ver = re.search(r"(?<=V)[0-9]+(?<=.)", decrypted_response["ver"])
                    if ver and int(ver.group(0)) >= 2:
                        logger.info(
                            "Set GCM encryption because version in search responce is 2 or later"
                        )
                        is_GCM = True
                device = cls(
                    device_ip=ip,
                    device_id=cid,
                    name=name,
                    is_GCM=is_GCM,
                )
                return device.bind()
            except socket.timeout:
                logger.info("No response from device")
        return None
