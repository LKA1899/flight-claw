import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from app.db import DATA_DIR
from app.services.settings_service import get_browser_profile_settings


PROFILE_LOCK_FILE_NAMES = ("SingletonLock", "SingletonSocket", "SingletonCookie")


@dataclass
class BrowserProfile:
    headless: bool
    executable_path: str | None = None
    locale: str | None = "zh-CN"
    timezone_id: str | None = "Asia/Shanghai"
    viewport_width: int = 1440
    viewport_height: int = 900
    user_agent: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    block_resource_types: set[str] = field(default_factory=set)
    blocked_domains: set[str] = field(default_factory=set)
    capture_xhr_enabled: bool = True
    capture_xhr_pattern: str = "flight|search|price|list|ota|batch"

    @classmethod
    def from_settings(cls, *, headless: bool, executable_path: str | None = None) -> "BrowserProfile":
        settings = get_browser_profile_settings()
        return cls(
            headless=headless,
            executable_path=executable_path or os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or None,
            locale=str(settings.get("locale") or "zh-CN"),
            timezone_id=str(settings.get("timezone_id") or "Asia/Shanghai"),
            viewport_width=int(settings.get("viewport_width") or 1440),
            viewport_height=int(settings.get("viewport_height") or 900),
            user_agent=str(settings.get("user_agent") or "") or None,
            extra_headers=dict(settings.get("extra_headers") or {}),
            block_resource_types=set(settings.get("block_resource_types") or []),
            blocked_domains=set(settings.get("blocked_domains") or []),
            capture_xhr_enabled=bool(settings.get("capture_xhr_enabled", True)),
            capture_xhr_pattern=str(settings.get("capture_xhr_pattern") or ""),
        )

    def context_options(self) -> dict[str, Any]:
        options: dict[str, Any] = {
            "executable_path": self.executable_path,
            "headless": self.headless,
            "viewport": {"width": self.viewport_width, "height": self.viewport_height},
            "locale": self.locale,
            "timezone_id": self.timezone_id,
        }
        if self.user_agent:
            options["user_agent"] = self.user_agent
        if self.extra_headers:
            options["extra_http_headers"] = self.extra_headers
        return {key: value for key, value in options.items() if value is not None}


def profile_dir_candidates(task_id: int) -> list[tuple[str, Path, bool]]:
    shared_dir = DATA_DIR / "browser_profile" / "ctrip"
    isolated_dir = shared_dir / f"task_{task_id}"
    return [
        ("shared", shared_dir, True),
        ("isolated", isolated_dir, True),
    ]


def clear_profile_lock_files(profile_dir: Path) -> None:
    for file_name in PROFILE_LOCK_FILE_NAMES:
        lock_path = profile_dir / file_name
        try:
            if lock_path.exists():
                lock_path.unlink()
        except OSError:
            continue


def is_profile_lock_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "profile appears to be in use" in message or "process_singleton" in message


def install_resource_blocking(context, profile: BrowserProfile) -> None:
    if not profile.block_resource_types and not profile.blocked_domains:
        return

    def route_handler(route, request) -> None:
        url = request.url.lower()
        resource_type = request.resource_type
        if resource_type in profile.block_resource_types or any(domain.lower() in url for domain in profile.blocked_domains):
            route.abort()
            return
        route.continue_()

    context.route("**/*", route_handler)


def launch_persistent_browser_context(playwright, *, task_id: int, profile: BrowserProfile):
    last_error: Exception | None = None
    for profile_mode, profile_dir, clear_locks_first in profile_dir_candidates(task_id):
        profile_dir.mkdir(parents=True, exist_ok=True)
        if clear_locks_first:
            clear_profile_lock_files(profile_dir)
        try:
            context = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                **profile.context_options(),
            )
            install_resource_blocking(context, profile)
            return context, profile_mode, str(profile_dir)
        except PlaywrightError as exc:
            last_error = exc
            if profile_mode == "shared" and is_profile_lock_error(exc):
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Failed to launch Chromium context")
