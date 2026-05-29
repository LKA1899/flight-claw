from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import FlightUser
from app.security.jwt import decode_access_token

security_scheme = HTTPBearer(auto_error=False)


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials is not None:
        return credentials.credentials
    return request.query_params.get("token")


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> FlightUser:
    token = _extract_token(request, credentials)
    if token is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")

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
