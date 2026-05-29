import secrets
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    STATUS_FAILED,
    STATUS_PARTIAL_SUCCESS,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
)
from app.models import FlightMonitor, FlightQueryTask, FlightScan, FlightScanStepLog


def make_scan_no() -> str:
    return f"SCAN_{datetime.now():%Y%m%d%H%M%S%f}_{secrets.token_hex(2)}"


def create_scan(db: Session, monitor: FlightMonitor | None, trigger_type: str) -> FlightScan:
    scan = FlightScan(
        scan_no=make_scan_no(),
        monitor_id=monitor.id if monitor else None,
        trigger_type=trigger_type,
        trip_type=monitor.trip_type if monitor else None,
        status=STATUS_PENDING,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    return scan


def refresh_scan_counts(db: Session, scan_id: int) -> FlightScan | None:
    scan = db.get(FlightScan, scan_id)
    if not scan:
        return None
    tasks = list(db.scalars(select(FlightQueryTask).where(FlightQueryTask.scan_id == scan_id)))
    scan.total_task_count = len(tasks)
    scan.success_task_count = sum(1 for task in tasks if task.status == STATUS_SUCCESS)
    scan.failed_task_count = sum(1 for task in tasks if task.status == STATUS_FAILED)
    scan.partial_task_count = sum(1 for task in tasks if task.status == STATUS_PARTIAL_SUCCESS)
    running_count = sum(1 for task in tasks if task.status == STATUS_RUNNING)
    pending_count = sum(1 for task in tasks if task.status == STATUS_PENDING)
    completed_count = scan.success_task_count + scan.failed_task_count + scan.partial_task_count

    if running_count or (pending_count and completed_count):
        scan.status = STATUS_RUNNING
        scan.end_time = None
    elif pending_count:
        scan.status = STATUS_PENDING
        scan.end_time = None
    elif tasks and scan.success_task_count == len(tasks):
        scan.status = STATUS_SUCCESS
        scan.end_time = datetime.now()
    elif tasks and scan.failed_task_count == len(tasks):
        scan.status = STATUS_FAILED
        scan.end_time = datetime.now()
    elif tasks:
        scan.status = STATUS_PARTIAL_SUCCESS
        scan.end_time = datetime.now()
    else:
        scan.status = STATUS_SKIPPED
        scan.end_time = datetime.now()
    db.commit()
    db.refresh(scan)
    return scan


def scan_dict(item: FlightScan) -> dict[str, Any]:
    monitor = item.monitor
    return {
        "id": item.id,
        "scan_no": item.scan_no,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "monitor_name": monitor.monitor_name if monitor else None,
        "from_city": monitor.from_city if monitor else None,
        "to_city": monitor.to_city if monitor else None,
        "trigger_type": item.trigger_type,
        "status": item.status,
        "trip_type": item.trip_type,
        "total_task_count": item.total_task_count,
        "success_task_count": item.success_task_count,
        "failed_task_count": item.failed_task_count,
        "partial_task_count": item.partial_task_count,
        "start_time": item.start_time.isoformat() if item.start_time else None,
        "end_time": item.end_time.isoformat() if item.end_time else None,
        "duration_seconds": int((item.end_time - item.start_time).total_seconds()) if item.start_time and item.end_time else None,
        "report_id": item.report_id,
        "error_message": item.error_message,
        "create_time": item.create_time.isoformat() if item.create_time else None,
    }


def step_log_dict(item: FlightScanStepLog) -> dict[str, Any]:
    return {
        "id": item.id,
        "scan_id": item.scan_id,
        "step_code": item.step_code,
        "step_name": item.step_name,
        "status": item.status,
        "input_json": item.input_json,
        "output_json": item.output_json,
        "error_message": item.error_message,
        "start_time": item.start_time.isoformat() if item.start_time else None,
        "end_time": item.end_time.isoformat() if item.end_time else None,
        "duration_seconds": int((item.end_time - item.start_time).total_seconds()) if item.start_time and item.end_time else None,
        "create_time": item.create_time.isoformat() if item.create_time else None,
    }
