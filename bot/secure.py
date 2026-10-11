"""YouTube iznini, sadece GitHub secret'ındaki istemci anahtarıyla açılabilecek şekilde şifreler."""
import base64
import hashlib
import json

from cryptography.fernet import Fernet


def _key(client_secret_json: str) -> bytes:
    data = json.loads(client_secret_json)
    inner = data.get("installed") or data.get("web") or {}
    material = (inner.get("client_secret", "") + "|" + inner.get("client_id", "") + "|yt-bot").encode()
    return base64.urlsafe_b64encode(hashlib.sha256(material).digest())


def encrypt_token(token_json: str, client_secret_json: str) -> bytes:
    return Fernet(_key(client_secret_json)).encrypt(token_json.encode("utf-8"))


def decrypt_token(blob: bytes, client_secret_json: str) -> str:
    return Fernet(_key(client_secret_json)).decrypt(blob).decode("utf-8")
