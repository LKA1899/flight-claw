import os
import shutil
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError

from app.db import DATA_DIR
from app.crawler.fingerprint_pool import BrowserFingerprint, select_browser_fingerprint
from app.services.settings_service import get_browser_profile_settings


PROFILE_LOCK_FILE_NAMES = ("SingletonLock", "SingletonSocket", "SingletonCookie")
WINDOWS_CHROME_PATHS = (
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
)


@dataclass
class BrowserLaunchResult:
    context: Any
    session_mode: str
    profile_dir: str
    fallback_used: bool = False
    cleanup_dir: str | None = None

    def artifact_meta(self) -> dict[str, Any]:
        return {
            "session_mode": self.session_mode,
            "profile_dir": self.profile_dir,
            "fallback_used": self.fallback_used,
        }

    def cleanup(self) -> None:
        if not self.cleanup_dir:
            return
        shutil.rmtree(self.cleanup_dir, ignore_errors=True)


@dataclass
class BrowserProfile:
    headless: bool
    executable_path: str | None = None
    fingerprint_name: str | None = None
    profile_key: str | None = None
    fingerprint_mode: str | None = None
    date_bucket: str | None = None
    penalty_index: int = 0
    session_mode: str = "persistent"
    fallback_mode: str = "isolated_ephemeral"
    locale: str | None = "zh-CN"
    timezone_id: str | None = "Asia/Shanghai"
    viewport_width: int = 1440
    viewport_height: int = 900
    device_scale_factor: float | None = 1.0
    user_agent: str | None = None
    extra_headers: dict[str, str] = field(default_factory=dict)
    block_resource_types: set[str] = field(default_factory=set)
    blocked_domains: set[str] = field(default_factory=set)
    capture_xhr_enabled: bool = True
    capture_xhr_pattern: str = "flight|search|price|list|ota|batch"

    @classmethod
    def from_settings(
        cls,
        *,
        headless: bool,
        task_id: int | None = None,
        monitor_id: int | None = None,
        route_key: str | None = None,
        date_bucket: str | None = None,
        penalty_index: int = 0,
        executable_path: str | None = None,
    ) -> "BrowserProfile":
        settings = get_browser_profile_settings()
        fingerprint_enabled = bool(settings.get("fingerprint_pool_enabled", True))
        fingerprint_mode = str(settings.get("fingerprint_mode") or "fixed")
        fingerprint: BrowserFingerprint | None = None
        if fingerprint_enabled:
            fingerprint = select_browser_fingerprint(
                mode=fingerprint_mode,
                task_id=task_id,
                monitor_id=monitor_id,
                route_key=route_key,
                date_bucket=date_bucket,
                penalty_index=penalty_index,
            )
        base_headers = dict(settings.get("extra_headers") or {})
        if fingerprint:
            merged_headers = dict(fingerprint.extra_headers)
            merged_headers.update(base_headers)
        else:
            merged_headers = base_headers
        configured_executable_path = str(settings.get("executable_path") or "").strip() or None
        resolved_executable_path = (
            executable_path
            or os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
            or configured_executable_path
            or _detect_installed_chrome_path(settings)
        )
        configured_user_agent = str(settings.get("user_agent") or "").strip() or None
        force_fingerprint_user_agent = bool(settings.get("force_fingerprint_user_agent", False))
        if fingerprint and force_fingerprint_user_agent:
            resolved_user_agent = fingerprint.user_agent
        elif configured_user_agent:
            resolved_user_agent = configured_user_agent
        elif fingerprint:
            resolved_user_agent = fingerprint.user_agent
        else:
            resolved_user_agent = None
        return cls(
            headless=headless,
            executable_path=resolved_executable_path,
            fingerprint_name=fingerprint.name if fingerprint else "custom",
            profile_key=fingerprint.name if fingerprint and str(settings.get("fingerprint_profile_strategy") or "pool") == "pool" else None,
            fingerprint_mode=fingerprint_mode,
            date_bucket=date_bucket,
            penalty_index=penalty_index,
            session_mode=str(settings.get("browser_session_mode") or "persistent"),
            fallback_mode=str(settings.get("browser_fallback_mode") or "isolated_ephemeral"),
            locale=fingerprint.locale if fingerprint else str(settings.get("locale") or "zh-CN"),
            timezone_id=fingerprint.timezone_id if fingerprint else str(settings.get("timezone_id") or "Asia/Shanghai"),
            viewport_width=fingerprint.viewport_width if fingerprint else int(settings.get("viewport_width") or 1440),
            viewport_height=fingerprint.viewport_height if fingerprint else int(settings.get("viewport_height") or 900),
            device_scale_factor=fingerprint.device_scale_factor if fingerprint else float(settings.get("device_scale_factor") or 1.0),
            user_agent=resolved_user_agent,
            extra_headers=merged_headers,
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
            "device_scale_factor": self.device_scale_factor,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
        }
        if self.user_agent:
            options["user_agent"] = self.user_agent
        if self.extra_headers:
            options["extra_http_headers"] = self.extra_headers
        return {key: value for key, value in options.items() if value is not None}

    def artifact_meta(self) -> dict[str, Any]:
        return {
            "fingerprint_name": self.fingerprint_name,
            "profile_key": self.profile_key,
            "fingerprint_mode": self.fingerprint_mode,
            "date_bucket": self.date_bucket,
            "penalty_index": self.penalty_index,
            "session_mode": self.session_mode,
            "fallback_mode": self.fallback_mode,
            "locale": self.locale,
            "timezone_id": self.timezone_id,
            "viewport": f"{self.viewport_width}x{self.viewport_height}",
            "device_scale_factor": self.device_scale_factor,
            "user_agent": self.user_agent,
            "executable_path": self.executable_path,
        }


def _detect_installed_chrome_path(settings: dict) -> str | None:
    if not bool(settings.get("prefer_installed_chrome", True)):
        return None
    if sys.platform != "win32":
        return None
    for path in WINDOWS_CHROME_PATHS:
        if Path(path).exists():
            return path
    return None


def profile_dir_candidates(task_id: int, profile: BrowserProfile) -> list[tuple[str, Path, bool]]:
    shared_dir = DATA_DIR / "browser_profile" / "ctrip" / (profile.profile_key or "default")
    isolated_dir = shared_dir / f"task_{task_id}"
    return [
        ("shared", shared_dir, True),
        ("isolated", isolated_dir, True),
    ]


def _launch_context(playwright, *, profile: BrowserProfile, profile_dir: str):
    return playwright.chromium.launch_persistent_context(
        user_data_dir=profile_dir,
        **profile.context_options(),
    )


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
    if profile.session_mode == "isolated_ephemeral":
        temp_root = DATA_DIR / "tmp"
        temp_root.mkdir(parents=True, exist_ok=True)
        temp_dir = tempfile.mkdtemp(prefix="flightclaw-profile-", dir=str(temp_root))
        context = _launch_context(playwright, profile=profile, profile_dir=temp_dir)
        install_resource_blocking(context, profile)
        return BrowserLaunchResult(
            context=context,
            session_mode="isolated_ephemeral",
            profile_dir=temp_dir,
            cleanup_dir=temp_dir,
        )

    last_error: Exception | None = None
    for profile_mode, profile_dir, clear_locks_first in profile_dir_candidates(task_id, profile):
        if profile.session_mode == "persistent_task_isolated" and profile_mode != "isolated":
            continue
        profile_dir.mkdir(parents=True, exist_ok=True)
        if clear_locks_first:
            clear_profile_lock_files(profile_dir)
        try:
            context = _launch_context(playwright, profile=profile, profile_dir=str(profile_dir))
            install_resource_blocking(context, profile)
            return BrowserLaunchResult(
                context=context,
                session_mode="persistent" if profile_mode == "shared" else "persistent_task_isolated",
                profile_dir=str(profile_dir),
                fallback_used=profile_mode != "shared",
            )
        except PlaywrightError as exc:
            last_error = exc
            if profile_mode == "shared" and is_profile_lock_error(exc):
                continue
            raise
    if last_error:
        raise last_error
    raise RuntimeError("Failed to launch Chromium context")
