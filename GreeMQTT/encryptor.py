import base64
import json
from typing import Any

from Cryptodome.Cipher import AES


GENERIC_KEY = "a3K8Bx%2r8Y7#xDh"
GENERIC_GCM_KEY = "{yxAHAY_Lm6pbC/<"
GCM_IV = b"\x54\x40\x78\x44\x49\x67\x5a\x51\x6c\x5e\x63\x13"
GCM_ADD = b"qualcomm-test"


def _pkcs7_pad(data: str) -> str:
    length = 16 - (len(data) % 16)
    return data + chr(length) * length


def encrypt(pack: str, key: str | None = None, is_GCM: bool = False) -> dict[str, str]:
    if is_GCM:
        k = (key or GENERIC_GCM_KEY).encode("utf-8")
        cipher = AES.new(k, AES.MODE_GCM, nonce=GCM_IV)
        cipher.update(GCM_ADD)
        encrypted_data, tag = cipher.encrypt_and_digest(pack.encode("utf-8"))
        return {
            "pack": base64.b64encode(encrypted_data).decode("utf-8"),
            "tag": base64.b64encode(tag).decode("utf-8"),
        }
    else:
        k = (key or GENERIC_KEY).encode("utf-8")
        cipher = AES.new(k, AES.MODE_ECB)
        padded = _pkcs7_pad(pack).encode("utf-8")
        encrypted = cipher.encrypt(padded)
        return {"pack": base64.b64encode(encrypted).decode("utf-8")}


def decrypt(response: dict, key: str | None = None, is_GCM: bool = False) -> dict[str, Any]:
    if is_GCM or "tag" in response:
        k = (key or GENERIC_GCM_KEY).encode("utf-8")
        cipher = AES.new(k, AES.MODE_GCM, nonce=GCM_IV)
        cipher.update(GCM_ADD)
        data = base64.b64decode(response["pack"])
        tag = base64.b64decode(response["tag"])
        decrypted = cipher.decrypt_and_verify(data, tag)
        return json.loads(decrypted.replace(b"\xff", b"").decode("utf-8"))
    else:
        k = (key or GENERIC_KEY).encode("utf-8")
        cipher = AES.new(k, AES.MODE_ECB)
        data = base64.b64decode(response["pack"])
        decrypted = cipher.decrypt(data)
        unpadded = decrypted[: decrypted.rfind(b"}") + 1]
        return json.loads(unpadded.decode("utf-8"))
