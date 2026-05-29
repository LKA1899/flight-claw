from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import FlightMonitor, FlightMonitorDate


def list_monitors(db: Session) -> list[tuple[FlightMonitor, int]]:
    stmt = (
        select(FlightMonitor, func.count(FlightMonitorDate.id))
        .outerjoin(FlightMonitorDate)
        .group_by(FlightMonitor.id)
        .order_by(FlightMonitor.id.desc())
    )
    return list(db.execute(stmt).all())


def get_monitor(db: Session, monitor_id: int) -> FlightMonitor:
    monitor = db.get(FlightMonitor, monitor_id)
    if not monitor:
        raise ValueError("Monitor not found")
    return monitor


def create_monitor(db: Session, data: dict) -> FlightMonitor:
    monitor = FlightMonitor(**data)
    db.add(monitor)
    db.commit()
    db.refresh(monitor)
    return monitor


def update_monitor(db: Session, monitor_id: int, data: dict) -> FlightMonitor:
    monitor = get_monitor(db, monitor_id)
    for key, value in data.items():
        setattr(monitor, key, value)
    db.commit()
    db.refresh(monitor)
    return monitor


def delete_monitor(db: Session, monitor_id: int) -> None:
    monitor = get_monitor(db, monitor_id)
    db.delete(monitor)
    db.commit()


def toggle_monitor(db: Session, monitor_id: int) -> FlightMonitor:
    monitor = get_monitor(db, monitor_id)
    monitor.enabled = not monitor.enabled
    db.commit()
    db.refresh(monitor)
    return monitor


def enabled_monitors(db: Session) -> list[FlightMonitor]:
    return list(db.scalars(select(FlightMonitor).where(FlightMonitor.enabled.is_(True)).order_by(FlightMonitor.id)))
