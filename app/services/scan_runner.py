import json
import os
import random
import threading
import time
import traceback
from datetime import datetime
from typing import Any, Callable

from sqlalchemy import func, select

from app.constants import (
    STATUS_CANCEL_REQUESTED,
    STATUS_CANCELLED,
    STATUS_FAILED,
    STATUS_PARTIAL_SUCCESS,
    STATUS_PENDING,
    STATUS_QUEUED,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    TRIGGER_MANUAL,
)
from app.crawler.ctrip import run_ctrip_task
from app.db import SessionLocal
from app.models import (
    FlightBestDaily,
    FlightMonitor,
    FlightPriceRaw,
    FlightQueryTask,
    FlightReport,
    FlightRoundTripOutbound,
    FlightRoundTripPlan,
    FlightScan,
    FlightScanStepLog,
)
from app.services.analyze_service import analyze_best_daily
from app.services.monitor_service import get_monitor
from app.services.notify_service import send_and_log_notification
from app.services.plan_service import generate_plans_for_batch, generate_plans_from_outbounds
from app.services.price_parse_service import parse_task_price
from app.services.scan_service import create_scan, refresh_scan_counts
from app.services.settings_service import get_scan_interval_range
from app.services.task_service import generate_tasks_for_monitors, pending_ctrip_tasks_for_batch, successful_tasks_with_snapshot_for_batch

_dispatch_lock = threading.Lock()


SCAN_STEPS: list[tuple[str, str]] = [
    ("GENERATE_TASKS", "Generate query tasks"),
    ("RUN_BROWSER_SEARCH", "Run browser search"),
    ("SAVE_SNAPSHOT", "Save snapshot"),
    ("PARSE_RESULT", "Parse price results"),
    ("ANALYZE_RESULT", "Analyze results"),
    ("GENERATE_REPORT", "Generate report"),
]


def json_default(value: Any) -> str:
    if hasattr(value, "id"):
        return f"{value.__class__.__name__}(id={value.id})"
    return str(value)


class ScanPipeline:
    def __init__(self, scan_id: int):
        self.scan_id = scan_id
        self.context: dict[str, Any] = {"scan_id": scan_id}

    def run(self) -> None:
        with SessionLocal() as db:
            scan = db.get(FlightScan, self.scan_id)
            if not scan:
                raise ValueError(f"Scan not found: {self.scan_id}")
            if scan.status == STATUS_CANCEL_REQUESTED:
                scan.status = STATUS_CANCELLED
                scan.end_time = datetime.now()
                db.commit()
                return
            scan.status = STATUS_RUNNING
            scan.start_time = datetime.now()
            scan.end_time = None
            db.commit()

        for code, name in SCAN_STEPS:
            if self._cancel_requested():
                self._mark_cancelled()
                return
            self._run_step(code, name, getattr(self, f"_step_{code.lower()}"))
            with SessionLocal() as db:
                scan = db.get(FlightScan, self.scan_id)
                if scan and scan.status == STATUS_CANCELLED:
                    return

        with SessionLocal() as db:
            scan = refresh_scan_counts(db, self.scan_id)
            if scan and scan.status in {STATUS_RUNNING, STATUS_QUEUED, STATUS_PENDING}:
                scan.end_time = datetime.now()
                db.commit()

    def _cancel_requested(self) -> bool:
        with SessionLocal() as db:
            scan = db.get(FlightScan, self.scan_id)
            return bool(scan and scan.status == STATUS_CANCEL_REQUESTED)

    def _mark_cancelled(self) -> None:
        with SessionLocal() as db:
            scan = db.get(FlightScan, self.scan_id)
            if not scan:
                return
            tasks = list(db.scalars(select(FlightQueryTask).where(FlightQueryTask.scan_id == self.scan_id)))
            for task in tasks:
                if task.status in {STATUS_PENDING, STATUS_QUEUED, STATUS_CANCEL_REQUESTED, STATUS_RUNNING}:
                    task.status = STATUS_CANCELLED
                    task.end_time = datetime.now()
            scan.status = STATUS_CANCELLED
            scan.end_time = datetime.now()
            db.commit()

    def _run_step(self, code: str, name: str, fn: Callable[[], dict]) -> None:
        with SessionLocal() as db:
            log = FlightScanStepLog(
                scan_id=self.scan_id,
                step_code=code,
                step_name=name,
                status=STATUS_RUNNING,
                input_json=json.dumps(self.context, ensure_ascii=False, default=json_default),
                start_time=datetime.now(),
            )
            db.add(log)
            db.commit()
            log_id = log.id

        try:
            output = fn()
            if output:
                self.context[f"{code.lower()}_output"] = output
            with SessionLocal() as db:
                log = db.get(FlightScanStepLog, log_id)
                if log:
                    log.status = output.get("status", STATUS_SUCCESS) if output else STATUS_SUCCESS
                    log.output_json = json.dumps(output or {}, ensure_ascii=False, default=json_default)
                    log.end_time = datetime.now()
                    db.commit()
        except Exception as exc:
            error = "".join(traceback.format_exception_only(type(exc), exc)).strip()
            with SessionLocal() as db:
                log = db.get(FlightScanStepLog, log_id)
                scan = db.get(FlightScan, self.scan_id)
                if log:
                    log.status = STATUS_FAILED
                    log.error_message = error
                    log.output_json = json.dumps({"error": error}, ensure_ascii=False)
                    log.end_time = datetime.now()
                if scan:
                    scan.status = STATUS_FAILED
                    scan.error_message = error
                    scan.end_time = datetime.now()
                db.commit()
            raise

    def _step_generate_tasks(self) -> dict:
        with SessionLocal() as db:
            scan = db.get(FlightScan, self.scan_id)
            if not scan or not scan.monitor_id:
                raise ValueError("Scan monitor_id is required for monitor scan")
            monitor = db.get(FlightMonitor, scan.monitor_id)
            if not monitor:
                raise ValueError(f"Monitor not found: {scan.monitor_id}")
            existing_tasks = []
            if scan.batch_no:
                existing_tasks = list(db.scalars(select(FlightQueryTask).where(FlightQueryTask.scan_id == scan.id)))
            if existing_tasks:
                batch_no = scan.batch_no
                task_count = len(existing_tasks)
                executable_task_count = sum(1 for task in existing_tasks if task.status == STATUS_PENDING)
                warnings = ["Reused existing scan tasks; successful tasks were not recreated."]
            else:
                batch, task_count, warnings = generate_tasks_for_monitors(
                    db,
                    [monitor],
                    scan_id=scan.id,
                    trigger_type=scan.trigger_type,
                )
                batch_no = batch.batch_no
                scan.batch_no = batch_no
                executable_task_count = task_count
            scan.total_task_count = task_count
            db.commit()
            self.context["batch_no"] = batch_no
            self.context["generated_task_count"] = executable_task_count
            self.context["generate_task_warnings"] = warnings
            return {
                "batch_no": batch_no,
                "total_task_count": task_count,
                "executable_task_count": executable_task_count,
                "warnings": warnings,
                "status": STATUS_SKIPPED if task_count == 0 else STATUS_SUCCESS,
            }

    def _step_run_browser_search(self) -> dict:
        batch_no = self.context.get("batch_no")
        if not batch_no:
            return {"message": "No batch_no in context; skipped.", "total": 0, "status": STATUS_SKIPPED}
        if int(self.context.get("generated_task_count") or 0) == 0:
            return {"message": "No generated tasks; browser search skipped.", "total": 0, "status": STATUS_SKIPPED}
        with SessionLocal() as db:
            tasks = pending_ctrip_tasks_for_batch(db, batch_no)
        success_count = 0
        failed_count = 0
        results = []
        failed_task_ids: list[int] = []
        failed_error_types: list[str] = []
        for index, task in enumerate(tasks):
            if self._cancel_requested():
                self._mark_cancelled()
                return {"message": "Scan cancelled before remaining browser tasks.", "status": STATUS_CANCELLED}
            if index > 0:
                self._sleep_between_batch_tasks()
                if self._cancel_requested():
                    self._mark_cancelled()
                    return {"message": "Scan cancelled between browser tasks.", "status": STATUS_CANCELLED}
            result = run_ctrip_task(task.id)
            results.append(result)
            if result.get("status") == STATUS_CANCELLED:
                self._mark_cancelled()
                return {"message": "Scan cancelled during browser search.", "status": STATUS_CANCELLED}
            if result.get("status") == STATUS_FAILED:
                failed_count += 1
                failed_task_ids.append(task.id)
                error_type = result.get("error_type")
                if isinstance(error_type, str) and error_type:
                    failed_error_types.append(error_type)
            else:
                success_count += 1
            with SessionLocal() as db:
                refresh_scan_counts(db, self.scan_id)
        return {
            "batch_no": batch_no,
            "total": len(tasks),
            "success_task_count": success_count,
            "failed_task_count": failed_count,
            "failed_task_ids": failed_task_ids,
            "failed_error_types": sorted(set(failed_error_types)),
            "partial_failed": failed_count > 0,
            "status": (
                STATUS_FAILED
                if tasks and failed_count == len(tasks)
                else STATUS_PARTIAL_SUCCESS if failed_count > 0 else STATUS_SUCCESS
            ),
            "results": results,
        }

    def _sleep_between_batch_tasks(self) -> None:
        interval_min_seconds, interval_max_seconds = get_scan_interval_range()
        seconds = random.uniform(interval_min_seconds, interval_max_seconds)
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            if self._cancel_requested():
                self._mark_cancelled()
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            time.sleep(min(1.0, remaining))

    def _step_parse_result(self) -> dict:
        batch_no = self.context.get("batch_no")
        if not batch_no:
            return {"message": "No batch_no in context; skipped.", "total_task_count": 0, "status": STATUS_SKIPPED}
        if int(self.context.get("generated_task_count") or 0) == 0:
            return {"message": "No generated tasks; price parsing skipped.", "total_task_count": 0, "status": STATUS_SKIPPED}
        with SessionLocal() as db:
            tasks = successful_tasks_with_snapshot_for_batch(db, batch_no)
        parsed_task_count = 0
        failed_task_count = 0
        total_price_item_count = 0
        results = []
        for task in tasks:
            try:
                result = parse_task_price(task.id)
            except Exception as exc:
                result = {"task_id": task.id, "parsed_count": 0, "failed_count": 1, "warnings": [str(exc)]}
            results.append(result)
            parsed_count = int(result.get("parsed_count") or 0)
            total_price_item_count += parsed_count
            if parsed_count > 0:
                parsed_task_count += 1
            else:
                failed_task_count += 1
        if tasks and total_price_item_count == 0:
            raise RuntimeError("No price items parsed from any task in this scan")
        if not tasks and int(self.context.get("generated_task_count") or 0) > 0:
            return {"message": "No SUCCESS tasks with text snapshot found for price parsing", "status": STATUS_SKIPPED}
        return {
            "batch_no": batch_no,
            "total_task_count": len(tasks),
            "parsed_task_count": parsed_task_count,
            "failed_task_count": failed_task_count,
            "total_price_item_count": total_price_item_count,
            "partial_failed": failed_task_count > 0,
            "status": STATUS_PARTIAL_SUCCESS if failed_task_count > 0 else STATUS_SUCCESS,
            "results": results,
        }

    def _step_save_snapshot(self) -> dict:
        batch_no = self.context.get("batch_no")
        if not batch_no:
            return {"message": "No batch_no in context; skipped.", "status": STATUS_SKIPPED}
        with SessionLocal() as db:
            tasks = list(db.scalars(select(FlightQueryTask).where(FlightQueryTask.batch_no == batch_no)))
        screenshot_count = sum(1 for task in tasks if task.screenshot_path)
        text_count = sum(1 for task in tasks if task.text_path)
        return {
            "batch_no": batch_no,
            "total_task_count": len(tasks),
            "screenshot_count": screenshot_count,
            "text_count": text_count,
            "message": "Snapshots are written by the browser search step and summarized here.",
        }

    def _step_analyze_result(self) -> dict:
        batch_no = self.context.get("batch_no")
        if not batch_no:
            raise RuntimeError("No batch_no in context for scan analysis")
        if int(self.context.get("generated_task_count") or 0) == 0:
            return {"message": "No generated tasks; analysis skipped.", "status": STATUS_SKIPPED}
        plan_result = generate_plans_for_batch(batch_no)
        outbound_plan_result = generate_plans_from_outbounds(batch_no)
        plan_result["outbound_clues"] = outbound_plan_result
        analyze_result = analyze_best_daily(batch_no)
        with SessionLocal() as db:
            roundtrip_plan_count = db.scalar(select(func.count(FlightRoundTripPlan.id)).where(FlightRoundTripPlan.batch_no == batch_no)) or 0
            roundtrip_clue_count = db.scalar(select(func.count(FlightRoundTripOutbound.id)).where(FlightRoundTripOutbound.batch_no == batch_no)) or 0
        return {
            "batch_no": batch_no,
            "plan_result": plan_result,
            "analyze_result": analyze_result,
            "roundtrip_plan_count": roundtrip_plan_count,
            "roundtrip_clue_count": roundtrip_clue_count,
        }

    def _step_generate_report(self) -> dict:
        with SessionLocal() as db:
            scan = db.get(FlightScan, self.scan_id)
            if not scan:
                raise ValueError("Scan not found")
            batch_no = scan.batch_no
            price_count = db.scalar(select(func.count(FlightPriceRaw.id)).where(FlightPriceRaw.batch_no == batch_no)) if batch_no else 0
            best_items = list(db.scalars(select(FlightBestDaily).where(FlightBestDaily.batch_no == batch_no))) if batch_no else []
            roundtrip_plans = list(db.scalars(select(FlightRoundTripPlan).where(FlightRoundTripPlan.batch_no == batch_no))) if batch_no else []
            roundtrip_clues = list(db.scalars(select(FlightRoundTripOutbound).where(FlightRoundTripOutbound.batch_no == batch_no))) if batch_no else []
            monitor_label = scan.monitor.monitor_name if scan.monitor else f"Monitor#{scan.monitor_id}"
            title = f"{monitor_label} · {scan.scan_no}"
            lines = [
                f"# {title}",
                "",
                f"- 路线: {monitor_label}",
                f"- Scan No: {scan.scan_no}",
                f"- Batch No: {batch_no or '-'}",
                f"- Trigger: {scan.trigger_type}",
                f"- Tasks: {scan.success_task_count}/{scan.total_task_count} success, {scan.failed_task_count} failed, {scan.partial_task_count} partial",
                f"- Price Rows: {price_count or 0}",
                f"- Round-trip Plans: {len(roundtrip_plans)}",
                f"- Round-trip Clues: {len(roundtrip_clues)}",
            ]
            if best_items:
                lines.extend(["", "## Best Results"])
                for item in best_items:
                    lines.append(f"- {item.monitor.monitor_name if item.monitor else item.monitor_id} / {item.depart_date}: {item.summary or '-'}")
            report = FlightReport(
                scan_id=scan.id,
                monitor_id=scan.monitor_id,
                batch_no=batch_no,
                title=title,
                content_md="\n".join(lines),
            )
            db.add(report)
            db.flush()
            scan.report_id = report.id
            db.commit()
            return {"report_id": report.id, "title": title}


def _build_scan_notification(scan: FlightScan) -> tuple[str, str]:
    monitor_label = scan.monitor.monitor_name if scan.monitor else f"Monitor#{scan.monitor_id}"
    title = f"{monitor_label} · {scan.scan_no}"
    lines = [
        f"## {title}",
        "",
        f"- 状态: {scan.status}",
        f"- 触发方式: {scan.trigger_type}",
        f"- 任务: {scan.success_task_count}/{scan.total_task_count} 成功, {scan.failed_task_count} 失败, {scan.partial_task_count} 部分成功",
    ]
    if scan.batch_no:
        with SessionLocal() as db:
            price_count = db.scalar(select(func.count(FlightPriceRaw.id)).where(FlightPriceRaw.batch_no == scan.batch_no)) or 0
            best_count = db.scalar(select(func.count(FlightBestDaily.id)).where(FlightBestDaily.batch_no == scan.batch_no)) or 0
            plan_count = db.scalar(select(func.count(FlightRoundTripPlan.id)).where(FlightRoundTripPlan.batch_no == scan.batch_no)) or 0
            clue_count = db.scalar(select(func.count(FlightRoundTripOutbound.id)).where(FlightRoundTripOutbound.batch_no == scan.batch_no)) or 0
        lines.extend([
            f"- 价格行: {price_count}",
            f"- 今日机会: {best_count}",
            f"- 往返组合: {plan_count}",
            f"- 往返线索: {clue_count}",
        ])
    if scan.error_message:
        lines.extend(["", f"错误: {scan.error_message}"])
    return title, "\n".join(lines)


def _run_scan_thread(scan_id: int) -> None:
    try:
        ScanPipeline(scan_id).run()
    except BaseException as exc:
        error = "".join(traceback.format_exception_only(type(exc), exc)).strip()
        with SessionLocal() as db:
            scan = db.get(FlightScan, scan_id)
            if scan:
                scan.status = STATUS_FAILED
                scan.error_message = error
                scan.end_time = datetime.now()
                db.commit()
    finally:
        with SessionLocal() as db:
            scan = db.get(FlightScan, scan_id)
            if scan and scan.monitor_id:
                monitor = db.get(FlightMonitor, scan.monitor_id)
                if monitor:
                    monitor.last_scan_id = scan.id
                    monitor.last_scan_time = scan.end_time or datetime.now()
                    monitor.last_scan_status = scan.status
                    db.commit()
                # send notification after monitor status is updated
                try:
                    title, content = _build_scan_notification(scan)
                    send_and_log_notification(title, content, batch_no=scan.batch_no)
                except Exception:
                    pass  # notification failure must not affect scan status
        dispatch_queued_scans()


def _max_running_route_scans() -> int:
    try:
        return max(1, int(os.getenv("MAX_RUNNING_ROUTE_SCANS", "2")))
    except ValueError:
        return 2


def _active_scan_for_monitor(db, monitor_id: int) -> FlightScan | None:
    return db.scalar(
        select(FlightScan)
        .where(
            FlightScan.monitor_id == monitor_id,
            FlightScan.status.in_([STATUS_QUEUED, STATUS_RUNNING, STATUS_CANCEL_REQUESTED]),
        )
        .order_by(FlightScan.id.desc())
    )


def _running_route_count(db) -> int:
    return db.scalar(
        select(func.count(FlightScan.id)).where(
            FlightScan.status == STATUS_RUNNING,
            FlightScan.monitor_id.isnot(None),
        )
    ) or 0


def _start_scan_thread(scan_id: int) -> None:
    thread = threading.Thread(target=_run_scan_thread, args=(scan_id,), daemon=True)
    thread.start()


def dispatch_queued_scans() -> None:
    with _dispatch_lock:
        with SessionLocal() as db:
            capacity = _max_running_route_scans() - _running_route_count(db)
            if capacity <= 0:
                return
            running_monitor_ids = {
                row[0]
                for row in db.execute(
                    select(FlightScan.monitor_id).where(
                        FlightScan.status == STATUS_RUNNING,
                        FlightScan.monitor_id.isnot(None),
                    )
                ).all()
            }
            queued = list(
                db.scalars(
                    select(FlightScan)
                    .where(FlightScan.status == STATUS_QUEUED)
                    .order_by(FlightScan.id)
                )
            )
            scan_ids = []
            for scan in queued:
                if scan.monitor_id in running_monitor_ids:
                    continue
                scan.status = STATUS_RUNNING
                scan_ids.append(scan.id)
                if scan.monitor_id:
                    running_monitor_ids.add(scan.monitor_id)
                if len(scan_ids) >= capacity:
                    break
            db.commit()
        for scan_id in scan_ids:
            _start_scan_thread(scan_id)


def scan_monitor(db, monitor_id: int, trigger_type: str = TRIGGER_MANUAL) -> FlightScan:
    monitor = get_monitor(db, monitor_id)
    active = _active_scan_for_monitor(db, monitor_id)
    if active:
        return active
    scan = create_scan(db, monitor, trigger_type)
    scan.status = STATUS_QUEUED
    monitor.last_scan_id = scan.id
    monitor.last_scan_time = datetime.now()
    monitor.last_scan_status = scan.status
    db.commit()
    dispatch_queued_scans()
    return scan


def cancel_scan(db, scan_id: int) -> FlightScan:
    scan = db.get(FlightScan, scan_id)
    if not scan:
        raise ValueError(f"Scan not found: {scan_id}")
    tasks = list(db.scalars(select(FlightQueryTask).where(FlightQueryTask.scan_id == scan_id)))
    if scan.status == STATUS_QUEUED:
        scan.status = STATUS_CANCELLED
        scan.end_time = datetime.now()
    elif scan.status == STATUS_RUNNING:
        scan.status = STATUS_CANCEL_REQUESTED
    elif scan.status == STATUS_PENDING:
        scan.status = STATUS_CANCELLED
        scan.end_time = datetime.now()
    for task in tasks:
        if task.status in {STATUS_PENDING, STATUS_QUEUED}:
            task.status = STATUS_CANCELLED
            task.end_time = datetime.now()
        elif task.status == STATUS_RUNNING:
            task.status = STATUS_CANCEL_REQUESTED
    if scan.monitor_id:
        monitor = db.get(FlightMonitor, scan.monitor_id)
        if monitor:
            monitor.last_scan_id = scan.id
            monitor.last_scan_time = datetime.now()
            monitor.last_scan_status = scan.status
    db.commit()
    db.refresh(scan)
    return scan


def cancel_running_monitor_scan(db, monitor_id: int) -> FlightScan | None:
    scan = _active_scan_for_monitor(db, monitor_id)
    if not scan:
        return None
    return cancel_scan(db, scan.id)


def restart_scan(db, scan_id: int) -> FlightScan:
    scan = db.get(FlightScan, scan_id)
    if not scan:
        raise ValueError(f"Scan not found: {scan_id}")
    if scan.monitor_id:
        active = _active_scan_for_monitor(db, scan.monitor_id)
        if active and active.id != scan.id:
            return active
    tasks = list(db.scalars(select(FlightQueryTask).where(FlightQueryTask.scan_id == scan_id)))
    for task in tasks:
        if task.status in {STATUS_FAILED, STATUS_CANCELLED, STATUS_CANCEL_REQUESTED, STATUS_PENDING}:
            task.status = STATUS_PENDING
            task.error_message = None
            task.start_time = None
            task.end_time = None
    scan.status = STATUS_QUEUED
    scan.error_message = None
    scan.end_time = None
    if scan.monitor_id:
        monitor = db.get(FlightMonitor, scan.monitor_id)
        if monitor:
            monitor.last_scan_id = scan.id
            monitor.last_scan_time = datetime.now()
            monitor.last_scan_status = scan.status
    db.commit()
    dispatch_queued_scans()
    db.refresh(scan)
    return scan
