"""Authentication API - JWT issue / session inspection.

Phase 5: failed sign-ins are counted per officer ID in memory. After
CRIMENET_LOGIN_MAX_ATTEMPTS failures inside the attempt window the ID is locked for
CRIMENET_LOGIN_LOCKOUT seconds and every further attempt is refused with HTTP 429
before the password is even checked, so online password guessing is rate-limited
instead of being free.
"""
from __future__ import annotations

import threading
import time

from fastapi import APIRouter, Depends, HTTPException, status

from ..audit import audit_log
from ..config import (DATA_CLASSIFICATION, LOGIN_ATTEMPT_WINDOW_SECONDS, LOGIN_LOCKOUT_SECONDS,
                      LOGIN_MAX_ATTEMPTS)
from ..database.postgres import relational
from ..schemas.api import LoginRequest, LoginResponse, UserProfile
from ..security.crypto import verify_password
from ..security.deps import Principal, get_principal
from ..security.jwt_handler import create_access_token
from ..security.rbac import ROLE_SUMMARY, permissions_for

router = APIRouter(prefix="/api/auth", tags=["auth"])

# --- login rate limiting (in-memory, per officer ID) -----------------------
_attempts: dict[str, list[float]] = {}
_locked_until: dict[str, float] = {}
_rl_lock = threading.Lock()


def _key(user_id: str) -> str:
    return (user_id or "").strip().upper()


def lockout_state(user_id: str) -> dict[str, object]:
    """Current rate-limit state for one officer ID (used by the API and by tests)."""
    now = time.time()
    key = _key(user_id)
    with _rl_lock:
        recent = [t for t in _attempts.get(key, []) if now - t < LOGIN_ATTEMPT_WINDOW_SECONDS]
        _attempts[key] = recent
        remaining = max(0.0, _locked_until.get(key, 0.0) - now)
    return {
        "user_id": key,
        "failed_attempts_in_window": len(recent),
        "max_attempts": LOGIN_MAX_ATTEMPTS,
        "window_seconds": LOGIN_ATTEMPT_WINDOW_SECONDS,
        "locked": remaining > 0,
        "lockout_seconds_remaining": round(remaining, 1),
        "lockout_seconds": LOGIN_LOCKOUT_SECONDS,
    }


def _register_failure(user_id: str) -> dict[str, object]:
    now = time.time()
    key = _key(user_id)
    with _rl_lock:
        recent = [t for t in _attempts.get(key, []) if now - t < LOGIN_ATTEMPT_WINDOW_SECONDS]
        recent.append(now)
        _attempts[key] = recent
        locked = len(recent) >= LOGIN_MAX_ATTEMPTS
        if locked:
            _locked_until[key] = now + LOGIN_LOCKOUT_SECONDS
    return lockout_state(user_id) | {"locked_now": locked}


def _clear_failures(user_id: str) -> None:
    key = _key(user_id)
    with _rl_lock:
        _attempts.pop(key, None)
        _locked_until.pop(key, None)


def _refuse_locked(state: dict[str, object]) -> None:
    seconds = int(state["lockout_seconds_remaining"]) or 1
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"Too many failed sign-in attempts for this Officer ID. "
               f"Try again in {seconds} second(s).",
        headers={"Retry-After": str(seconds)},
    )


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    # rate limit first: a locked ID is refused before any password check runs
    state = lockout_state(payload.user_id)
    if state["locked"]:
        audit_log.record(payload.user_id, "UNKNOWN", "LOGIN_LOCKED_OUT", status="DENIED",
                         detail=f"Attempt refused: ID locked for another "
                                f"{state['lockout_seconds_remaining']}s after "
                                f"{state['failed_attempts_in_window']} failed attempts.")
        _refuse_locked(state)

    user = relational.get("users", payload.user_id.strip().upper()) or \
           relational.get("users", payload.user_id.strip())
    if not user or not verify_password(payload.password, user["password_hash"]):
        after = _register_failure(payload.user_id)
        audit_log.record(payload.user_id, "UNKNOWN", "LOGIN_FAILED", status="DENIED",
                         detail=f"Invalid credentials supplied "
                                f"(attempt {after['failed_attempts_in_window']} of "
                                f"{LOGIN_MAX_ATTEMPTS} in the window).")
        if after["locked_now"]:
            audit_log.record(payload.user_id, "UNKNOWN", "LOGIN_LOCKED_OUT", status="DENIED",
                             detail=f"Officer ID locked for {LOGIN_LOCKOUT_SECONDS}s after "
                                    f"{after['failed_attempts_in_window']} failed attempts.")
            _refuse_locked(after)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid Officer ID or password.")
    if not user.get("active", True):
        audit_log.record(user["user_id"], user["role"], "LOGIN_BLOCKED", status="DENIED",
                         detail="Account disabled.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="This account has been disabled. Contact an administrator.")

    _clear_failures(user["user_id"])
    token = create_access_token(user["user_id"], user["role"], user.get("case_access", []),
                                payload.remember)
    audit_log.record(user["user_id"], user["role"], "USER_LOGIN",
                     detail=f"JWT issued (expires {token['expires_at']}).")
    return LoginResponse(
        **token,
        user=UserProfile(
            user_id=user["user_id"], display_name=user["display_name"], role=user["role"],
            unit=user.get("unit", ""), badge=user.get("badge", ""),
            case_access=user.get("case_access", []), permissions=permissions_for(user["role"]),
        ),
        classification=DATA_CLASSIFICATION,
    )


@router.get("/me", response_model=UserProfile)
def me(principal: Principal = Depends(get_principal)) -> UserProfile:
    return UserProfile(**principal.dict())


@router.post("/logout")
def logout(principal: Principal = Depends(get_principal)) -> dict[str, str]:
    audit_log.record(principal.user_id, principal.role, "USER_LOGOUT",
                     detail="Session ended by user; client token discarded.")
    return {"status": "SESSION_ENDED",
            "detail": "Token discarded client-side. Stateless JWT sessions expire at the token exp claim."}


@router.get("/rate-limit/{user_id}")
def rate_limit(user_id: str) -> dict[str, object]:
    """Inspect the current sign-in rate-limit state for an officer ID."""
    return lockout_state(user_id) | {
        "policy": f"{LOGIN_MAX_ATTEMPTS} failed attempts per "
                  f"{LOGIN_ATTEMPT_WINDOW_SECONDS}s window locks the ID for "
                  f"{LOGIN_LOCKOUT_SECONDS}s; checked before the password.",
        "storage": "in-memory per-process counter (no external dependency)",
    }


@router.get("/roles")
def roles() -> dict[str, object]:
    return {
        "roles": [
            {"role": r, "summary": s, "permissions": permissions_for(r)}
            for r, s in ROLE_SUMMARY.items()
        ],
        "demo_accounts": [
            {"user_id": "INV-2201", "role": "INVESTIGATOR", "password": "investigate123"},
            {"user_id": "ANL-3310", "role": "ANALYST", "password": "analyze123"},
            {"user_id": "SUP-1100", "role": "SUPERVISOR", "password": "supervise123"},
            {"user_id": "ADM-0001", "role": "ADMIN", "password": "administer123"},
        ],
        "classification": DATA_CLASSIFICATION,
    }
