import json
from pathlib import Path

from app.db import DATA_DIR

SETTINGS_PATH = DATA_DIR / "settings.json"

DEFAULTS = {
    "headless": False,
    "scan_interval_min_seconds": 30,
    "scan_interval_max_seconds": 90,
    "browser_profile": {
        "fingerprint_pool_enabled": True,
        "fingerprint_mode": "per_monitor_daily",
        "fingerprint_profile_strategy": "pool",
        "fingerprint_verification_switch_threshold": 2,
        "browser_session_mode": "persistent",
        "browser_fallback_mode": "isolated_ephemeral",
        "browser_retry_on_verification": True,
        "browser_retry_on_profile_lock": True,
        "browser_retry_max_attempts": 1,
        "browser_warmup_enabled": False,
        "prefer_installed_chrome": True,
        "executable_path": "",
        "locale": "zh-CN",
        "timezone_id": "Asia/Shanghai",
        "viewport_width": 1440,
        "viewport_height": 900,
        "user_agent": "",
        "force_fingerprint_user_agent": False,
        "extra_headers": {},
        "block_resource_types": ["font", "media"],
        "blocked_domains": [],
        "capture_xhr_enabled": True,
        "capture_xhr_pattern": "flight|search|price|list|ota|batch",
    },
}

SCAN_INTERVAL_MIN_ALLOWED = 5
SCAN_INTERVAL_MAX_ALLOWED = 600


def load_settings() -> dict:
    if SETTINGS_PATH.exists():
        try:
            return json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return dict(DEFAULTS)


def save_settings(data: dict) -> dict:
    current = load_settings()
    current.update(data)
    _validate_settings(current)
    SETTINGS_PATH.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")
    return current


def get_headless() -> bool:
    return bool(load_settings().get("headless", False))


def get_scan_interval_range() -> tuple[int, int]:
    settings = load_settings()
    minimum = int(settings.get("scan_interval_min_seconds", DEFAULTS["scan_interval_min_seconds"]))
    maximum = int(settings.get("scan_interval_max_seconds", DEFAULTS["scan_interval_max_seconds"]))
    if minimum > maximum:
        minimum, maximum = DEFAULTS["scan_interval_min_seconds"], DEFAULTS["scan_interval_max_seconds"]
    minimum = max(SCAN_INTERVAL_MIN_ALLOWED, min(SCAN_INTERVAL_MAX_ALLOWED, minimum))
    maximum = max(SCAN_INTERVAL_MIN_ALLOWED, min(SCAN_INTERVAL_MAX_ALLOWED, maximum))
    if minimum > maximum:
        minimum = maximum
    return minimum, maximum


def get_browser_profile_settings() -> dict:
    settings = load_settings()
    profile = dict(DEFAULTS["browser_profile"])
    custom = settings.get("browser_profile")
    if isinstance(custom, dict):
        profile.update(custom)
    return profile


def _validate_settings(data: dict) -> None:
    minimum = int(data.get("scan_interval_min_seconds", DEFAULTS["scan_interval_min_seconds"]))
    maximum = int(data.get("scan_interval_max_seconds", DEFAULTS["scan_interval_max_seconds"]))
    if minimum < SCAN_INTERVAL_MIN_ALLOWED or minimum > SCAN_INTERVAL_MAX_ALLOWED:
        raise ValueError(
            f"scan_interval_min_seconds must be between {SCAN_INTERVAL_MIN_ALLOWED} and {SCAN_INTERVAL_MAX_ALLOWED}"
        )
    if maximum < SCAN_INTERVAL_MIN_ALLOWED or maximum > SCAN_INTERVAL_MAX_ALLOWED:
        raise ValueError(
            f"scan_interval_max_seconds must be between {SCAN_INTERVAL_MIN_ALLOWED} and {SCAN_INTERVAL_MAX_ALLOWED}"
        )
    if minimum > maximum:
        raise ValueError("scan_interval_min_seconds must be less than or equal to scan_interval_max_seconds")
