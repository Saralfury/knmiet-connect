from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def _cipher() -> Fernet:
    return Fernet(get_settings().totp_encryption_key.encode("ascii"))


def encrypt_totp_secret(secret: str) -> bytes:
    return _cipher().encrypt(secret.encode("ascii"))


def decrypt_totp_secret(value: bytes) -> str:
    try:
        return _cipher().decrypt(value).decode("ascii")
    except InvalidToken as exc:
        raise ValueError("Stored TOTP secret could not be decrypted") from exc
