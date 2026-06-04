import json

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.constants import (
    COMPLETENESS_OUTBOUND_WITH_STARTING_PRICE,
    COMPLETENESS_FULL_ROUND_TRIP,
    PLATFORM_CTRIP,
    PRICE_ROUND_TRIP_STARTING,
    PRICE_ROUND_TRIP_TOTAL,
    RETURN_DETAIL_EXPAND_FAILED,
    RETURN_DETAIL_EXPANDED,
    RETURN_DETAIL_EXPANDING,
    RETURN_DETAIL_NOT_EXPANDED,
    RISK_LOW,
    RISK_MEDIUM,
)
from app.db import SessionLocal
from app.models import FlightQueryTask, FlightRoundTripOutbound, FlightRoundTripPlan, FlightRoundTripReturn
from app.parsers.ctrip_parser import parse_ctrip_text
from app.services.parser_pipeline import load_text_snapshot, parse_ctrip_task_items


def parse_roundtrip_outbounds(task_id: int) -> dict:
    with SessionLocal() as db:
        task = db.get(FlightQueryTask, task_id)
        if not task:
            raise ValueError(f"Query task not found: {task_id}")
        return parse_roundtrip_outbounds_for_task(db, task)


def parse_roundtrip_outbounds_for_task(db: Session, task: FlightQueryTask) -> dict:
    if task.platform != PLATFORM_CTRIP:
        raise ValueError(f"Unsupported platform: {task.platform}")
    if not task.return_date:
        raise ValueError("Round-trip task return_date is required")

    pipeline_result = parse_ctrip_task_items(db, task)
    items = pipeline_result.items
    db.execute(delete(FlightRoundTripOutbound).where(FlightRoundTripOutbound.task_id == task.id))
    parsed_count = 0
    for index, item in enumerate(items, start=1):
        row = FlightRoundTripOutbound(
            task_id=task.id,
            batch_no=task.batch_no,
            monitor_id=task.monitor_id,
            platform=task.platform,
            from_city=task.from_city,
            to_city=task.to_city,
            depart_date=task.depart_date,
            return_date=task.return_date,
            outbound_rank=index,
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
            display_total_price=item.price,
            currency=item.currency,
            price_type=PRICE_ROUND_TRIP_STARTING,
            price_display_text=f"{item.currency} {int(item.price) if item.price == int(item.price) else item.price}" if item.price is not None else None,
            return_detail_status=RETURN_DETAIL_NOT_EXPANDED,
            data_completeness=COMPLETENESS_OUTBOUND_WITH_STARTING_PRICE,
            is_complete_plan=False,
            source_html_path=None,
            source_screenshot_path=task.screenshot_path,
            raw_text=item.raw_text,
            raw_json=json.dumps(item.raw_json or {}, ensure_ascii=False),
        )
        db.add(row)
        parsed_count += 1
    db.commit()
    return {"task_id": task.id, "parsed_count": parsed_count}


def list_outbounds_for_task(db: Session, task_id: int) -> list[FlightRoundTripOutbound]:
    return list(
        db.scalars(
            select(FlightRoundTripOutbound)
            .where(FlightRoundTripOutbound.task_id == task_id)
            .order_by(FlightRoundTripOutbound.outbound_rank.asc(), FlightRoundTripOutbound.id.asc())
        )
    )


def selected_outbounds_for_expansion(db: Session, task: FlightQueryTask, strategy: dict) -> list[FlightRoundTripOutbound]:
    mode = strategy.get("roundtrip_outbound_expand_mode") or "NONE"
    outbounds = list(
        db.scalars(
            select(FlightRoundTripOutbound)
            .where(FlightRoundTripOutbound.task_id == task.id)
            .order_by(FlightRoundTripOutbound.display_total_price.asc(), FlightRoundTripOutbound.outbound_rank.asc())
        )
    )
    if strategy.get("roundtrip_expand_only_priced", True):
        outbounds = [item for item in outbounds if item.display_total_price is not None]
    if strategy.get("roundtrip_skip_expand_over_budget") and task.monitor and task.monitor.max_price:
        outbounds = [item for item in outbounds if item.display_total_price is None or item.display_total_price <= task.monitor.max_price]
    if mode == "LOWEST_TOP_N":
        return outbounds[: int(strategy.get("roundtrip_expand_top_n") or 3)]
    if mode == "SPECIFIC_RANKS":
        ranks = _parse_ranks(strategy.get("roundtrip_expand_ranks"))
        return [item for index, item in enumerate(outbounds, start=1) if index in ranks]
    if mode == "ALL":
        return outbounds
    return []


def _parse_ranks(value: str | None) -> set[int]:
    ranks: set[int] = set()
    for part in (value or "").split(","):
        try:
            ranks.add(int(part.strip()))
        except ValueError:
            continue
    return ranks


def mark_outbound_status(db: Session, outbound_id: int, status: str) -> None:
    outbound = db.get(FlightRoundTripOutbound, outbound_id)
    if outbound:
        outbound.return_detail_status = status
        db.commit()


def parse_roundtrip_returns_for_outbound(
    db: Session,
    task: FlightQueryTask,
    outbound: FlightRoundTripOutbound,
    text_path: str,
    screenshot_path: str | None,
    fetch_limit: int,
) -> dict:
    visible_text = load_text_snapshot(text_path)
    items = parse_ctrip_text(visible_text)[:fetch_limit]
    db.execute(delete(FlightRoundTripPlan).where(FlightRoundTripPlan.outbound_id == outbound.id))
    db.execute(delete(FlightRoundTripReturn).where(FlightRoundTripReturn.outbound_id == outbound.id))
    return_count = 0
    plan_count = 0
    for index, item in enumerate(items, start=1):
        row = FlightRoundTripReturn(
            task_id=task.id,
            batch_no=task.batch_no,
            monitor_id=task.monitor_id,
            outbound_id=outbound.id,
            from_city=task.to_city,
            to_city=task.from_city,
            depart_date=task.depart_date,
            return_date=task.return_date,
            return_rank=index,
            airline=item.airline,
            flight_no=item.flight_no,
            depart_time=item.depart_time,
            arrive_time=item.arrive_time,
            depart_airport=item.depart_airport,
            arrive_airport=item.arrive_airport,
            duration_minutes=item.duration_minutes,
            transfer_count=item.transfer_count,
            transfer_city=item.transfer_city,
            cabin_info=item.cabin_info,
            baggage_info=item.baggage_info,
            total_price=item.price,
            price_delta=None,
            currency=item.currency,
            price_type=PRICE_ROUND_TRIP_TOTAL,
            price_display_text=f"{item.currency} {int(item.price) if item.price == int(item.price) else item.price}" if item.price is not None else None,
            source_html_path=None,
            source_screenshot_path=screenshot_path,
            raw_text=item.raw_text,
            raw_json=json.dumps(item.raw_json or {}, ensure_ascii=False),
        )
        db.add(row)
        db.flush()
        return_count += 1
        if item.price is not None:
            db.add(_plan_from_return(task, outbound, row))
            plan_count += 1
    outbound.return_detail_status = RETURN_DETAIL_EXPANDED if return_count else RETURN_DETAIL_EXPAND_FAILED
    db.commit()
    return {"return_count": return_count, "plan_count": plan_count}


def _plan_from_return(task: FlightQueryTask, outbound: FlightRoundTripOutbound, return_row: FlightRoundTripReturn) -> FlightRoundTripPlan:
    total_duration = (outbound.duration_minutes or 0) + (return_row.duration_minutes or 0) or None
    total_transfer = (outbound.transfer_count or 0) + (return_row.transfer_count or 0)
    outbound_summary = f"{outbound.airline or ''} {outbound.flight_no or ''} {outbound.depart_time or ''}-{outbound.arrive_time or ''}".strip()
    return_summary = f"{return_row.airline or ''} {return_row.flight_no or ''} {return_row.depart_time or ''}-{return_row.arrive_time or ''}".strip()
    score = max(0.0, 1000.0 - float(return_row.total_price or 0) / 10 - total_transfer * 25 - (total_duration or 0) / 60)
    return FlightRoundTripPlan(
        task_id=task.id,
        batch_no=task.batch_no,
        monitor_id=task.monitor_id,
        outbound_id=outbound.id,
        return_id=return_row.id,
        depart_date=task.depart_date,
        return_date=task.return_date,
        total_price=return_row.total_price or 0,
        currency=return_row.currency,
        total_duration_minutes=total_duration,
        total_transfer_count=total_transfer,
        outbound_summary=outbound_summary,
        return_summary=return_summary,
        risk_level=RISK_LOW if total_transfer <= 1 else RISK_MEDIUM,
        score=round(score, 2),
        reason="完整往返组合，价格来自已选去程后的返程列表。",
        warning=None,
        data_completeness=COMPLETENESS_FULL_ROUND_TRIP,
        is_complete_plan=True,
    )


RETURN_EXPANDING = RETURN_DETAIL_EXPANDING
RETURN_EXPAND_FAILED = RETURN_DETAIL_EXPAND_FAILED
