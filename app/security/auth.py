from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import FlightUser
from app.security.jwt import decode_access_token

security_scheme = HTTPBearer(auto_error=False)
ACCESS_TOKEN_COOKIE = "flight_scan_access_token"
CSRF_TOKEN_COOKIE = "flight_scan_csrf_token"
STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> tuple[str | None, str | None]:
    if credentials is not None:
        return credentials.credentials, "header"
    cookie_token = getattr(request, "cookies", {}).get(ACCESS_TOKEN_COOKIE)
    if cookie_token:
        return cookie_token, "cookie"
    return None, None


def _validate_csrf_for_cookie_auth(request: Request) -> None:
    if getattr(request, "method", "GET").upper() not in STATE_CHANGING_METHODS:
        return
    expected = getattr(request, "cookies", {}).get(CSRF_TOKEN_COOKIE)
    provided = getattr(request, "headers", {}).get("X-CSRF-Token")
    if not expected or not provided or provided != expected:
        raise HTTPException(status_code=403, detail="CSRF token missing or invalid")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> FlightUser:
    token, source = _extract_token(request, credentials)
    if token is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")
    if source == "cookie":
        _validate_csrf_for_cookie_auth(request)

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    user = db.scalar(select(FlightUser).where(FlightUser.id == user_id))
    if user is None or not user.enabled:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

    return user


def require_admin(current_user: FlightUser = Depends(get_current_user)) -> FlightUser:
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Admin permission required")
    return current_user
