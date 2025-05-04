import base64
import json
from typing import Optional, Any, Dict

from Crypto.Cipher import AES
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


GENERIC_KEY = "a3K8Bx%2r8Y7#xDh"
GENERIC_GCM_KEY = "{yxAHAY_Lm6pbC/<"
GCM_IV = b"\x54\x40\x78\x44\x49\x67\x5a\x51\x6c\x5e\x63\x13"
GCM_ADD = b"qualcomm-test"


def create_cipher(key: str) -> Any:
    return Cipher(
        algorithms.AES(key.encode("utf-8")), modes.ECB(), backend=default_backend()
    )


def create_GCM_cipher(key) -> Any:
    cipher = AES.new(bytes(key, "utf-8"), AES.MODE_GCM, nonce=GCM_IV)
    cipher.update(GCM_ADD)
    return cipher


def add_pkcs7_padding(data) -> str:
    length = 16 - (len(data) % 16)
    padded = data + chr(length) * length
    return padded


def decrypt_ECB(response: Dict, key: Optional[str]) -> Dict:
    decryptor = create_cipher(key or GENERIC_KEY).decryptor()
    pack_decoded = base64.b64decode(response["pack"])
    pack_decrypted = decryptor.update(pack_decoded) + decryptor.finalize()
    pack_unpadded = pack_decrypted[0 : pack_decrypted.rfind(b"}") + 1]
    return json.loads(pack_unpadded.decode("utf-8"))


def decrypt_GCM(response: Dict, key: Optional[str]) -> Dict:
    cipher = create_GCM_cipher(key or GENERIC_GCM_KEY)
    base64decodedPack = base64.b64decode(response["pack"])
    base64decodedTag = base64.b64decode(response["tag"])
    decryptedPack = cipher.decrypt_and_verify(base64decodedPack, base64decodedTag)
    return json.loads(decryptedPack.replace(b"\xff", b"").decode("utf-8"))


def decrypt(response: Dict, key: Optional[str] = None, is_GCM: bool = False) -> Dict:
    if is_GCM or "tag" in response:
        return decrypt_GCM(response, key=key)
    return decrypt_ECB(response, key=key)


def encrypt_ECB(pack: str, key: Optional[str]) -> Dict:
    encryptor = create_cipher(key or GENERIC_KEY).encryptor()
    pack_padded = add_pkcs7_padding(pack)
    pack_encrypted = (
        encryptor.update(bytes(pack_padded, encoding="utf-8")) + encryptor.finalize()
    )
    pack_encoded = base64.b64encode(pack_encrypted)
    return {"pack": pack_encoded.decode("utf-8")}


def encrypt_GCM(pack: str, key: Optional[str]) -> Dict:
    encrypted_data, tag = create_GCM_cipher(key or GENERIC_GCM_KEY).encrypt_and_digest(
        pack.encode("utf-8")
    )
    encrypted_pack = base64.b64encode(encrypted_data).decode("utf-8")
    tag = base64.b64encode(tag).decode("utf-8")
    return {"pack": encrypted_pack, "tag": tag}


def encrypt(pack, key: Optional[str] = None, is_GCM: bool = False) -> Dict:
    if is_GCM:
        return encrypt_GCM(pack, key=key)
    return encrypt_ECB(pack, key=key)
