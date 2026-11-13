from datetime import datetime, timedelta, timezone

import jwt
from jwt import ExpiredSignatureError, InvalidTokenError

from app.core.config import settings

__all__ = [
    "ExpiredSignatureError",
    "InvalidTokenError",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
]

ALGORITHM = "HS256"


def create_access_token(user_id: int, role: str) -> str:
    """Kratkotrajan token koji putuje uz svaki zahtjev."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "iss": settings.jwt_issuer,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(user_id: int) -> str:
    """Dugotrajan token koji se salje samo na /auth/refresh; nosi najmanje."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "type": "refresh",
        "iss": settings.jwt_issuer,
        "exp": now + timedelta(days=settings.refresh_token_expire_days),
    }
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Provjerava potpis, istek i izdavatelja; vraca sadrzaj tokena.

    Istekli token podize ExpiredSignatureError, svaki drugi neispravan
    token InvalidTokenError. Prvi je podvrsta drugoga, pa se hvata prvi.
    """
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[ALGORITHM],  # nikad algoritam iz zaglavlja samog tokena
        issuer=settings.jwt_issuer,
        options={"require": ["exp", "sub", "iss", "type"]},
    )
