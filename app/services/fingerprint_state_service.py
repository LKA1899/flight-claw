import json
import threading
from datetime import datetime

from app.constants import PAGE_VERIFICATION_REQUIRED
from app.db import DATA_DIR


STATE_PATH = DATA_DIR / "fingerprint_state.json"
_state_lock = threading.Lock()


def get_penalty_index(platform: str, monitor_id: int | None, date_bucket: str | None) -> int:
    if monitor_id is None or not date_bucket:
        return 0
    state = _load_state()
    entry = state.get(_state_key(platform, monitor_id, date_bucket), {})
    return int(entry.get("penalty_index") or 0)


def record_fingerprint_result(
    *,
    platform: str,
    monitor_id: int | None,
    date_bucket: str | None,
    error_type: str | None,
    threshold: int,
) -> None:
    if monitor_id is None or not date_bucket:
        return
    state = _load_state()
    key = _state_key(platform, monitor_id, date_bucket)
    entry = state.get(
        key,
        {
            "verification_count": 0,
            "penalty_index": 0,
            "last_error": None,
            "update_time": None,
        },
    )
    if error_type == PAGE_VERIFICATION_REQUIRED:
        entry["verification_count"] = int(entry.get("verification_count") or 0) + 1
        if entry["verification_count"] >= max(1, threshold):
            entry["penalty_index"] = int(entry.get("penalty_index") or 0) + 1
            entry["verification_count"] = 0
    elif error_type is None:
        entry["verification_count"] = 0
    entry["last_error"] = error_type
    entry["update_time"] = datetime.now().isoformat(timespec="seconds")
    state[key] = entry
    _save_state(state)


def _state_key(platform: str, monitor_id: int, date_bucket: str) -> str:
    return f"{platform.lower()}:monitor:{monitor_id}:{date_bucket}"


def _load_state() -> dict:
    with _state_lock:
        if not STATE_PATH.exists():
            return {}
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}


def _save_state(state: dict) -> None:
    with _state_lock:
        STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
