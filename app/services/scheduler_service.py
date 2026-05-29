from datetime import datetime

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.constants import STATUS_RUNNING, TRIGGER_SCHEDULED
from app.db import SessionLocal
from app.models import FlightMonitor, FlightScan
from app.services.scan_runner import scan_monitor

scheduler = BackgroundScheduler()


def _run_scheduled_monitor_scan(monitor_id: int) -> None:
    try:
        with SessionLocal() as db:
            running = db.scalar(
                select(FlightScan).where(
                    FlightScan.monitor_id == monitor_id,
                    FlightScan.status == STATUS_RUNNING,
                )
            )
            monitor = db.get(FlightMonitor, monitor_id)
            if not monitor:
                return
            if running:
                monitor.last_scan_time = datetime.now()
                monitor.last_scan_status = "SKIPPED_RUNNING"
                db.commit()
                return
            scan = scan_monitor(db, monitor_id, TRIGGER_SCHEDULED)
            monitor.last_scan_id = scan.id
            monitor.last_scan_time = datetime.now()
            monitor.last_scan_status = scan.status
            db.commit()
    except Exception as exc:
        with SessionLocal() as db:
            monitor = db.get(FlightMonitor, monitor_id)
            if monitor:
                monitor.last_scan_time = datetime.now()
                monitor.last_scan_status = "FAILED"
                monitor.schedule_remark = f"Last scheduler error: {exc}"
                db.commit()


def _register_enabled_jobs() -> int:
    count = 0
    with SessionLocal() as db:
        monitors = db.scalars(
            select(FlightMonitor).where(
                FlightMonitor.enabled.is_(True),
                FlightMonitor.schedule_enabled.is_(True),
                FlightMonitor.schedule_cron.is_not(None),
            )
        )
        for monitor in monitors:
            try:
                trigger = CronTrigger.from_crontab(
                    monitor.schedule_cron,
                    timezone=monitor.schedule_timezone or "Asia/Shanghai",
                )
            except ValueError:
                monitor.last_scan_status = "INVALID_CRON"
                db.commit()
                continue
            job = scheduler.add_job(
                _run_scheduled_monitor_scan,
                trigger,
                args=[monitor.id],
                id=f"monitor_scan_{monitor.id}",
                replace_existing=True,
            )
            monitor.next_scan_time = job.next_run_time.replace(tzinfo=None) if job.next_run_time else None
            count += 1

        db.commit()
    return count


def start_scheduler() -> None:
    if not scheduler.running:
        scheduler.start()
    refresh_scheduler()


def refresh_scheduler() -> dict:
    if not scheduler.running:
        scheduler.start()
    for job in scheduler.get_jobs():
        if job.id.startswith("monitor_scan_"):
            scheduler.remove_job(job.id)
    with SessionLocal() as db:
        for monitor in db.scalars(select(FlightMonitor).where(FlightMonitor.next_scan_time.is_not(None))):
            monitor.next_scan_time = None
        db.commit()
    count = _register_enabled_jobs()
    return {"scheduled_job_count": count}


def scheduled_jobs() -> list[dict]:
    if not scheduler.running:
        return []
    return [
        {
            "id": job.id,
            "next_run_time": job.next_run_time,
            "trigger": str(job.trigger),
        }
        for job in scheduler.get_jobs()
        if job.id.startswith("monitor_scan_")
    ]


def shutdown_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=True)
