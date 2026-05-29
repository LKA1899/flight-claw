import asyncio
import json
import os
import random
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.constants import (
    COMPLETENESS_OUTBOUND_WITH_STARTING_PRICE,
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


def _prepare_playwright_event_loop() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

class ManualInterventionRequired(RuntimeError):
    """Raised when the user must handle login, captcha, or changed page structure."""


def log(message: str) -> None:
    print(f"[FlightClaw][CTRIP] {datetime.now():%Y-%m-%d %H:%M:%S} {message}", flush=True)


def wait_for_manual_continue(page: Page, message: str) -> None:
    log("需要人工接管")
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
                button.textContent = "我已处理，继续";
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
        page.wait_for_function("() => window.__flightclawManualContinue === true", timeout=MANUAL_CONTINUE_TIMEOUT_MS)
        log("人工接管已确认，继续执行")
        return
    except PlaywrightTimeoutError as exc:
        raise ManualInterventionRequired("Manual intervention timed out") from exc
    except PlaywrightError:
        pass
    raise ManualInterventionRequired(message)


def _sleep_before_single_task() -> None:
    seconds = random.uniform(3, 8)
    log(f"低频控制：执行前等待 {seconds:.1f} 秒")
    time.sleep(seconds)


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
    current_url = page.url.lower()
    expected_from = _normalize_city_code(_city_code(task.from_city, getattr(task, "from_airports", None)))
    expected_to = _normalize_city_code(_city_code(task.to_city, getattr(task, "to_airports", None)))
    list_marker = "/online/list/" in current_url
    channel_marker = "/online/channel" in current_url
    route_marker = f"-{expected_from}-{expected_to}" in current_url

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

    raise RuntimeError(
        "Ctrip search did not land on the requested result page. "
        f"expected_url={expected_url}, current_url={page.url}, "
        f"route={task.from_city}->{task.to_city}, depart_date={task.depart_date}"
    )


def _looks_like_manual_verification(page: Page) -> bool:
    keywords = ["验证码", "滑块", "人机验证", "安全验证", "访问异常", "网络环境异常", "请完成验证"]
    try:
        text = page.locator("body").inner_text(timeout=5_000)
    except PlaywrightError:
        return False
    return any(keyword in text for keyword in keywords)


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


def _wait_for_result_or_manual(page: Page) -> None:
    log("等待结果")
    try:
        page.wait_for_load_state("networkidle", timeout=RESULT_TIMEOUT_MS)
    except PlaywrightTimeoutError:
        if _looks_like_manual_verification(page):
            wait_for_manual_continue(page, "检测到登录、验证码或风控页面，请人工处理。")
        wait_for_manual_continue(page, "等待结果超时，请人工确认页面是否已经完成搜索。")

    if _looks_like_manual_verification(page):
        wait_for_manual_continue(page, "检测到登录、验证码或风控提示，请人工处理。")


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
    raise ManualInterventionRequired(f"Cannot find outbound select button for rank {rank}")


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


def _expand_roundtrip_returns(page: Page, task_id: int, outbound_url: str) -> dict:
    total_returns = 0
    total_plans = 0
    failed = 0
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
            _wait_for_result_or_manual(page)
            _click_outbound_by_rank(page, rank)
            _wait_for_result_or_manual(page)
            screenshot_path, text_path = _save_snapshot(page, task_id, label=f"outbound_rank_{rank}_return")
            if not text_path:
                raise RuntimeError("Return text snapshot was not saved")
            with SessionLocal() as db:
                task = db.get(FlightQueryTask, task_id)
                outbound_row = db.get(FlightRoundTripOutbound, outbound.id)
                if not task or not outbound_row:
                    raise ValueError("Task or outbound disappeared during return expansion")
                parsed = parse_roundtrip_returns_for_outbound(db, task, outbound_row, text_path, screenshot_path, fetch_limit)
            total_returns += parsed["return_count"]
            total_plans += parsed["plan_count"]
        except Exception:
            failed += 1
            with SessionLocal() as db:
                mark_outbound_status(db, outbound.id, RETURN_EXPAND_FAILED)
            if not continue_on_failed:
                raise
    return {"return_count": total_returns, "plan_count": total_plans, "failed_count": failed}


def run_ctrip_task(task_id: int) -> dict:
    _prepare_playwright_event_loop()
    if not _browser_lock.acquire(blocking=False):
        raise RuntimeError("已有浏览器查询正在执行，请等待当前任务完成后再试。")
    page = None
    browser = None
    roundtrip_parsed_count = None
    roundtrip_expand_result = None
    final_status = STATUS_SUCCESS
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
            }

        _sleep_before_single_task()
        with sync_playwright() as p:
            profile_dir = DATA_DIR / "browser_profile" / "ctrip"
            profile_dir.mkdir(parents=True, exist_ok=True)
            headless = get_headless()
            log(f"浏览器模式: {'无头' if headless else '有头'}")
            executable_path = os.getenv("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH") or None
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(profile_dir),
                executable_path=executable_path,
                headless=headless,
                viewport={"width": 1440, "height": 900},
            )
            page = browser.pages[0] if browser.pages else browser.new_page()
            page.set_default_timeout(30_000)

            try:
                target_url = (
                    _build_roundtrip_list_url(type("TaskStub", (), task_data))
                    if task_data["trip_type"] == TRIP_ROUND_TRIP
                    else _build_list_url(type("TaskStub", (), task_data))
                )
                log(f"打开结果页 {target_url}")
                page.goto(target_url, wait_until="domcontentloaded", timeout=GOTO_TIMEOUT_MS)
            except PlaywrightTimeoutError as exc:
                raise RuntimeError(f"页面打不开或加载超时: {exc}") from exc

            _wait_for_result_or_manual(page)
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
                    strategy = _strategy_from_task(task)
                if strategy.get("roundtrip_expand_return") and roundtrip_parsed_count > 0:
                    roundtrip_expand_result = _expand_roundtrip_returns(page, task_id, target_url)
            browser.close()
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
                    task.status = STATUS_FAILED
                    task.error_message = "No round-trip outbound rows parsed"
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
        error_message = str(exc)
        log(f"任务失败: {error_message}")
        screenshot_path = None
        text_path = None
        if page:
            screenshot_path, text_path = _save_snapshot(page, task_id, failed=True)
        if browser:
            try:
                browser.close()
            except PlaywrightError:
                pass
        _mark_failed(task_id, error_message, screenshot_path, text_path)
        return {
            "task_id": task_id,
            "status": STATUS_FAILED,
            "error_message": error_message,
            "screenshot_path": screenshot_path,
            "text_path": text_path,
        }
    finally:
        _browser_lock.release()
