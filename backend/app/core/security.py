import base64
import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.fernet import Fernet, InvalidToken
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(subject: str, role: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key.get_secret_value(), algorithm="HS256")


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.jwt_secret_key.get_secret_value(), algorithms=["HS256"])


def _cipher() -> Fernet:
    settings = get_settings()
    secret = settings.secret_encryption_key or settings.jwt_secret_key
    digest = hashlib.sha256(secret.get_secret_value().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    return _cipher().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return _cipher().decrypt(value.encode("ascii")).decode("utf-8")
    except InvalidToken:
        return None


def mask_secret(value: str | None) -> str | None:
    plaintext = decrypt_secret(value)
    if not plaintext:
        return None
    if len(plaintext) <= 4:
        return "****"
    return f"{plaintext[:2]}{'*' * min(8, len(plaintext) - 4)}{plaintext[-2:]}"
