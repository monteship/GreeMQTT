import os
import re
from enum import Enum
from typing import Optional, Dict

from dotenv import load_dotenv

import paho.mqtt.client as mqtt

import threading
import time
import json
import socket

from encryptor import (
    decrypt_GCM_generic,
    decrypt_generic,
    encrypt_GCM_generic,
    encrypt_generic,
    encrypt_GCM,
    encrypt,
    decrypt_GCM,
    decrypt,
)

# Load environment variables from .env file
load_dotenv()
NETWORK = os.getenv("NETWORK").split(",")


# MQTT Configuration
MQTT_BROKER = os.getenv("MQTT_BROKER", "localhost")
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "gree")

# Initialize MQTT client
mqtt_client = mqtt.Client()
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)


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
            return {"status": pack_decrypted["r"]}
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
    print(
        f"Binding device: {scan_result.ip} ({scan_result.name}, ID: {scan_result.device_id}, encryption: {scan_result.encryption_type.name})"
    )

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
    response = json.loads(result)
    if response["t"] == "pack":
        pack_decrypted = scan_result.decrypt_generic(
            response["pack"], response.get("tag")
        )

        bind_resp = json.loads(pack_decrypted)

        if "t" in bind_resp and bind_resp["t"].lower() == "bindok":
            key = bind_resp["key"]
            print("Bind to %s succeeded, key = %s" % (scan_result.device_id, key))
            scan_result.key = key
            return scan_result
        return None
    return None


def search_devices(ip_address=None) -> Optional[ScanResult]:
    print(f"Searching for devices using broadcast address: {ip_address}")
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
                    print(
                        "Set GCM encryption because version in search responce is 2 or later"
                    )
                    encryption_type = Encryption.GCM
            return bind_device(ScanResult(address, cid, name, encryption_type))
        except socket.timeout:
            print("No response from device")
    return None


def status_request_pack(device_id: str) -> str:
    keywords = [
        "Pow",
        "Mod",
        "SetTem",
        "WdSpd",
        "Air",
        "Blo",
        "Health",
        "SwhSlp",
        "Lig",
        "SwingLfRig",
        "SwUpDn",
        "Quiet",
        "Tur",
        "StHt",
        "TemUn",
        "HeatCoolType",
        "TemRec",
        "SvSt",
    ]
    cols = ",".join(f'"{i}"' for i in keywords)
    return f'''{{"cols":[{cols}],"mac":"{device_id}","t":"status"}}'''


def get_param(device):
    request = device.encrypt_request(status_request_pack(device.device_id))
    result = send_data(device.ip, device.port, request.encode())
    if not result:
        print(f"Failed to get parameters from device {device.device_id}")
        return
    response = json.loads(result)
    if response["t"] == "pack":
        params = device.decrypt_response(response)

        device_topic = f"{MQTT_TOPIC}/{device.device_id}"
        payload = json.dumps(params)

        mqtt_client.publish(device_topic, payload)
        print(f"Published to MQTT topic {device_topic}: {payload}")


def set_params(device, params):
    opts, ps = zip(*[(f'"{k}"', f'"{v}"') for k, v in params.items()])
    pack = f'{{"opt":[{",".join(opts)}],"p":[{",".join(ps)}],"t":"cmd"}}'
    request = device.encrypt_request(pack)
    result = send_data(device.ip, device.port, request.encode())
    if result:
        response = json.loads(result)
        if (
            response["t"] == "pack"
            and device.decrypt_response(response).get("status") != 200
        ):
            print("Failed to set parameter")


def periodic_update(device, interval=5):
    """Periodically fetch and publish device parameters."""
    while True:
        get_param(device)
        time.sleep(interval)


def handle_set_params(device):
    """Subscribe to the set topic and handle incoming messages to set parameters."""

    def on_message(client, userdata, msg):
        try:
            params = json.loads(msg.payload.decode("utf-8"))
            set_params(device, params)
        except json.JSONDecodeError:
            print(f"Invalid JSON received on topic {msg.topic}: {msg.payload}")

    set_topic = f"{MQTT_TOPIC}/{device.device_id}/set"
    mqtt_client.subscribe(set_topic)
    mqtt_client.message_callback_add(set_topic, on_message)

    print(f"Subscribed to topic {set_topic} for setting parameters.")
    while True:
        time.sleep(1)  # Keep the thread alive


if __name__ == "__main__":
    threads = []
    for device_ip in NETWORK:
        d = search_devices(device_ip)
        if d:
            print("Device found: %s" % d)
            # Start a thread for periodic updates
            thread = threading.Thread(target=periodic_update, args=(d,))
            thread.daemon = True  # Daemonize thread to exit with the main program
            threads.append(thread)
            thread.start()

            # Start a thread to handle set_params
            set_thread = threading.Thread(target=handle_set_params, args=(d,))
            set_thread.daemon = True
            threads.append(set_thread)
            set_thread.start()

    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
