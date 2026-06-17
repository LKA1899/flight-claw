import os
import secrets
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import FlightUser
from app.security.auth import ACCESS_TOKEN_COOKIE, CSRF_TOKEN_COOKIE, get_current_user
from app.security.captcha import check_login_rate_limit, clear_login_rate_limit, generate_captcha, verify_captcha
from app.security.jwt import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token
from app.security.password import hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)
    captcha_id: str = Field(min_length=1)
    captcha_code: str = Field(min_length=1)


LOGIN_ERROR_MSG = "用户名、密码或验证码错误"


def _cookie_secure() -> bool:
    return os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"}


def _user_dict(user: FlightUser) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "display_name": user.display_name,
        "role": user.role,
    }


@router.get("/captcha")
def get_captcha():
    data = generate_captcha()
    return {"success": True, "data": data}


@router.post("/login")
def login(body: LoginRequest, response: Response, db: Session = Depends(get_db)):
    try:
        check_login_rate_limit(body.username)
    except ValueError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc

    if not verify_captcha(body.captcha_id, body.captcha_code):
        raise HTTPException(status_code=400, detail=LOGIN_ERROR_MSG)

    user = db.scalar(select(FlightUser).where(FlightUser.username == body.username))
    if user is None or not user.enabled:
        raise HTTPException(status_code=400, detail=LOGIN_ERROR_MSG)

    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=400, detail=LOGIN_ERROR_MSG)

    clear_login_rate_limit(body.username)
    user.last_login_time = datetime.now()
    db.commit()

    expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id, "role": user.role},
        expires_delta=expires_delta,
    )
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        ACCESS_TOKEN_COOKIE,
        access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        CSRF_TOKEN_COOKIE,
        csrf_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=False,
        secure=_cookie_secure(),
        samesite="lax",
        path="/",
    )
    return {
        "success": True,
        "data": {
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": _user_dict(user),
        },
    }


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(ACCESS_TOKEN_COOKIE, path="/")
    response.delete_cookie(CSRF_TOKEN_COOKIE, path="/")
    return {"success": True, "data": None}


@router.get("/me")
def me(current_user: FlightUser = Depends(get_current_user)):
    return {"success": True, "data": _user_dict(current_user)}
