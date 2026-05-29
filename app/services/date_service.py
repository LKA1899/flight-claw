from datetime import date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import FlightMonitorDate
from app.services.monitor_service import get_monitor


def parse_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def list_dates(db: Session, monitor_id: int) -> list[FlightMonitorDate]:
    return list(
        db.scalars(
            select(FlightMonitorDate)
            .where(FlightMonitorDate.monitor_id == monitor_id)
            .order_by(FlightMonitorDate.depart_date, FlightMonitorDate.return_date)
        )
    )


def add_date(
    db: Session,
    monitor_id: int,
    depart_date: date,
    remark: str | None = None,
    return_date: date | None = None,
) -> bool:
    get_monitor(db, monitor_id)
    item = FlightMonitorDate(
        monitor_id=monitor_id,
        depart_date=depart_date,
        return_date=return_date,
        enabled=True,
        remark=remark,
    )
    db.add(item)
    try:
        db.commit()
        return True
    except IntegrityError:
        db.rollback()
        return False


def batch_add_dates(
    db: Session,
    monitor_id: int,
    start_date: date,
    end_date: date,
    weekdays: set[int],
    return_start_date: date | None = None,
    return_end_date: date | None = None,
) -> tuple[int, int]:
    if end_date < start_date:
        raise ValueError("end_date must be greater than or equal to start_date")
    get_monitor(db, monitor_id)
    created = 0
    skipped = 0

    depart_dates: list[date] = []
    current = start_date
    while current <= end_date:
        if not weekdays or current.isoweekday() in weekdays:
            depart_dates.append(current)
        current += timedelta(days=1)

    if return_start_date and return_end_date:
        return_dates: list[date] = []
        current = return_start_date
        while current <= return_end_date:
            if not weekdays or current.isoweekday() in weekdays:
                return_dates.append(current)
            current += timedelta(days=1)

        for d in depart_dates:
            for r in return_dates:
                if add_date(db, monitor_id, d, return_date=r):
                    created += 1
                else:
                    skipped += 1
    else:
        for d in depart_dates:
            if add_date(db, monitor_id, d):
                created += 1
            else:
                skipped += 1

    return created, skipped


def delete_date(db: Session, date_id: int) -> int:
    item = db.get(FlightMonitorDate, date_id)
    if not item:
        raise ValueError("Date not found")
    monitor_id = item.monitor_id
    db.delete(item)
    db.commit()
    return monitor_id


def toggle_date(db: Session, date_id: int) -> int:
    item = db.get(FlightMonitorDate, date_id)
    if not item:
        raise ValueError("Date not found")
    item.enabled = not item.enabled
    monitor_id = item.monitor_id
    db.commit()
    return monitor_id


def enabled_dates_for_monitor(db: Session, monitor_id: int) -> list[FlightMonitorDate]:
    return list(
        db.scalars(
            select(FlightMonitorDate)
            .where(FlightMonitorDate.monitor_id == monitor_id, FlightMonitorDate.enabled.is_(True))
            .order_by(FlightMonitorDate.depart_date, FlightMonitorDate.return_date)
        )
    )
