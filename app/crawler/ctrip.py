import asyncio
import json
import os
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.constants import (
    COMPLETENESS_OUTBOUND_WITH_STARTING_PRICE,
    PAGE_CONTEXT_MISMATCH,
    PAGE_DATE_DRIFT,
    PAGE_LOAD_TIMEOUT,
    PAGE_LOGIN_REQUIRED,
    PAGE_MANUAL_TAKEOVER_TIMEOUT,
    PAGE_PARSE_ZERO_RESULT,
    PAGE_PROFILE_LOCKED,
    PAGE_STRUCTURE_CHANGED,
    PAGE_UNKNOWN,
    PAGE_VERIFICATION_REQUIRED,
    STATUS_CANCEL_REQUESTED,
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_PARTIAL_SUCCESS,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    TRIP_ROUND_TRIP,
)
from app.db import DATA_DIR, SessionLocal
from app.models import FlightQueryTask, FlightRoundTripOutbound
from app.parsers.ctrip_parser import normalize_text
from app.services.city_code_service import resolve_city_code
from app.services.settings_service import get_headless
from app.services.roundtrip_service import (
    RETURN_EXPAND_FAILED,
    RETURN_EXPANDING,
    parse_roundtrip_outbounds_for_task,
    parse_roundtrip_returns_for_outbound,
    selected_outbounds_for_expansion,
    mark_outbound_status,
)
from app.services.task_service import refresh_batch_counts

CTRIP_FLIGHT_URL = "https://flights.ctrip.com/online/channel-domestic"
CTRIP_LIST_URL = "https://flights.ctrip.com/online/list/oneway-{from_code}-{to_code}"
CTRIP_ROUNDTRIP_LIST_URL = "https://flights.ctrip.com/online/list/round-{from_code}-{to_code}"
GOTO_TIMEOUT_MS = 60_000
RESULT_TIMEOUT_MS = 120_000
MANUAL_CONTINUE_TIMEOUT_MS = 15 * 60_000
_browser_lock = threading.Lock()
_PROFILE_LOCK_FILE_NAMES = ("SingletonLock", "SingletonSocket", "SingletonCookie")


def _prepare_playwright_event_loop() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


class PageStateError(RuntimeError):
    def __init__(self, error_type: str, message: str):
        super().__init__(f"{error_type}: {message}")
        self.error_type = error_type
        self.message = message


class ManualInterventionRequired(PageStateError):
    """Raised when the user must handle login, captcha, or changed page structure."""


class TaskCancelled(RuntimeError):
    """Raised when a query task or parent scan is cancelled."""


def log(message: str) -> None:
    print(f"[FlightClaw][CTRIP] {datetime.now():%Y-%m-%d %H:%M:%S} {message}", flush=True)


def _task_cancel_requested(task_id: int | None) -> bool:
    if not task_id:
        return False
    with SessionLocal() as db:
        task = db.get(FlightQueryTask, task_id)
        if not task:
            return False
        if task.status in {STATUS_CANCEL_REQUESTED, STATUS_CANCELLED}:
            return True
        if task.scan_id:
            from app.models import FlightScan

            scan = db.get(FlightScan, task.scan_id)
            if scan and scan.status in {STATUS_CANCEL_REQUESTED, STATUS_CANCELLED}:
                return True
    return False


def _raise_if_cancelled(task_id: int | None) -> None:
    if _task_cancel_requested(task_id):
        raise TaskCancelled("Task cancelled")


def _acquire_browser_lock(task_id: int) -> None:
    while True:
        _raise_if_cancelled(task_id)
        if _browser_lock.acquire(blocking=False):
            return
        log("Another browser query is running; waiting for browser slot")
        time.sleep(2)


def _profile_dir_candidates(task_id: int) -> list[tuple[str, Path, bool]]:
    shared_dir = DATA_DIR / "browser_profile" / "ctrip"
    isolated_dir = shared_dir / f"task_{task_id}"
    return [
        ("shared", shared_dir, True),
        ("isolated", isolated_dir, True),
    ]


def _clear_profile_lock_files(profile_dir: Path) -> None:
    for file_name in _PROFILE_LOCK_FILE_NAMES:
        lock_path = profile_dir / file_name
        try:
            if lock_path.exists():
                lock_path.unlink()
        except OSError:
            continue


def _is_profile_lock_error(exc: Exception) -> bool:
    message = str(exc).lower()
    return "profile appears to be in use" in message or "process_singleton" in message


def _launch_browser_context(playwright, task_id: int, headless: bool, executable_path: str | None):
    last_error: Exception | None = None
    for profile_mode, profile_dir, clear_locks_first in _profile_dir_candidates(task_id):
        profile_dir.mkdir(parents=True, exist_ok=True)
        if clear_locks_first:
            _clear_profile_lock_files(profile_dir)
        try:
            log(f"Launch Chromium profile: mode={profile_mode}, dir={profile_dir}")
            browser = playwright.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                executable_path=executable_path,
                headless=headless,
                viewport={"width": 1440, "height": 900},
            )
            return browser, profile_mode, str(profile_dir)
        except PlaywrightError as exc:
            last_error = exc
            if profile_mode == "shared" and _is_profile_lock_error(exc):
                log("Shared browser profile is busy, falling back to isolated profile")
                continue
            if _is_profile_lock_error(exc):
                raise PageStateError(PAGE_PROFILE_LOCKED, str(exc)) from exc
            raise
    if last_error:
        if _is_profile_lock_error(last_error):
            raise PageStateError(PAGE_PROFILE_LOCKED, str(last_error)) from last_error
        raise last_error
    raise RuntimeError("Failed to launch Chromium context")


def _safe_page_title(page: Page | None) -> str | None:
    if not page:
        return None
    try:
        value = page.title()
    except PlaywrightError:
        return None
    value = normalize_text(value or "")
    return value or None


def _safe_page_url(page: Page | None) -> str | None:
    if not page:
        return None
    try:
        return page.url or None
    except PlaywrightError:
        return None


def _page_context_suffix(page: Page | None) -> str:
    parts: list[str] = []
    current_url = _safe_page_url(page)
    page_title = _safe_page_title(page)
    if current_url:
        parts.append(f"current_url={current_url}")
    if page_title:
        parts.append(f"page_title={page_title}")
    return ", ".join(parts)


def _raise_page_error(error_type: str, message: str, page: Page | None = None) -> None:
    suffix = _page_context_suffix(page)
    if suffix:
        message = f"{message}, {suffix}"
    raise PageStateError(error_type, message)


def _error_type_from_message(message: str) -> str:
    prefix = (message or "").split(":", 1)[0].strip()
    if prefix.startswith("PAGE_"):
        return prefix
    return PAGE_UNKNOWN


def _build_failure_message(exc: Exception, page: Page | None = None) -> str:
    base_message = str(exc).strip() or f"{PAGE_UNKNOWN}: unknown error"
    suffix = _page_context_suffix(page)
    if isinstance(exc, PageStateError):
        if suffix and suffix not in base_message:
            return f"{base_message}, {suffix}"
        return base_message
    if suffix and suffix not in base_message:
        return f"{PAGE_UNKNOWN}: {base_message}, {suffix}"
    return f"{PAGE_UNKNOWN}: {base_message}"


def _looks_like_result_list(page: Page) -> bool:
    result_selectors = [
        "text=选为去程",
        "text=選為去程",
        "text=往返总价",
        "text=选择去程",
        "text=直飞/经停",
        "text=中转组合",
    ]
    for selector in result_selectors:
        try:
            if page.locator(selector).count() > 0:
                return True
        except PlaywrightError:
            continue

    text = _page_visible_text(page)
    if not text:
        return False
    strong_keywords = ["选为去程", "往返总价", "选择去程", "中转组合", "最近更新时间", "直飞/经停"]
    return sum(1 for keyword in strong_keywords if keyword in text) >= 2


def _dismiss_known_result_dialogs(page: Page) -> bool:
    dismiss_pairs = [
        ("出行提醒", "知道了"),
        ("进藏提醒", "知道了"),
    ]
    for title_text, button_text in dismiss_pairs:
        try:
            title = page.get_by_text(title_text, exact=True)
            button = page.get_by_text(button_text, exact=True)
            if title.count() > 0 and button.count() > 0:
                button.first.click(timeout=3_000)
                page.wait_for_timeout(500)
                log(f"Dismissed page dialog: {title_text}")
                return True
        except PlaywrightError:
            continue
    return False


def _classify_page_text(page: Page) -> str | None:
    if _looks_like_result_list(page):
        return None

    login_signals = [
        "text=账号密码登录",
        "text=验证码登录",
        "text=忘记密码",
        "text=免费注册",
        "input[placeholder*='手机号']",
        "input[placeholder*='用户名']",
        "input[placeholder*='邮箱']",
        "input[placeholder*='登录密码']",
    ]
    matched_login_signals = 0
    for selector in login_signals:
        try:
            if page.locator(selector).count() > 0:
                matched_login_signals += 1
        except PlaywrightError:
            continue
    if matched_login_signals >= 2:
        return PAGE_LOGIN_REQUIRED

    try:
        login_modal = page.locator("input[placeholder*='登录密码']").count() > 0
    except PlaywrightError:
        login_modal = False

    text = _page_visible_text(page)
    if not text:
        return PAGE_LOGIN_REQUIRED if login_modal else None
    lowered = text.lower()
    verification_keywords = [
        "验证码",
        "滑块",
        "人机验证",
        "安全验证",
        "访问异常",
        "网络环境异常",
        "请完成验证",
        "verify",
        "verification",
        "risk control",
        "risk-control",
    ]
    login_keywords = ["账号密码登录", "验证码登录", "请先登录", "登录验证", "forget password", "forgot password"]
    if login_modal or any(keyword.lower() in lowered for keyword in login_keywords):
        return PAGE_LOGIN_REQUIRED
    if any(keyword.lower() in lowered for keyword in verification_keywords):
        return PAGE_VERIFICATION_REQUIRED
    return None


def wait_for_manual_continue(page: Page, message: str, task_id: int | None = None) -> None:
    log("Manual takeover required")
    log(message)
    try:
        page.bring_to_front()
        page.evaluate(
            """(message) => {
                const existing = document.getElementById("flightclaw-manual-tip");
                if (existing) existing.remove();
                const tip = document.createElement("div");
                tip.id = "flightclaw-manual-tip";
                tip.innerHTML = "";
                const text = document.createElement("div");
                text.textContent = message;
                const button = document.createElement("button");
                button.type = "button";
                button.textContent = "I have handled it, continue";
                button.onclick = () => {
                    window.__flightclawManualContinue = true;
                    tip.remove();
                };
                Object.assign(tip.style, {
                    position: "fixed",
                    left: "16px",
                    right: "16px",
                    bottom: "16px",
                    zIndex: "2147483647",
                    padding: "14px 18px",
                    background: "#fff7ed",
                    border: "1px solid #fb923c",
                    color: "#7c2d12",
                    fontSize: "16px",
                    borderRadius: "8px",
                    boxShadow: "0 12px 32px rgba(0,0,0,0.18)",
                    display: "flex",
                    gap: "12px",
                    alignItems: "center",
                    justifyContent: "space-between"
                });
                Object.assign(button.style, {
                    border: "0",
                    borderRadius: "6px",
                    background: "#ea580c",
                    color: "#fff",
                    cursor: "pointer",
                    padding: "8px 12px",
                    whiteSpace: "nowrap"
                });
                tip.appendChild(text);
                tip.appendChild(button);
                window.__flightclawManualContinue = false;
                document.body.appendChild(tip);
            }""",
            message,
        )
        deadline = time.monotonic() + MANUAL_CONTINUE_TIMEOUT_MS / 1000
        while time.monotonic() < deadline:
            _raise_if_cancelled(task_id)
            try:
                page.wait_for_function("() => window.__flightclawManualContinue === true", timeout=5_000)
                break
            except PlaywrightTimeoutError:
                continue
        else:
            raise PlaywrightTimeoutError("Manual intervention timed out")
        log("Manual takeover confirmed, continue")
        return
    except PlaywrightTimeoutError as exc:
        raise ManualInterventionRequired(PAGE_MANUAL_TAKEOVER_TIMEOUT, "manual takeover timed out") from exc
    except PlaywrightError:
        pass
    raise ManualInterventionRequired(PAGE_UNKNOWN, message)


def _cancellable_sleep(seconds: float, task_id: int | None = None) -> None:
    deadline = time.monotonic() + seconds
    while True:
        _raise_if_cancelled(task_id)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return
        time.sleep(min(1.0, remaining))


def _sleep_before_single_task(task_id: int | None = None) -> None:
    seconds = random.uniform(3, 8)
    log(f"低频控制：执行前等待 {seconds:.1f} 秒")
    _cancellable_sleep(seconds, task_id)


def sleep_between_batch_tasks() -> None:
    seconds = random.uniform(30, 90)
    log(f"低频控制：任务间等待 {seconds:.1f} 秒")
    time.sleep(seconds)


def _city_code(city: str, airports: str | None = None) -> str:
    return resolve_city_code(city, airports=airports)


def _normalize_city_code(value: str | None) -> str:
    return (value or "").strip().lower()


def _build_list_url(task: object) -> str:
    from_code = _city_code(task.from_city, getattr(task, "from_airports", None))
    to_code = _city_code(task.to_city, getattr(task, "to_airports", None))
    params = urlencode(
        {
            "depdate": task.depart_date.isoformat(),
            "cabin": "y_s",
            "adult": "1",
            "child": "0",
            "infant": "0",
        }
    )
    return f"{CTRIP_LIST_URL.format(from_code=from_code, to_code=to_code)}?{params}"


def _build_roundtrip_list_url(task: object) -> str:
    from_code = _city_code(task.from_city, getattr(task, "from_airports", None))
    to_code = _city_code(task.to_city, getattr(task, "to_airports", None))
    return_date = getattr(task, "return_date", None)
    if not return_date:
        raise ValueError("Round-trip task return_date is required")
    depdate = f"{task.depart_date.isoformat()}_{return_date.isoformat()}"
    return (
        f"{CTRIP_ROUNDTRIP_LIST_URL.format(from_code=from_code, to_code=to_code)}"
        f"?_=1&depdate={depdate}&cabin=Y_S_C_F"
    )


def _safe_fill(page: Page, labels: list[str], value: str, action_name: str) -> bool:
    log(action_name)
    candidates = []
    for label in labels:
        candidates.extend(
            [
                page.get_by_placeholder(label),
                page.get_by_label(label),
                page.get_by_role("textbox", name=label),
                page.locator(f"input[placeholder*='{label}']"),
            ]
        )
    for locator in candidates:
        try:
            if locator.count() == 0:
                continue
            item = locator.first
            item.click(timeout=3_000)
            item.fill(value, timeout=5_000)
            page.keyboard.press("Enter")
            return True
        except PlaywrightError:
            continue
    return False


def _safe_click_search(page: Page) -> bool:
    log("点击搜索")
    candidates = [
        page.get_by_role("button", name="搜索"),
        page.get_by_text("搜索", exact=True),
        page.locator("button").filter(has_text="搜索"),
        page.locator("a").filter(has_text="搜索"),
    ]
    for locator in candidates:
        try:
            if locator.count() == 0:
                continue
            locator.first.click(timeout=5_000)
            return True
        except PlaywrightError:
            continue
    return False


def _validate_result_context(page: Page, task: object, expected_url: str, allow_channel: bool = False) -> None:
    current_url = (page.url or "").lower()
    expected_from = _normalize_city_code(_city_code(task.from_city, getattr(task, "from_airports", None)))
    expected_to = _normalize_city_code(_city_code(task.to_city, getattr(task, "to_airports", None)))
    list_marker = "/online/list/" in current_url
    channel_marker = "/online/channel" in current_url
    route_marker = f"-{expected_from}-{expected_to}" in current_url
    page_error_type = _classify_page_text(page)
    if page_error_type == PAGE_VERIFICATION_REQUIRED:
        _raise_page_error(page_error_type, "verification or risk-control page detected", page)
    if page_error_type == PAGE_LOGIN_REQUIRED:
        _raise_page_error(page_error_type, "login page detected", page)

    expected_depdate = parse_qs(urlparse(expected_url).query).get("depdate", [None])[0]
    current_depdate = parse_qs(urlparse(page.url).query).get("depdate", [None])[0]
    if expected_depdate and current_depdate and expected_depdate != current_depdate:
        _raise_page_error(
            PAGE_DATE_DRIFT,
            f"expected {expected_depdate} but actual page shows {current_depdate}",
            page,
        )

    if list_marker and route_marker:
        return

    if allow_channel and channel_marker:
        try:
            body_text = page.locator("body").inner_text(timeout=5_000)
        except PlaywrightError:
            body_text = ""
        if task.from_city in body_text and task.to_city in body_text:
            return

    try:
        body_text = page.locator("body").inner_text(timeout=5_000)
    except PlaywrightError:
        body_text = ""
    if list_marker and task.from_city in body_text and task.to_city in body_text:
        return

    _raise_page_error(
        PAGE_CONTEXT_MISMATCH,
        "expected route "
        f"{expected_from.upper()}->{expected_to.upper()} but current page did not match expected result page; "
        f"expected_url={expected_url}, route={task.from_city}->{task.to_city}, depart_date={task.depart_date}",
        page,
    )


def _looks_like_manual_verification(page: Page) -> bool:
    return _classify_page_text(page) == PAGE_VERIFICATION_REQUIRED


def _try_fill_and_search(page: Page, task: FlightQueryTask) -> None:
    from_ok = _safe_fill(page, ["出发", "出发城市", "出发地"], task.from_city, "填写出发城市")
    to_ok = _safe_fill(page, ["到达", "到达城市", "目的地"], task.to_city, "填写到达城市")
    date_ok = _safe_fill(page, ["出发日期", "日期", "去程日期"], task.depart_date.isoformat(), "填写去程日期")

    if task.trip_type == TRIP_ROUND_TRIP and task.return_date:
        return_date_ok = _safe_fill(page, ["返程日期", "返回日期"], task.return_date.isoformat(), "填写返程日期")
        if not return_date_ok:
            log("返程日期填写失败，尝试切换往返模式")
            _try_switch_to_roundtrip(page)
            _safe_fill(page, ["返程日期", "返回日期"], task.return_date.isoformat(), "填写返程日期(重试)")

    if not (from_ok and to_ok and date_ok):
        wait_for_manual_continue(
            page,
            "自动填写失败或页面结构已变化，请人工处理登录/验证码/搜索表单后再继续。",
        )

    if not _safe_click_search(page):
        wait_for_manual_continue(page, "搜索按钮找不到，请人工确认页面结构。")


def _try_switch_to_roundtrip(page: Page) -> None:
    log("尝试切换到往返模式")
    candidates = [
        page.get_by_text("往返", exact=True),
        page.get_by_text("往返"),
        page.get_by_role("tab", name="往返"),
        page.get_by_role("radio", name="往返"),
        page.locator("[data-tab='roundtrip']"),
        page.locator("[data-tab='round']"),
    ]
    for locator in candidates:
        try:
            if locator.count() == 0:
                continue
            locator.first.click(timeout=5_000)
            page.wait_for_timeout(1500)
            log("已切换到往返模式")
            return
        except PlaywrightError:
            continue
    log("无法自动切换到往返模式，将继续尝试填写返程日期")


def _wait_for_result_or_manual(
    page: Page,
    task_id: int | None = None,
    *,
    headless: bool,
    manual_takeover_enabled: bool,
) -> None:
    log("等待结果")
    deadline = time.monotonic() + RESULT_TIMEOUT_MS / 1000
    while True:
        _raise_if_cancelled(task_id)
        try:
            page.wait_for_load_state("networkidle", timeout=5_000)
            break
        except PlaywrightTimeoutError:
            if _looks_like_result_list(page):
                _dismiss_known_result_dialogs(page)
                break
            if time.monotonic() >= deadline:
                if _looks_like_manual_verification(page):
                    if headless or not manual_takeover_enabled:
                        _raise_page_error(PAGE_VERIFICATION_REQUIRED, "verification or risk-control page detected", page)
                    wait_for_manual_continue(page, "检测到登录、验证码或风控页面，请人工处理。", task_id)
                    return
                if headless or not manual_takeover_enabled:
                    _raise_page_error(PAGE_LOAD_TIMEOUT, "result page load timed out", page)
                wait_for_manual_continue(page, "等待结果超时，请人工确认页面是否已经完成搜索。", task_id)
                return

    _dismiss_known_result_dialogs(page)
    page_error_type = _classify_page_text(page)
    if page_error_type == PAGE_VERIFICATION_REQUIRED:
        if headless or not manual_takeover_enabled:
            _raise_page_error(page_error_type, "verification or risk-control page detected", page)
        wait_for_manual_continue(page, "检测到登录、验证码或风控提示，请人工处理。", task_id)
        return
    if page_error_type == PAGE_LOGIN_REQUIRED:
        if headless or not manual_takeover_enabled:
            _raise_page_error(page_error_type, "login page detected", page)
        wait_for_manual_continue(page, "检测到登录页面，请人工处理。", task_id)


def _click_outbound_by_rank(page: Page, rank: int) -> None:
    candidates = [
        page.get_by_text("选为去程"),
        page.get_by_text("選為去程"),
        page.get_by_text("订票"),
        page.get_by_text("訂票"),
        page.locator("button").filter(has_text="选为去程"),
        page.locator("button").filter(has_text="订票"),
    ]
    for locator in candidates:
        try:
            count = locator.count()
            if count >= rank:
                locator.nth(rank - 1).scroll_into_view_if_needed(timeout=5_000)
                locator.nth(rank - 1).click(timeout=10_000)
                return
        except PlaywrightError:
            continue
    raise PageStateError(PAGE_STRUCTURE_CHANGED, f"cannot find outbound select button for rank {rank}")


def _strategy_from_task(task: FlightQueryTask) -> dict:
    if not task.strategy_snapshot_json:
        return {}
    try:
        value = json.loads(task.strategy_snapshot_json)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _load_more_results_for_snapshot(page: Page, max_scrolls: int = 8) -> None:
    try:
        last_height = page.evaluate("() => document.body.scrollHeight")
    except PlaywrightError:
        return
    stable_count = 0
    for _ in range(max_scrolls):
        try:
            page.evaluate("() => window.scrollBy(0, Math.floor(window.innerHeight * 0.85))")
            page.wait_for_timeout(700)
            current_height = page.evaluate("() => document.body.scrollHeight")
        except PlaywrightError:
            break
        if current_height == last_height:
            stable_count += 1
            if stable_count >= 2:
                break
        else:
            stable_count = 0
            last_height = current_height
    try:
        page.evaluate("() => window.scrollTo(0, 0)")
        page.wait_for_timeout(300)
    except PlaywrightError:
        pass


def _page_visible_text(page: Page) -> str:
    try:
        text = page.locator("body").inner_text(timeout=10_000)
    except PlaywrightError:
        text = ""
    return normalize_text(text)


def _save_snapshot(page: Page, task_id: int, failed: bool = False, label: str | None = None) -> tuple[str | None, str | None]:
    suffix = "_failed" if failed else ""
    middle = f"_{label}" if label else ""
    screenshot_path = DATA_DIR / "screenshots" / f"task_{task_id}{middle}{suffix}.png"
    text_path = DATA_DIR / "text" / f"task_{task_id}{middle}{suffix}.txt"
    saved_screenshot = None
    saved_text = None

    _load_more_results_for_snapshot(page)

    try:
        log("保存截图")
        page.screenshot(path=str(screenshot_path), full_page=True, timeout=30_000)
        saved_screenshot = str(screenshot_path)
    except PlaywrightError as exc:
        log(f"截图保存失败: {exc}")

    try:
        log("保存可见文本")
        text_path.write_text(_page_visible_text(page), encoding="utf-8")
        saved_text = str(text_path)
    except Exception as exc:
        log(f"可见文本保存失败: {exc}")

    return saved_screenshot, saved_text


def _try_capture_failure_artifacts(
    page: Page | None,
    task_id: int,
    *,
    label: str | None = None,
    current_screenshot_path: str | None = None,
    current_text_path: str | None = None,
) -> tuple[str | None, str | None]:
    if not page:
        return current_screenshot_path, current_text_path
    try:
        screenshot_path, text_path = _save_snapshot(page, task_id, failed=True, label=label)
    except Exception as exc:
        log(f"保存失败现场时发生异常: {exc}")
        return current_screenshot_path, current_text_path
    return screenshot_path or current_screenshot_path, text_path or current_text_path


def _mark_failed(task_id: int, error_message: str, screenshot_path: str | None = None, text_path: str | None = None) -> None:
    with SessionLocal() as db:
        task = db.get(FlightQueryTask, task_id)
        if not task:
            return
        task.status = STATUS_FAILED
        task.error_message = error_message
        task.end_time = datetime.now()
        if screenshot_path:
            task.screenshot_path = screenshot_path
        if text_path:
            task.text_path = text_path
        task.html_path = None
        batch_no = task.batch_no
        db.commit()
        refresh_batch_counts(db, batch_no)


def _mark_cancelled(task_id: int) -> None:
    with SessionLocal() as db:
        task = db.get(FlightQueryTask, task_id)
        if not task:
            return
        task.status = STATUS_CANCELLED
        task.error_message = None
        task.end_time = datetime.now()
        batch_no = task.batch_no
        db.commit()
        refresh_batch_counts(db, batch_no)


def _expand_roundtrip_returns(
    page: Page,
    task_id: int,
    outbound_url: str,
    *,
    headless: bool,
    manual_takeover_enabled: bool,
) -> dict:
    total_returns = 0
    total_plans = 0
    failed = 0
    outbound_errors: list[dict[str, object]] = []
    with SessionLocal() as db:
        task = db.get(FlightQueryTask, task_id)
        if not task:
            raise ValueError(f"Query task not found: {task_id}")
        strategy = _strategy_from_task(task)
        if not strategy.get("roundtrip_expand_return"):
            return {"return_count": 0, "plan_count": 0, "failed_count": 0}
        outbounds = selected_outbounds_for_expansion(db, task, strategy)
        continue_on_failed = strategy.get("continue_on_expand_failed", True)
        fetch_limit = int(strategy.get("roundtrip_return_fetch_limit") or 10)

    for outbound in outbounds:
        rank = outbound.outbound_rank or 1
        try:
            with SessionLocal() as db:
                mark_outbound_status(db, outbound.id, RETURN_EXPANDING)
            page.goto(outbound_url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            _wait_for_result_or_manual(
                page,
                task_id,
                headless=headless,
                manual_takeover_enabled=manual_takeover_enabled,
            )
            _click_outbound_by_rank(page, rank)
            _wait_for_result_or_manual(
                page,
                task_id,
                headless=headless,
                manual_takeover_enabled=manual_takeover_enabled,
            )
            screenshot_path, text_path = _save_snapshot(page, task_id, label=f"outbound_rank_{rank}_return")
            if not text_path:
                raise PageStateError(PAGE_STRUCTURE_CHANGED, f"return snapshot text was not saved for outbound rank {rank}")
            with SessionLocal() as db:
                task = db.get(FlightQueryTask, task_id)
                outbound_row = db.get(FlightRoundTripOutbound, outbound.id)
                if not task or not outbound_row:
                    raise ValueError("Task or outbound disappeared during return expansion")
                parsed = parse_roundtrip_returns_for_outbound(db, task, outbound_row, text_path, screenshot_path, fetch_limit)
            if int(parsed.get("return_count") or 0) <= 0:
                raise PageStateError(PAGE_PARSE_ZERO_RESULT, f"no return rows parsed for outbound rank {rank}")
            total_returns += parsed["return_count"]
            total_plans += parsed["plan_count"]
        except Exception as exc:
            failed += 1
            failure_message = _build_failure_message(exc, page)
            if page:
                _save_snapshot(page, task_id, failed=True, label=f"outbound_rank_{rank}_return")
            with SessionLocal() as db:
                mark_outbound_status(db, outbound.id, RETURN_EXPAND_FAILED)
            outbound_errors.append(
                {
                    "outbound_id": outbound.id,
                    "outbound_rank": rank,
                    "error_type": _error_type_from_message(failure_message),
                    "error_message": failure_message,
                }
            )
            if not continue_on_failed:
                raise
    return {
        "return_count": total_returns,
        "plan_count": total_plans,
        "failed_count": failed,
        "outbound_errors": outbound_errors,
    }


def run_ctrip_task(task_id: int) -> dict:
    _prepare_playwright_event_loop()
    browser_lock_acquired = False
    try:
        _acquire_browser_lock(task_id)
        browser_lock_acquired = True
    except TaskCancelled:
        _mark_cancelled(task_id)
        return {"task_id": task_id, "status": STATUS_CANCELLED, "message": "Task cancelled before browser start"}
    page = None
    browser = None
    roundtrip_parsed_count = None
    roundtrip_expand_result = None
    final_status = STATUS_SUCCESS
    screenshot_path = None
    text_path = None
    try:
        with SessionLocal() as db:
            task = db.get(FlightQueryTask, task_id)
            if not task:
                raise ValueError(f"Query task not found: {task_id}")
            if task.status not in {STATUS_PENDING, STATUS_FAILED}:
                return {
                    "task_id": task_id,
                    "status": task.status,
                    "message": "Task status is not PENDING or FAILED; skipped.",
                }
            log(f"开始执行任务 task_id={task.id}, {task.from_city}->{task.to_city}, {task.depart_date}")
            task.status = STATUS_RUNNING
            task.error_message = None
            task.start_time = datetime.now()
            task.end_time = None
            db.commit()
            task_data = {
                "id": task.id,
                "trip_type": task.trip_type,
                "from_city": task.from_city,
                "from_airports": task.monitor.from_airports if task.monitor else None,
                "to_city": task.to_city,
                "to_airports": task.monitor.to_airports if task.monitor else None,
                "depart_date": task.depart_date,
                "return_date": task.return_date,
                "batch_no": task.batch_no,
                "manual_takeover_enabled": bool(task.monitor.manual_takeover_enabled) if task.monitor else True,
            }

        _sleep_before_single_task(task_id)
        with sync_playwright() as p:
            headless = get_headless()
            log(f"浏览器模式: {'无头' if headless else '有头'}")
            executable_path = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or None
            browser, profile_mode, profile_dir = _launch_browser_context(p, task_id, headless, executable_path)
            log(f"Browser context started: mode={profile_mode}, dir={profile_dir}")
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.set_default_timeout(30_000)
            try:
                try:
                    target_url = (
                        _build_roundtrip_list_url(type("TaskStub", (), task_data))
                        if task_data["trip_type"] == TRIP_ROUND_TRIP
                        else _build_list_url(type("TaskStub", (), task_data))
                    )
                    log(f"打开结果页 {target_url}")
                    page.goto(target_url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
                except PlaywrightTimeoutError as exc:
                    _raise_page_error(PAGE_LOAD_TIMEOUT, f"page navigation timed out: {exc}", page)

                _wait_for_result_or_manual(
                    page,
                    task_id,
                    headless=headless,
                    manual_takeover_enabled=bool(task_data["manual_takeover_enabled"]),
                )
                _validate_result_context(page, type("TaskStub", (), task_data), target_url)
                snapshot_label = "roundtrip_outbound" if task_data["trip_type"] == TRIP_ROUND_TRIP else None
                screenshot_path, text_path = _save_snapshot(page, task_id, label=snapshot_label)
                if task_data["trip_type"] == TRIP_ROUND_TRIP:
                    with SessionLocal() as db:
                        task = db.get(FlightQueryTask, task_id)
                        if not task:
                            raise ValueError(f"Query task not found during round-trip parse: {task_id}")
                        task.screenshot_path = screenshot_path
                        task.text_path = text_path
                        task.html_path = None
                        db.commit()
                        parsed = parse_roundtrip_outbounds_for_task(db, task)
                        roundtrip_parsed_count = parsed["parsed_count"]
                        if roundtrip_parsed_count <= 0:
                            _raise_page_error(PAGE_PARSE_ZERO_RESULT, "no outbound rows parsed", page)
                        strategy = _strategy_from_task(task)
                    if strategy.get("roundtrip_expand_return") and roundtrip_parsed_count > 0:
                        roundtrip_expand_result = _expand_roundtrip_returns(
                            page,
                            task_id,
                            target_url,
                            headless=headless,
                            manual_takeover_enabled=bool(task_data["manual_takeover_enabled"]),
                        )
            except Exception:
                screenshot_path, text_path = _try_capture_failure_artifacts(
                    page,
                    task_id,
                    current_screenshot_path=screenshot_path,
                    current_text_path=text_path,
                )
                raise
            finally:
                if browser:
                    try:
                        browser.close()
                    except PlaywrightError:
                        pass
                    browser = None

        with SessionLocal() as db:
            task = db.get(FlightQueryTask, task_id)
            if not task:
                raise ValueError(f"Query task not found after run: {task_id}")
            task.screenshot_path = screenshot_path
            task.text_path = text_path
            task.html_path = None
            task.end_time = datetime.now()
            task.error_message = None
            if task.trip_type == TRIP_ROUND_TRIP:
                parsed_count = roundtrip_parsed_count
                if parsed_count is None:
                    parsed = parse_roundtrip_outbounds_for_task(db, task)
                    parsed_count = parsed["parsed_count"]
                if parsed_count > 0:
                    plan_count = (roundtrip_expand_result or {}).get("plan_count", 0)
                    task.status = STATUS_SUCCESS if plan_count else STATUS_PARTIAL_SUCCESS
                    task.data_completeness = "FULL_ROUND_TRIP" if plan_count else COMPLETENESS_OUTBOUND_WITH_STARTING_PRICE
                    task.roundtrip_stage = "PLAN_GENERATED" if plan_count else "OUTBOUND_PARSED"
                else:
                    raise PageStateError(PAGE_PARSE_ZERO_RESULT, "no outbound rows parsed")
            else:
                task.status = STATUS_SUCCESS
            batch_no = task.batch_no
            final_status = task.status
            db.commit()
            refresh_batch_counts(db, batch_no)
        log("任务成功")
        return {
            "task_id": task_id,
            "status": final_status,
            "screenshot_path": screenshot_path,
            "text_path": text_path,
        }
    except Exception as exc:
        if isinstance(exc, TaskCancelled):
            log("任务已取消")
            if browser:
                try:
                    browser.close()
                except PlaywrightError:
                    pass
            _mark_cancelled(task_id)
            return {
                "task_id": task_id,
                "status": STATUS_CANCELLED,
                "message": "Task cancelled",
            }
        error_message = _build_failure_message(exc, page)
        log(f"任务失败: {error_message}")
        if browser:
            try:
                browser.close()
            except PlaywrightError:
                pass
        _mark_failed(task_id, error_message, screenshot_path, text_path)
        return {
            "task_id": task_id,
            "status": STATUS_FAILED,
            "error_type": _error_type_from_message(error_message),
            "error_message": error_message,
            "screenshot_path": screenshot_path,
            "text_path": text_path,
            "page_url": _safe_page_url(page),
            "page_title": _safe_page_title(page),
        }
    finally:
        if browser_lock_acquired and _browser_lock.locked():
            _browser_lock.release()
