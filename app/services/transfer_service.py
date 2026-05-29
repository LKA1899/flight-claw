from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FlightTransferCity
from app.services.monitor_service import get_monitor


def list_transfers(db: Session, monitor_id: int) -> list[FlightTransferCity]:
    return list(
        db.scalars(
            select(FlightTransferCity)
            .where(FlightTransferCity.monitor_id == monitor_id)
            .order_by(FlightTransferCity.sort_no, FlightTransferCity.id)
        )
    )


def enabled_transfers(db: Session, monitor_id: int) -> list[FlightTransferCity]:
    return list(
        db.scalars(
            select(FlightTransferCity)
            .where(FlightTransferCity.monitor_id == monitor_id, FlightTransferCity.enabled.is_(True))
            .order_by(FlightTransferCity.sort_no, FlightTransferCity.id)
        )
    )


def get_transfer(db: Session, transfer_id: int) -> FlightTransferCity:
    item = db.get(FlightTransferCity, transfer_id)
    if not item:
        raise ValueError("Transfer city not found")
    return item


def create_transfer(db: Session, monitor_id: int, data: dict) -> FlightTransferCity:
    get_monitor(db, monitor_id)
    item = FlightTransferCity(monitor_id=monitor_id, **data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_transfer(db: Session, transfer_id: int, data: dict) -> FlightTransferCity:
    item = get_transfer(db, transfer_id)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_transfer(db: Session, transfer_id: int) -> int:
    item = get_transfer(db, transfer_id)
    monitor_id = item.monitor_id
    db.delete(item)
    db.commit()
    return monitor_id


def toggle_transfer(db: Session, transfer_id: int) -> int:
    item = get_transfer(db, transfer_id)
    item.enabled = not item.enabled
    monitor_id = item.monitor_id
    db.commit()
    return monitor_id
