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


class Encryptor:
    def __init__(self, key: Optional[str] = None):
        self.key = key

    def create_cipher(self) -> Any:
        raise NotImplementedError

    def encrypt(self, pack: str) -> Dict:
        raise NotImplementedError

    def decrypt(self, response: Dict) -> Dict:
        raise NotImplementedError


class ECBEncryptor(Encryptor):
    def __init__(self, key: Optional[str] = None):
        super().__init__(key or GENERIC_KEY)

    def create_cipher(self) -> Any:
        return Cipher(
            algorithms.AES(self.key.encode("utf-8")),
            modes.ECB(),
            backend=default_backend(),
        )

    @staticmethod
    def add_pkcs7_padding(data) -> str:
        length = 16 - (len(data) % 16)
        padded = data + chr(length) * length
        return padded

    def encrypt(self, pack: str) -> Dict:
        encryptor = self.create_cipher().encryptor()
        pack_padded = self.add_pkcs7_padding(pack)
        pack_encrypted = (
            encryptor.update(bytes(pack_padded, encoding="utf-8"))
            + encryptor.finalize()
        )
        pack_encoded = base64.b64encode(pack_encrypted)
        return {"pack": pack_encoded.decode("utf-8")}

    def decrypt(self, response: Dict) -> Dict:
        decryptor = self.create_cipher().decryptor()
        pack_decoded = base64.b64decode(response["pack"])
        pack_decrypted = decryptor.update(pack_decoded) + decryptor.finalize()
        pack_unpadded = pack_decrypted[0 : pack_decrypted.rfind(b"}") + 1]
        return json.loads(pack_unpadded.decode("utf-8"))


class GCMEncryptor(Encryptor):
    def __init__(self, key: Optional[str] = None):
        super().__init__(key or GENERIC_GCM_KEY)

    def create_cipher(self) -> Any:
        cipher = AES.new(bytes(self.key, "utf-8"), AES.MODE_GCM, nonce=GCM_IV)
        cipher.update(GCM_ADD)
        return cipher

    def encrypt(self, pack: str) -> Dict:
        cipher = self.create_cipher()
        encrypted_data, tag = cipher.encrypt_and_digest(pack.encode("utf-8"))
        encrypted_pack = base64.b64encode(encrypted_data).decode("utf-8")
        tag = base64.b64encode(tag).decode("utf-8")
        return {"pack": encrypted_pack, "tag": tag}

    def decrypt(self, response: Dict) -> Dict:
        cipher = self.create_cipher()
        base64decodedPack = base64.b64decode(response["pack"])
        base64decodedTag = base64.b64decode(response["tag"])
        decryptedPack = cipher.decrypt_and_verify(base64decodedPack, base64decodedTag)
        return json.loads(decryptedPack.replace(b"\xff", b"").decode("utf-8"))


class EncryptorFactory:
    @staticmethod
    def get_encryptor(is_GCM: bool = False, key: Optional[str] = None) -> Encryptor:
        if is_GCM:
            return GCMEncryptor(key)
        return ECBEncryptor(key)


def encrypt(pack, key: Optional[str] = None, is_GCM: bool = False) -> Dict:
    encryptor = EncryptorFactory.get_encryptor(is_GCM, key)
    return encryptor.encrypt(pack)


def decrypt(response: Dict, key: Optional[str] = None, is_GCM: bool = False) -> Dict:
    if is_GCM or "tag" in response:
        encryptor = GCMEncryptor(key)
    else:
        encryptor = ECBEncryptor(key)
    return encryptor.decrypt(response)
