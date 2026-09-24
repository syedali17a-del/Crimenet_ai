"""JWT issuing / verification (PyJWT)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

import jwt

from ..config import JWT_ALGORITHM, JWT_EXPIRY_MINUTES, JWT_SECRET


class TokenError(Exception):
    pass


def create_access_token(user_id: str, role: str, case_access: list[str],
                        remember: bool = False) -> dict[str, Any]:
    minutes = JWT_EXPIRY_MINUTES * (3 if remember else 1)
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=minutes)
    payload = {
        "sub": user_id,
        "role": role,
        "case_access": case_access,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "iss": "crimenet-ai",
        "aud": "crimenet-console",
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": exp.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "expires_in": minutes * 60,
    }


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM],
                          audience="crimenet-console", issuer="crimenet-ai")
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("Session expired. Please sign in again.") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("Invalid session token.") from exc
