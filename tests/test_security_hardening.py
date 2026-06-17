import importlib
import os
import unittest
from datetime import date, datetime
from types import SimpleNamespace

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import FlightMonitor, FlightUser
from app.services import date_service


class SecurityHardeningTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _create_user(self, role: str = "USER") -> FlightUser:
        user = FlightUser(
            username=f"user-{role.lower()}",
            password_hash="unused",
            display_name="Test User",
            role=role,
            enabled=True,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user

    def _create_monitor(self, trip_type: str = "ONE_WAY") -> FlightMonitor:
        monitor = FlightMonitor(
            monitor_name="security-monitor",
            from_city="SHA",
            to_city="BKK",
            platform="CTRIP",
            trip_type=trip_type,
            allow_direct=True,
            allow_transfer=False,
            allow_train_positioning=False,
            allow_hidden_city=False,
            enabled=True,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        self.db.add(monitor)
        self.db.commit()
        self.db.refresh(monitor)
        return monitor

    def test_production_rejects_missing_or_default_jwt_secret(self):
        jwt_module = importlib.import_module("app.security.jwt")
        old_env = {key: os.environ.get(key) for key in ("APP_ENV", "SECRET_KEY")}
        try:
            os.environ["APP_ENV"] = "production"
            os.environ.pop("SECRET_KEY", None)
            with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
                importlib.reload(jwt_module)

            os.environ["SECRET_KEY"] = "change-me"
            with self.assertRaisesRegex(RuntimeError, "SECRET_KEY"):
                importlib.reload(jwt_module)
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
            importlib.reload(jwt_module)

    def test_get_current_user_rejects_query_string_token(self):
        from app.security.auth import get_current_user
        from app.security.jwt import create_access_token

        user = self._create_user(role="ADMIN")
        token = create_access_token({"user_id": user.id, "sub": user.username, "role": user.role})
        request = SimpleNamespace(query_params={"token": token}, cookies={})

        with self.assertRaises(HTTPException) as ctx:
            get_current_user(request=request, credentials=None, db=self.db)

        self.assertEqual(ctx.exception.status_code, 401)

    def test_require_admin_rejects_non_admin_user(self):
        from app.security.auth import require_admin

        user = self._create_user(role="USER")

        with self.assertRaises(HTTPException) as ctx:
            require_admin(user)

        self.assertEqual(ctx.exception.status_code, 403)

    def test_batch_date_range_has_business_cap(self):
        monitor = self._create_monitor()

        with self.assertRaisesRegex(ValueError, "date range"):
            date_service.batch_add_dates(
                self.db,
                monitor.id,
                start_date=date(2026, 1, 1),
                end_date=date(2027, 2, 15),
                weekdays=set(),
            )

    def test_roundtrip_date_combinations_have_business_cap(self):
        monitor = self._create_monitor(trip_type="ROUND_TRIP")

        with self.assertRaisesRegex(ValueError, "date combinations"):
            date_service.batch_add_dates(
                self.db,
                monitor.id,
                start_date=date(2026, 1, 1),
                end_date=date(2026, 3, 1),
                weekdays=set(),
                return_start_date=date(2026, 1, 1),
                return_end_date=date(2026, 3, 1),
            )

    def test_schedule_cron_rejects_too_frequent_runs(self):
        from app.services.scheduler_service import validate_schedule_cron

        with self.assertRaisesRegex(ValueError, "too frequent"):
            validate_schedule_cron("* * * * *", "Asia/Shanghai")

    def test_captcha_store_is_capped(self):
        from app.security import captcha

        captcha._CAPTCHA_STORE.clear()

        for _ in range(captcha.MAX_CAPTCHA_STORE_SIZE + 1):
            captcha.generate_captcha()

        self.assertLessEqual(len(captcha._CAPTCHA_STORE), captcha.MAX_CAPTCHA_STORE_SIZE)

    def test_production_app_disables_openapi_docs(self):
        from app.main import create_app

        old_env = {key: os.environ.get(key) for key in ("APP_ENV", "SECRET_KEY")}
        try:
            os.environ["APP_ENV"] = "production"
            os.environ["SECRET_KEY"] = "x" * 64
            app = create_app()
        finally:
            for key, value in old_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        self.assertIsNone(app.docs_url)
        self.assertIsNone(app.redoc_url)
        self.assertIsNone(app.openapi_url)
