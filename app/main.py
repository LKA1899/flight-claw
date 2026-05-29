import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import select

from app.db import SessionLocal, create_all
from app.models import FlightUser
from app.routers import api, auth
from app.services.scheduler_service import shutdown_scheduler, start_scheduler


def _init_default_admin() -> None:
    admin_username = os.getenv("ADMIN_USERNAME", "admin").strip()
    admin_password = os.getenv("ADMIN_PASSWORD", "").strip()

    if not admin_password:
        print("[FlightClaw] ADMIN_PASSWORD not set. Skipping default admin initialization.")
        return

    with SessionLocal() as db:
        existing = db.scalar(select(FlightUser).where(FlightUser.username == admin_username))
        if existing:
            return

        from app.security.password import hash_password

        user = FlightUser(
            username=admin_username,
            password_hash=hash_password(admin_password),
            display_name="管理员",
            role="ADMIN",
        )
        db.add(user)
        db.commit()
        print("[FlightClaw] Default admin user initialized. Please change password in production.")


def create_app() -> FastAPI:
    app = FastAPI(title="FlightScan")

    cors_origins = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(auth.router)
    app.include_router(api.router)

    @app.exception_handler(ValueError)
    def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(HTTPException)
    def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"success": False, "message": exc.detail})

    @app.on_event("startup")
    def on_startup() -> None:
        create_all()
        _init_default_admin()
        start_scheduler()

    @app.on_event("shutdown")
    def on_shutdown() -> None:
        shutdown_scheduler()

    return app


app = create_app()
