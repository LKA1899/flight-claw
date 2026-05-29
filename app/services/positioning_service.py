from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import FlightPositioningCity
from app.services.monitor_service import get_monitor


def list_positionings(db: Session, monitor_id: int) -> list[FlightPositioningCity]:
    return list(
        db.scalars(
            select(FlightPositioningCity)
            .where(FlightPositioningCity.monitor_id == monitor_id)
            .order_by(FlightPositioningCity.sort_no, FlightPositioningCity.id)
        )
    )


def enabled_positionings(db: Session, monitor_id: int) -> list[FlightPositioningCity]:
    return list(
        db.scalars(
            select(FlightPositioningCity)
            .where(
                FlightPositioningCity.monitor_id == monitor_id,
                FlightPositioningCity.enabled.is_(True),
            )
            .order_by(FlightPositioningCity.sort_no, FlightPositioningCity.id)
        )
    )


def get_positioning(db: Session, positioning_id: int) -> FlightPositioningCity:
    item = db.get(FlightPositioningCity, positioning_id)
    if not item:
        raise ValueError("Positioning city not found")
    return item


def create_positioning(db: Session, monitor_id: int, data: dict) -> FlightPositioningCity:
    monitor = get_monitor(db, monitor_id)
    data.setdefault("from_city", monitor.from_city)
    item = FlightPositioningCity(monitor_id=monitor_id, **data)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def update_positioning(db: Session, positioning_id: int, data: dict) -> FlightPositioningCity:
    item = get_positioning(db, positioning_id)
    for key, value in data.items():
        setattr(item, key, value)
    db.commit()
    db.refresh(item)
    return item


def delete_positioning(db: Session, positioning_id: int) -> int:
    item = get_positioning(db, positioning_id)
    monitor_id = item.monitor_id
    db.delete(item)
    db.commit()
    return monitor_id


def toggle_positioning(db: Session, positioning_id: int) -> int:
    item = get_positioning(db, positioning_id)
    item.enabled = not item.enabled
    monitor_id = item.monitor_id
    db.commit()
    return monitor_id


def find_positioning_for_price(db: Session, monitor_id: int, from_city: str) -> FlightPositioningCity | None:
    return db.scalar(
        select(FlightPositioningCity)
        .where(
            FlightPositioningCity.monitor_id == monitor_id,
            FlightPositioningCity.positioning_city == from_city,
            FlightPositioningCity.enabled.is_(True),
        )
        .order_by(FlightPositioningCity.sort_no, FlightPositioningCity.id)
    )
