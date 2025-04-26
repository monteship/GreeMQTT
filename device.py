from loguru import logger

import json
import re
import socket
from enum import Enum
from typing import Optional, Dict
from encryptor import (
    encrypt,
    decrypt,
    encrypt_GCM,
    decrypt_GCM,
    encrypt_generic,
    decrypt_generic,
    encrypt_GCM_generic,
    decrypt_GCM_generic,
)

# Configure loguru
logger.add("logs/app.log", rotation="1 MB", retention="7 days", level="INFO")


class Encryption(Enum):
    ECB = "ECB"
    GCM = "GCM"


class ScanResult:
    def __init__(
        self,
        address: tuple[str, int],
        device_id: str,
        name: str,
        encryption_type: Encryption,
    ):
        self.ip = address[0]
        self.port = address[1]
        self.device_id = device_id
        self.name = name
        self.encryption_type = encryption_type
        self.key = None

    def encrypt_generic(self, data: str) -> str:
        if self.encryption_type == Encryption.GCM:
            return encrypt_GCM_generic(data)
        else:
            return encrypt_generic(data)

    def decrypt_generic(self, *args) -> str:
        if self.encryption_type == Encryption.GCM:
            return decrypt_GCM_generic(*args)
        else:
            return decrypt_generic(args[0])

    def encrypt_request(self, pack: str) -> str:
        request = f'{{"cid":"app","i":0,"t":"pack","uid":0,"tcid":"{self.device_id}",'
        if self.encryption_type == Encryption.GCM:
            data_encrypted = encrypt_GCM(pack, self.key)
            return f'{request}"tag":"{data_encrypted["tag"]}","pack":"{data_encrypted["pack"]}"}}'
        else:
            pack_encrypted = encrypt(pack, self.key)
            return f'{request}"pack":"{pack_encrypted}"}}'

    def decrypt_response(self, response: dict) -> Dict[str, str]:
        if self.encryption_type == Encryption.GCM:
            pack_decrypted = decrypt_GCM(response["pack"], response["tag"], self.key)
        else:
            pack_decrypted = decrypt(response["pack"], self.key)
        pack_decrypted = json.loads(pack_decrypted)
        if "cols" not in pack_decrypted:
            return pack_decrypted
        return dict(zip(pack_decrypted["cols"], pack_decrypted["dat"]))

    def __str__(self):
        return f"ScanResult(ip={self.ip}, port={self.port}, device_id={self.device_id}, name={self.name}, encryption_type={self.encryption_type})"


def create_request(tcid, pack_encrypted, i=0):
    request = f'{{"cid":"app","i":{i},"t":"pack","uid":0,"tcid":"{tcid}",'
    if isinstance(pack_encrypted, dict):
        request += (
            f'"tag":"{pack_encrypted["tag"]}","pack":"{pack_encrypted["pack"]}"}}'
        )
    else:
        request += f'"pack":"{pack_encrypted}"}}'
    return request


def send_data(ip, port, data):
    with socket.socket(type=socket.SOCK_DGRAM, proto=socket.IPPROTO_UDP) as s:
        s.settimeout(5)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.sendto(data, (ip, port))
        return s.recv(1024)


def bind_device(scan_result: ScanResult) -> Optional[ScanResult]:
    logger.info(f"Binding device: {scan_result})")
    pack = f'{{"mac":"{scan_result.device_id}","t":"bind","uid":0}}'
    pack_encrypted = scan_result.encrypt_generic(pack)
    request = create_request(scan_result.device_id, pack_encrypted, 1)
    result = send_data(scan_result.ip, scan_result.port, request.encode())
    if not result:
        if scan_result.encryption_type != Encryption.GCM:
            scan_result.encryption_type = Encryption.GCM
            return bind_device(scan_result)
        return None
    response = json.loads(result)
    if response["t"] == "pack":
        pack_decrypted = scan_result.decrypt_generic(
            response["pack"], response.get("tag")
        )
        bind_resp = json.loads(pack_decrypted)
        if "t" in bind_resp and bind_resp["t"].lower() == "bindok":
            key = bind_resp["key"]
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
            resp = json.loads(raw_json)
            encryption_type = Encryption.GCM if "tag" in resp else Encryption.ECB
            decrypted_pack = (
                decrypt_GCM_generic(resp["pack"], resp["tag"])
                if encryption_type == Encryption.GCM
                else decrypt_generic(resp["pack"])
            )
            pack = json.loads(decrypted_pack)
            name = pack.get("name", pack.get("model", "<unknown>"))
            cid = pack.get("cid", resp.get("cid", "<unknown-cid>"))
            if encryption_type != Encryption.GCM and "ver" in pack:
                ver = re.search(r"(?<=V)[0-9]+(?<=.)", pack["ver"])
                if int(ver.group(0)) >= 2:
                    logger.info(
                        "Set GCM encryption because version in search responce is 2 or later"
                    )
                    encryption_type = Encryption.GCM
            return bind_device(ScanResult(address, cid, name, encryption_type))
        except socket.timeout:
            logger.info("No response from device")
    return None


def status_request_pack(device_id: str) -> str:
    keywords = [
        "Pow",  # power state of the device
        "Mod",  # mode of the device (auto, cool, dry, fan, heat)
        "SetTem",  # set temperature
        "TemUn",  # temperature unit (Celsius or Fahrenheit)
        "WdSpd",  # fan speed (auto, low, medium-low, medium, medium-high, high)
        "Air",  # controls the state of the fresh air valve (not available on all units)
        "Blo",  # "Blow" or "X-Fan", this function keeps the fan running for a while after shutting down. Only usable in Dry and Cool mode
        "Health",  # controls Health ("Cold plasma") mode, only for devices equipped with "anion generator", which absorbs dust and kills bacteria
        "SwhSlp",  # sleep mode, which gradually changes the temperature in Cool, Heat and Dry mode
        "Lig",  # turns all indicators and the display on the unit on or off
        "SwingLfRig",  # controls the swing mode of the horizontal air blades (available on limited number of devices, e.g. some Cooper & Hunter units - thanks to mvmn)
        "SwUpDn",  # controls the swing mode of the vertical air blades
        "Quiet",  # controls the Quiet mode which slows down the fan to its most quiet speed. Not available in Dry and Fan mode.
        "Tur",  # sets fan speed to the maximum. Fan speed cannot be changed while active and only available in Dry and Cool mode
        "StHt",  # maintain the room temperature steadily at 8°C and prevent the room from freezing by heating operation when nobody is at home for long in severe winter (from http://www.gree.ca/en/features)
        # "HeatCoolType",  # unknown
        # "TemRec",  # this bit is used to distinguish between two Fahrenheit values (see Setting the temperature using Fahrenheit section below)
        "SvSt",  # energy saving mode
        "TemSen",  # temperature sensor (internal or external) with offset +40
    ]
    cols = ",".join(f'"{i}"' for i in keywords)
    return f'''{{"cols":[{cols}],"mac":"{device_id}","t":"status"}}'''


def get_param(device):
    request = device.encrypt_request(status_request_pack(device.device_id))
    result = send_data(device.ip, device.port, request.encode())
    if not result:
        logger.error(f"Failed to get parameters from device {device.device_id}")
        return None
    response = json.loads(result)
    if response["t"] == "pack":
        params = device.decrypt_response(response)

        if "TemSen" in params:
            params["TemSen"] = int(params["TemSen"]) - 40
        return params
    return None


def set_params(device, params):
    opts, ps = zip(*[(f'"{k}"', f"{v}") for k, v in params.items()])
    pack = f'{{"opt":[{",".join(opts)}],"p":[{",".join(ps)}],"t":"cmd"}}'
    request = device.encrypt_request(pack)
    result = send_data(device.ip, device.port, request.encode())
    if result:
        response = json.loads(result)
        if response["t"] == "pack":
            decrypt_response = device.decrypt_response(response)
            logger.debug(
                f"Set parameters for device {device.device_id}: {zip(decrypt_response['opt'], decrypt_response['val'])}"
            )
