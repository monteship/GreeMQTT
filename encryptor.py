import base64

from Crypto.Cipher import AES
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


GENERIC_KEY = "a3K8Bx%2r8Y7#xDh"
GENERIC_GCM_KEY = "{yxAHAY_Lm6pbC/<"
GCM_IV = b"\x54\x40\x78\x44\x49\x67\x5a\x51\x6c\x5e\x63\x13"
GCM_ADD = b"qualcomm-test"


def create_cipher(key):
    return Cipher(
        algorithms.AES(key.encode("utf-8")), modes.ECB(), backend=default_backend()
    )


def decrypt(pack_encoded, key):
    decryptor = create_cipher(key).decryptor()
    pack_decoded = base64.b64decode(pack_encoded)
    pack_decrypted = decryptor.update(pack_decoded) + decryptor.finalize()
    pack_unpadded = pack_decrypted[0 : pack_decrypted.rfind(b"}") + 1]
    return pack_unpadded.decode("utf-8")


def decrypt_generic(pack_encoded):
    return decrypt(pack_encoded, GENERIC_KEY)


def add_pkcs7_padding(data):
    length = 16 - (len(data) % 16)
    padded = data + chr(length) * length
    return padded


def encrypt(pack, key):
    encryptor = create_cipher(key).encryptor()
    pack_padded = add_pkcs7_padding(pack)
    pack_encrypted = (
        encryptor.update(bytes(pack_padded, encoding="utf-8")) + encryptor.finalize()
    )
    pack_encoded = base64.b64encode(pack_encrypted)
    return pack_encoded.decode("utf-8")


def encrypt_generic(pack):
    return encrypt(pack, GENERIC_KEY)


def create_GCM_cipher(key):
    cipher = AES.new(bytes(key, "utf-8"), AES.MODE_GCM, nonce=GCM_IV)
    cipher.update(GCM_ADD)
    return cipher


def decrypt_GCM(pack_encoded, tag_encoded, key):
    cipher = create_GCM_cipher(key)
    base64decodedPack = base64.b64decode(pack_encoded)
    base64decodedTag = base64.b64decode(tag_encoded)
    decryptedPack = cipher.decrypt_and_verify(base64decodedPack, base64decodedTag)
    decodedPack = decryptedPack.replace(b"\xff", b"").decode("utf-8")
    return decodedPack


def decrypt_GCM_generic(pack_encoded, tag_encoded):
    return decrypt_GCM(pack_encoded, tag_encoded, GENERIC_GCM_KEY)


def encrypt_GCM(pack, key):
    encrypted_data, tag = create_GCM_cipher(key).encrypt_and_digest(
        pack.encode("utf-8")
    )
    encrypted_pack = base64.b64encode(encrypted_data).decode("utf-8")
    tag = base64.b64encode(tag).decode("utf-8")
    data = {"pack": encrypted_pack, "tag": tag}
    return data


def encrypt_GCM_generic(pack):
    return encrypt_GCM(pack, GENERIC_GCM_KEY)
