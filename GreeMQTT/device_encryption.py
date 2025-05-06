from GreeMQTT.encryptor import encrypt, decrypt


class DeviceEncryption:
    def __init__(self, key: str | None, is_GCM: bool):
        self.key = key
        self.is_GCM = is_GCM

    def encrypt(self, pack: str) -> dict:
        return encrypt(pack, self.key, self.is_GCM)

    def decrypt(self, response: dict) -> dict:
        return decrypt(response, self.key, self.is_GCM)
