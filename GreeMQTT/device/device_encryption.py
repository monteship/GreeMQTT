from typing import Dict, Optional

from GreeMQTT.encryptor import decrypt, encrypt


class DeviceEncryptor:
    def __init__(self, key: Optional[str] = None, is_GCM: bool = False):
        self.key = key
        self.is_GCM = is_GCM

    def encrypt(self, pack: str) -> dict:
        return encrypt(pack, self.key, self.is_GCM)

    def decrypt(self, response: dict) -> Dict:
        return decrypt(response, self.key, self.is_GCM)

    def update_key(self, key: str):
        self.key = key

    def update_gcm(self, is_GCM: bool):
        self.is_GCM = is_GCM
