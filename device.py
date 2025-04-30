from loguru import logger

import json
import re
import socket
from typing import Optional, Dict, Tuple

from config import TRACKING_PARAMS
from encryptor import encrypt, decrypt
from utils import params_convert

# Configure loguru
logger.add("logs/app.log", rotation="1 MB", retention="7 days", level="INFO")

# Constants
SOCKET_TIMEOUT = 5
BUFFER_SIZE = 1024
UDP_PORT = 7000


class ScanResult:
    def __init__(
        self, address: Tuple[str, int], device_id: str, name: str, is_GCM: bool = False
    ):
        self.ip = address[0]
        self.port = address[1]
        self.device_id = device_id
        self.name = name
        self.is_GCM = is_GCM
        self.key: Optional[str] = None

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

    def __str__(self):
        return f"ScanResult(ip={self.ip}, port={self.port}, device_id={self.device_id}, GCM={self.is_GCM})"


def bind_request(scan_result: ScanResult, i=0) -> bytes:
    device_id = scan_result.device_id
    request = {"cid": "app", "i": i, "t": "pack", "uid": 0, "tcid": device_id}
    pack_encrypted = encrypt(
        f'{{"mac":"{device_id}","t":"bind","uid":0}}',
        is_GCM=scan_result.is_GCM,
    )
    request.update(pack_encrypted)
    return json.dumps(request).encode()


def send_data(scan_result: ScanResult, request: bytes) -> Optional[bytes]:
    with socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP) as s:
        s.settimeout(5)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.sendto(request, (scan_result.ip, scan_result.port))
        return s.recv(1024)


def bind_device(scan_result: ScanResult) -> Optional[ScanResult]:
    logger.info(f"Binding device: {scan_result})")

    request = bind_request(scan_result, 1)
    result = send_data(scan_result, request)
    if not result:
        if not scan_result.is_GCM:
            scan_result.is_GCM = True
            return bind_device(scan_result)
        return None
    response = json.loads(result)
    if response["t"] == "pack":
        decrypted_response = decrypt(response, is_GCM=scan_result.is_GCM)
        if "t" in decrypted_response and decrypted_response["t"].lower() == "bindok":
            key = decrypted_response["key"]
            logger.info("Bind to %s succeeded: %s" % (scan_result.device_id, key))
            scan_result.key = key
            return scan_result
        return None
    return None


def search_devices(ip_address=None) -> Optional[ScanResult]:
    logger.info(f"Searching for devices using broadcast address: {ip_address}")
    with socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP) as s:
        s.settimeout(5)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(b'{"t":"scan"}', (ip_address, 7000))
        try:
            data, address = s.recvfrom(1024)
            raw_json = data[: data.rfind(b"}") + 1]
            response = json.loads(raw_json)
            is_GCM = "tag" in response
            decrypted_response = decrypt(response, is_GCM=is_GCM)

            name = decrypted_response.get("name")
            cid = decrypted_response.get("cid", response.get("cid"))
            if not is_GCM and "ver" in decrypted_response:
                ver = re.search(r"(?<=V)[0-9]+(?<=.)", decrypted_response["ver"])
                if int(ver.group(0)) >= 2:
                    logger.info(
                        "Set GCM encryption because version in search responce is 2 or later"
                    )
                    is_GCM = True
            return bind_device(ScanResult(address, cid, name, is_GCM))
        except socket.timeout:
            logger.info("No response from device")
    return None


def status_request_pack(device_id: str) -> str:
    cols = ",".join(f'"{i}"' for i in TRACKING_PARAMS)
    return f'''{{"cols":[{cols}],"mac":"{device_id}","t":"status"}}'''


def get_param(device: ScanResult) -> Optional[Dict]:
    """
    Get parameters from the device.
    :param device: ScanResult object containing device information.
    :return: A dictionary of parameters if successful, None otherwise.
    """
    request = device.encrypt_request(status_request_pack(device.device_id))
    result = send_data(device, request.encode())
    if not result:
        logger.error(f"Failed to get parameters from device {device.device_id}")
        return None
    response = json.loads(result)
    if response["t"] == "pack":
        params = device.decrypt_response(response)

        return params_convert(params)
    return {}


def set_params(device: ScanResult, params: dict) -> None:
    """Set parameters for the device."""
    params = params_convert(params, back=True)

    opts, ps = zip(*[(f'"{k}"', f"{v}") for k, v in params.items()])
    pack = f'{{"opt":[{",".join(opts)}],"p":[{",".join(ps)}],"t":"cmd"}}'
    request = device.encrypt_request(pack)
    result = send_data(device, request.encode())
    if result:
        response = json.loads(result)
        if response["t"] == "pack":
            decrypt_response = device.decrypt_response(response)
            opt = decrypt_response.get("opt")
            val = decrypt_response.get("val")
            logger.debug(f"Set parameters for device {device.device_id}: {opt} = {val}")
