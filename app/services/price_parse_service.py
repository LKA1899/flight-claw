import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import PLATFORM_CTRIP, QUERY_DIRECT, QUERY_TRANSFER, STATUS_FAILED, STATUS_PARTIAL, STATUS_SUCCESS
from app.db import SessionLocal
from app.models import FlightPriceRaw, FlightQueryTask
from app.services.parser_pipeline import parse_ctrip_task_items


def _hash_key(
    task: FlightQueryTask,
    flight_no: str | None,
    depart_time: str | None,
    arrive_time: str | None,
    price: float,
) -> str:
    raw = "|".join(
        [
            str(task.id),
            flight_no or "",
            depart_time or "",
            arrive_time or "",
            str(int(price) if price == int(price) else price),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _mark_task_parse(
    db: Session,
    task: FlightQueryTask,
    status: str,
    error_message: str | None = None,
) -> None:
    task.parse_status = status
    task.parse_error_message = error_message
    task.parsed_time = datetime.now()
    db.commit()


def _parsed_query_type(item) -> str:
    return QUERY_TRANSFER if (item.transfer_count or 0) > 0 else QUERY_DIRECT


def _missing_required_fields(item) -> list[str]:
    required = {
        "depart_time": item.depart_time,
        "arrive_time": item.arrive_time,
        "depart_airport": item.depart_airport,
        "arrive_airport": item.arrive_airport,
    }
    return [name for name, value in required.items() if not value]


def parse_task_price(task_id: int) -> dict:
    with SessionLocal() as db:
        task = db.get(FlightQueryTask, task_id)
        if not task:
            raise ValueError(f"Query task not found: {task_id}")

        warnings: list[str] = []
        try:
            pipeline_result = parse_ctrip_task_items(db, task)
            warnings.extend(pipeline_result.warnings)
        except Exception as exc:
            _mark_task_parse(db, task, STATUS_FAILED, str(exc))
            return {"task_id": task_id, "parsed_count": 0, "failed_count": 1, "warnings": [str(exc)]}

        if task.platform != PLATFORM_CTRIP:
            message = f"Unsupported platform: {task.platform}"
            _mark_task_parse(db, task, STATUS_FAILED, message)
            return {"task_id": task_id, "parsed_count": 0, "failed_count": 1, "warnings": [message]}

        items = pipeline_result.items
        if not items:
            message = "No price items found"
            _mark_task_parse(db, task, STATUS_FAILED, message)
            return {"task_id": task_id, "parsed_count": 0, "failed_count": 1, "warnings": warnings + [message]}

        parsed_count = 0
        failed_count = 0
        skipped_incomplete_count = 0
        for item in items:
            if item.price is None:
                failed_count += 1
                continue
            missing_fields = _missing_required_fields(item)
            if missing_fields:
                skipped_incomplete_count += 1
                warnings.append(f"Skipped incomplete price {item.price}: missing {', '.join(missing_fields)}")
                continue
            unique_hash = _hash_key(task, item.flight_no, item.depart_time, item.arrive_time, item.price)
            existing = db.scalar(select(FlightPriceRaw).where(FlightPriceRaw.unique_hash == unique_hash))
            if existing:
                existing.query_type = _parsed_query_type(item)
                existing.transfer_count = item.transfer_count
                existing.transfer_city = item.transfer_city or task.transfer_city
                existing.source_html_path = None
                existing.source_screenshot_path = task.screenshot_path
                db.commit()
                parsed_count += 1
                warnings.append(f"Duplicate already exists: price={item.price}, flight_no={item.flight_no or '-'}")
                continue
            row = FlightPriceRaw(
                task_id=task.id,
                batch_no=task.batch_no,
                monitor_id=task.monitor_id,
                platform=task.platform,
                query_type=_parsed_query_type(item),
                depart_date=task.depart_date,
                return_date=task.return_date,
                trip_type=task.trip_type,
                from_city=task.from_city,
                to_city=task.to_city,
                airline=item.airline,
                flight_no=item.flight_no,
                depart_time=item.depart_time,
                arrive_time=item.arrive_time,
                depart_airport=item.depart_airport,
                arrive_airport=item.arrive_airport,
                duration_minutes=item.duration_minutes,
                transfer_count=item.transfer_count,
                transfer_city=item.transfer_city or task.transfer_city,
                cabin_info=item.cabin_info,
                baggage_info=item.baggage_info,
                price=item.price,
                currency=item.currency,
                source_html_path=None,
                source_screenshot_path=task.screenshot_path,
                raw_text=item.raw_text,
                raw_json=json.dumps(item.raw_json or {}, ensure_ascii=False),
                parse_status=STATUS_SUCCESS,
                error_message=None,
                unique_hash=unique_hash,
            )
            db.add(row)
            try:
                db.commit()
                parsed_count += 1
            except IntegrityError:
                db.rollback()
                warnings.append(f"Duplicate skipped: price={item.price}, flight_no={item.flight_no or '-'}")
            except Exception as exc:
                db.rollback()
                failed_count += 1
                warnings.append(f"Database write failed: {exc}")

        if parsed_count:
            status = STATUS_SUCCESS if failed_count == 0 else STATUS_PARTIAL
            error_message = None if status == STATUS_SUCCESS else "; ".join(warnings[:5])
            _mark_task_parse(db, task, status, error_message)
        else:
            message = "No new price rows inserted"
            _mark_task_parse(db, task, STATUS_FAILED, message)
            failed_count = max(failed_count, 1)
            warnings.append(message)

        return {
            "task_id": task_id,
            "parsed_count": parsed_count,
            "failed_count": failed_count,
            "skipped_incomplete_count": skipped_incomplete_count,
            "warnings": warnings,
        }


def list_task_prices(db: Session, task_id: int) -> list[FlightPriceRaw]:
    return list(
        db.scalars(
            select(FlightPriceRaw)
            .where(FlightPriceRaw.task_id == task_id)
            .order_by(FlightPriceRaw.price.asc(), FlightPriceRaw.id.desc())
        )
    )
