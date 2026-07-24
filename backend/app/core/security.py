import asyncio
import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(frozen=True)
class RefreshTokenBundle:
    token: str
    expires_at: datetime
    jti: str
    family_id: uuid.UUID


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(pwd_context.hash, password)


async def verify_password(password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(pwd_context.verify, password, password_hash)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(subject: str, role: str, extra: dict[str, Any] | None = None) -> str:
    settings = get_settings()
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "type": "access",
        "exp": utcnow() + timedelta(minutes=settings.access_token_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, family_id: uuid.UUID | None = None) -> RefreshTokenBundle:
    settings = get_settings()
    expires_at = utcnow() + timedelta(days=settings.refresh_token_days)
    token_family = family_id or uuid.uuid4()
    jti = secrets.token_urlsafe(32)
    payload = {
        "sub": subject,
        "type": "refresh",
        "jti": jti,
        "family_id": str(token_family),
        "iat": utcnow(),
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return RefreshTokenBundle(
        token=token,
        expires_at=expires_at,
        jti=jti,
        family_id=token_family,
    )


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise ValueError("Invalid token type")
    return payload


def new_opaque_token() -> str:
    return secrets.token_urlsafe(48)


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()
