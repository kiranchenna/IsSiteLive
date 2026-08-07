from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.encryption_key.encode())


def encrypt_password(plain: str) -> bytes:
    return _fernet.encrypt(plain.encode())


def decrypt_password(token: bytes) -> str:
    return _fernet.decrypt(token).decode()
