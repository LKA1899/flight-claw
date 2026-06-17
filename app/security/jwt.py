import os
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
_configured_secret = os.getenv("SECRET_KEY", "").strip()

if APP_ENV in {"production", "prod"}:
    if not _configured_secret or _configured_secret == "change-me" or len(_configured_secret) < 32:
        raise RuntimeError("SECRET_KEY must be set to a strong random value in production")

SECRET_KEY = _configured_secret or "change-me"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
