from dataclasses import dataclass
from hashlib import sha256
from random import Random
import sys


@dataclass(frozen=True)
class BrowserFingerprint:
    name: str
    user_agent: str
    viewport_width: int
    viewport_height: int
    device_scale_factor: float
    locale: str
    timezone_id: str
    extra_headers: dict[str, str]


FINGERPRINT_POOL: tuple[BrowserFingerprint, ...] = (
    BrowserFingerprint(
        name="win_chrome_136_1440",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
        viewport_width=1440,
        viewport_height=900,
        device_scale_factor=1.0,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
    ),
    BrowserFingerprint(
        name="win_chrome_136_1536",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
        viewport_width=1536,
        viewport_height=864,
        device_scale_factor=1.25,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
    ),
    BrowserFingerprint(
        name="win_edge_136_1440",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"
        ),
        viewport_width=1440,
        viewport_height=900,
        device_scale_factor=1.0,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
    ),
    BrowserFingerprint(
        name="mac_chrome_136_1512",
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/136.0.0.0 Safari/537.36"
        ),
        viewport_width=1512,
        viewport_height=982,
        device_scale_factor=2.0,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
    ),
    BrowserFingerprint(
        name="win_chrome_135_1366",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/135.0.0.0 Safari/537.36"
        ),
        viewport_width=1366,
        viewport_height=768,
        device_scale_factor=1.0,
        locale="zh-CN",
        timezone_id="Asia/Shanghai",
        extra_headers={"Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8"},
    ),
)


def select_browser_fingerprint(
    *,
    mode: str,
    task_id: int | None,
    monitor_id: int | None,
    route_key: str | None = None,
    date_bucket: str | None = None,
    penalty_index: int = 0,
) -> BrowserFingerprint:
    normalized_mode = (mode or "fixed").strip().lower()
    pool = _platform_compatible_pool()
    if normalized_mode == "fixed":
        return pool[0]
    if normalized_mode == "per_monitor_daily" and monitor_id is not None and date_bucket:
        return pool[_stable_index(f"monitor:{monitor_id}:day:{date_bucket}", len(pool), penalty_index)]
    if normalized_mode == "per_monitor" and monitor_id is not None:
        return pool[_stable_index(f"monitor:{monitor_id}", len(pool), penalty_index)]
    if normalized_mode == "per_route" and route_key:
        return pool[_stable_index(f"route:{route_key}", len(pool), penalty_index)]
    if normalized_mode == "random_pool":
        return pool[Random().randrange(len(pool))]
    if task_id is not None:
        return pool[_stable_index(f"task:{task_id}", len(pool))]
    return pool[0]


def _platform_compatible_pool() -> tuple[BrowserFingerprint, ...]:
    if sys.platform == "win32":
        windows_pool = tuple(item for item in FINGERPRINT_POOL if item.name.startswith("win_"))
        return windows_pool or FINGERPRINT_POOL
    return FINGERPRINT_POOL


def _stable_index(seed_text: str, pool_size: int, penalty_index: int = 0) -> int:
    digest = sha256(seed_text.encode("utf-8")).hexdigest()
    return (int(digest[:8], 16) + max(0, penalty_index)) % pool_size
