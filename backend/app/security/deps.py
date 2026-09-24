"""FastAPI security dependencies: JWT extraction, RBAC guard, case authorization."""
from __future__ import annotations

from typing import Any, Callable, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from ..database.postgres import relational
from .jwt_handler import TokenError, decode_token
from .rbac import can_access_case, has_permission, permissions_for

bearer_scheme = HTTPBearer(auto_error=False)


class Principal:
    def __init__(self, user_id: str, role: str, case_access: list[str], display_name: str,
                 unit: str = "", badge: str = "") -> None:
        self.user_id = user_id
        self.role = role
        self.case_access = case_access
        self.display_name = display_name
        self.unit = unit
        self.badge = badge

    @property
    def permissions(self) -> list[str]:
        return permissions_for(self.role)

    def dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "display_name": self.display_name,
            "role": self.role,
            "unit": self.unit,
            "badge": self.badge,
            "case_access": self.case_access,
            "permissions": self.permissions,
        }


async def get_principal(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Principal:
    # Phase 5: tokens are accepted ONLY from the Authorization header. A token in a
    # query string ends up in access logs, browser history, proxy logs and referrer
    # headers, so the query-string fallback was removed entirely.
    token = creds.credentials if creds else None
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Authentication required. Please sign in.")
    try:
        payload = decode_token(token)
    except TokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    user = relational.get("users", payload["sub"])
    if not user or not user.get("active", True):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Account is not active.")
    return Principal(
        user_id=user["user_id"],
        role=user["role"],
        case_access=user.get("case_access", []),
        display_name=user.get("display_name", user["user_id"]),
        unit=user.get("unit", ""),
        badge=user.get("badge", ""),
    )


def require_permission(permission: str) -> Callable[..., Principal]:
    async def guard(principal: Principal = Depends(get_principal)) -> Principal:
        if not has_permission(principal.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {principal.role} is not authorized for '{permission}'.",
            )
        return principal

    return guard


def authorize_case(principal: Principal, case_id: str | None) -> None:
    if case_id and not relational.get("cases", case_id):
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found.")
    if not can_access_case(principal.case_access, case_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Case-level authorization denied for {case_id}.",
        )


def authorized_case_ids(principal: Principal) -> list[str]:
    all_ids = [c["case_id"] for c in relational.all("cases")]
    if "*" in (principal.case_access or []):
        return all_ids
    return [c for c in all_ids if c in principal.case_access]
