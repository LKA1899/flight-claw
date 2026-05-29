import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    COMPLETENESS_OUTBOUND_WITH_STARTING_PRICE,
    QUERY_DIRECT,
    QUERY_HIDDEN_CITY,
    QUERY_TRAIN_PLUS_FLIGHT,
    QUERY_TRANSFER,
    RETURN_DETAIL_EXPAND_FAILED,
    RETURN_DETAIL_EXPANDED,
    RETURN_DETAIL_EXPANDING,
    RETURN_DETAIL_NOT_EXPANDED,
    RISK_HIGH,
    RISK_LOW,
    RISK_MEDIUM,
    TRIP_ONE_WAY,
    TRIP_ROUND_TRIP,
)
from app.db import SessionLocal
from app.models import FlightMonitor, FlightPlanResult, FlightPositioningCity, FlightPriceRaw, FlightRoundTripOutbound
from app.services.positioning_service import find_positioning_for_price

HIDDEN_CITY_WARNING = (
    "高风险甩尾方案：不适合托运行李；不适合买往返票；航变风险高；"
    "可能违反航司运输条款。默认不推荐，仅作为激进省钱参考。"
)
POSITIONING_BUFFER_MINUTES = 180


@dataclass
class PlanCandidate:
    batch_no: str
    monitor: FlightMonitor
    price: FlightPriceRaw
    plan_type: str
    risk_level: str
    total_price: float
    total_duration_minutes: int | None
    transfer_count: int
    warning: str | None
    reason: str
    positioning: FlightPositioningCity | None = None
    trip_type: str = TRIP_ONE_WAY
    return_date: date | None = None


def calculate_score(candidate: PlanCandidate) -> float:
    monitor = candidate.monitor
    duration = candidate.total_duration_minutes or 0

    score = 100.0
    score -= candidate.total_price / 100
    score -= (duration / 60) * 2
    score -= candidate.transfer_count * 8

    if candidate.plan_type == QUERY_TRAIN_PLUS_FLIGHT:
        score -= 6
    if candidate.plan_type == QUERY_HIDDEN_CITY:
        score -= 25
    if candidate.risk_level == RISK_MEDIUM:
        score -= 10
    if candidate.risk_level == RISK_HIGH:
        score -= 25
    if candidate.warning:
        score -= 5

    if candidate.plan_type == QUERY_DIRECT:
        score += 8
    if candidate.risk_level == RISK_LOW:
        score += 5
    if monitor.max_price and candidate.total_price < monitor.max_price:
        score += 5

    return round(score, 2)


def _plan_type_for_price(price: FlightPriceRaw) -> str | None:
    transfer_count = price.transfer_count or 0
    if price.query_type == QUERY_DIRECT and transfer_count == 0:
        return QUERY_DIRECT
    if price.query_type == QUERY_TRANSFER or transfer_count > 0:
        return QUERY_TRANSFER
    if price.query_type == QUERY_TRAIN_PLUS_FLIGHT:
        return QUERY_TRAIN_PLUS_FLIGHT
    if price.query_type == QUERY_HIDDEN_CITY:
        return QUERY_HIDDEN_CITY
    return None


def _risk_for_plan(plan_type: str, price: FlightPriceRaw) -> str:
    if plan_type == QUERY_HIDDEN_CITY:
        return RISK_HIGH
    if plan_type == QUERY_TRAIN_PLUS_FLIGHT:
        return RISK_MEDIUM
    if plan_type == QUERY_TRANSFER or (price.transfer_count or 0) > 0:
        return RISK_MEDIUM
    return RISK_LOW


def _reason(candidate: PlanCandidate) -> str:
    price = candidate.price
    parts = [f"总价 {price.currency} {candidate.total_price:.0f}", f"机票价 {price.currency} {price.price:.0f}"]
    if price.flight_no:
        parts.append(f"航班 {price.flight_no}")
    if price.depart_time:
        parts.append(f"起飞 {price.depart_time}")
    if candidate.total_duration_minutes:
        parts.append(f"总耗时约 {candidate.total_duration_minutes} 分钟")
    if candidate.transfer_count:
        parts.append(f"中转 {candidate.transfer_count} 次")
    if candidate.plan_type == QUERY_TRANSFER:
        if price.transfer_city:
            parts.append(f"配置中转城市 {price.transfer_city}")
        else:
            parts.append("未指定中转城市，由携程结果返回中转方案")
    if candidate.positioning:
        p = candidate.positioning
        parts.extend(
            [
                f"包含从 {p.from_city} 到 {p.positioning_city} 的 {p.positioning_type} 接驳",
                f"接驳成本预估 {price.currency} {p.estimated_cost:.0f}",
                f"接驳耗时预估 {p.estimated_minutes} 分钟",
                f"换乘缓冲 {POSITIONING_BUFFER_MINUTES} 分钟",
                "需要自行确认火车票/接驳票和机场交通",
            ]
        )
    parts.append(f"风险 {candidate.risk_level}")
    return "；".join(parts)


def _title(candidate: PlanCandidate) -> str:
    price = candidate.price
    flight = price.flight_no or "未知航班"
    arrow = " ↔ " if candidate.trip_type == TRIP_ROUND_TRIP else " → "
    if candidate.positioning:
        route = f"{candidate.positioning.from_city} → {candidate.positioning.positioning_city} → {price.to_city}"
    else:
        route = f"{price.from_city}{arrow}{price.to_city}"
    return f"{candidate.plan_type} · {route} · {flight} · {price.currency} {candidate.total_price:.0f}"


def _hash_key(price: FlightPriceRaw, plan_type: str) -> str:
    raw = "|".join([price.batch_no, str(price.monitor_id), str(price.depart_date), plan_type, str(price.id)])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _detail_json(candidate: PlanCandidate) -> str:
    price = candidate.price
    positioning = candidate.positioning
    return json.dumps(
        {
            "price_id": price.id,
            "task_id": price.task_id,
            "airline": price.airline,
            "flight_no": price.flight_no,
            "flight_price": price.price,
            "depart_time": price.depart_time,
            "arrive_time": price.arrive_time,
            "depart_airport": price.depart_airport,
            "arrive_airport": price.arrive_airport,
            "cabin_info": price.cabin_info,
            "baggage_info": price.baggage_info,
            "transfer_city": price.transfer_city,
            "transfer_count": price.transfer_count,
            "positioning": {
                "id": positioning.id,
                "from_city": positioning.from_city,
                "positioning_city": positioning.positioning_city,
                "positioning_type": positioning.positioning_type,
                "estimated_cost": positioning.estimated_cost,
                "estimated_minutes": positioning.estimated_minutes,
                "buffer_minutes": POSITIONING_BUFFER_MINUTES,
            }
            if positioning
            else None,
            "raw_text": price.raw_text,
            "trip_type": candidate.trip_type,
            "return_date": str(candidate.return_date) if candidate.return_date else None,
        },
        ensure_ascii=False,
    )


def _candidate_from_price(db: Session, price: FlightPriceRaw) -> PlanCandidate | None:
    plan_type = _plan_type_for_price(price)
    if not plan_type:
        return None
    monitor = price.task.monitor if price.task else None
    if not monitor:
        return None

    positioning = None
    total_price = price.price
    total_duration = price.duration_minutes
    warning = None
    transfer_count = price.transfer_count or 0

    if plan_type == QUERY_TRANSFER:
        transfer_count = max(1, transfer_count)

    if plan_type == QUERY_HIDDEN_CITY:
        warning = HIDDEN_CITY_WARNING
    elif plan_type == QUERY_TRAIN_PLUS_FLIGHT:
        positioning = find_positioning_for_price(db, price.monitor_id, price.from_city)
        if not positioning:
            warning = "未找到匹配的接驳城市配置，无法生成 TRAIN_PLUS_FLIGHT 方案。"
            return None
        total_price = price.price + positioning.estimated_cost
        total_duration = (price.duration_minutes or 0) + positioning.estimated_minutes + POSITIONING_BUFFER_MINUTES
        warning = (
            "火车/高铁接驳成本和耗时为用户配置的预估值；需要自行确认火车票/接驳票、余票、车站到机场交通和换乘时间。"
        )

    if monitor.max_transfer_count is not None and transfer_count > monitor.max_transfer_count:
        return None
    if monitor.max_total_hours is not None and total_duration is not None and total_duration > monitor.max_total_hours * 60:
        return None
    if monitor.max_price is not None and total_price > monitor.max_price:
        return None

    candidate = PlanCandidate(
        batch_no=price.batch_no,
        monitor=monitor,
        price=price,
        plan_type=plan_type,
        risk_level=_risk_for_plan(plan_type, price),
        total_price=total_price,
        total_duration_minutes=total_duration,
        transfer_count=transfer_count,
        warning=warning,
        reason="",
        positioning=positioning,
        trip_type=price.trip_type or TRIP_ONE_WAY,
        return_date=price.return_date,
    )
    candidate.reason = _reason(candidate)
    return candidate


def _save_plan(db: Session, candidate: PlanCandidate) -> bool:
    price = candidate.price
    unique_hash = _hash_key(price, candidate.plan_type)
    existing = db.scalar(select(FlightPlanResult).where(FlightPlanResult.unique_hash == unique_hash))
    row = existing or FlightPlanResult(
        batch_no=price.batch_no,
        monitor_id=price.monitor_id,
        depart_date=price.depart_date,
        plan_type=candidate.plan_type,
        source_task_ids=str(price.task_id),
        source_price_ids=str(price.id),
        unique_hash=unique_hash,
    )
    row.title = _title(candidate)
    row.total_price = candidate.total_price
    row.currency = price.currency
    row.total_duration_minutes = candidate.total_duration_minutes
    row.transfer_count = candidate.transfer_count
    row.risk_level = candidate.risk_level
    row.score = calculate_score(candidate)
    row.detail_json = _detail_json(candidate)
    row.reason = candidate.reason
    row.warning = candidate.warning
    row.trip_type = candidate.trip_type
    row.return_date = candidate.return_date
    if not existing:
        db.add(row)
    db.commit()
    return existing is None


def generate_plans_for_batch(batch_no: str) -> dict:
    with SessionLocal() as db:
        prices = list(
            db.scalars(
                select(FlightPriceRaw)
                .where(FlightPriceRaw.batch_no == batch_no)
                .order_by(FlightPriceRaw.monitor_id, FlightPriceRaw.depart_date, FlightPriceRaw.price.asc())
            )
        )
        generated_count = 0
        updated_count = 0
        skipped_count = 0
        groups: dict[str, int] = defaultdict(int)

        for price in prices:
            if price.trip_type == TRIP_ROUND_TRIP:
                skipped_count += 1
                continue
            candidate = _candidate_from_price(db, price)
            if not candidate:
                skipped_count += 1
                continue
            created = _save_plan(db, candidate)
            if created:
                generated_count += 1
            else:
                updated_count += 1
            groups[f"{price.monitor_id}:{price.depart_date}"] += 1

        return {
            "batch_no": batch_no,
            "source_price_count": len(prices),
            "generated_plan_count": generated_count,
            "updated_plan_count": updated_count,
            "skipped_count": skipped_count,
            "group_count": len(groups),
        }


def generate_plans_from_outbounds(batch_no: str) -> dict:
    with SessionLocal() as db:
        outbounds = list(
            db.scalars(
                select(FlightRoundTripOutbound)
                .where(
                    FlightRoundTripOutbound.batch_no == batch_no,
                    FlightRoundTripOutbound.display_total_price.is_not(None),
                    FlightRoundTripOutbound.return_detail_status != RETURN_DETAIL_EXPANDED,
                )
                .order_by(FlightRoundTripOutbound.monitor_id, FlightRoundTripOutbound.depart_date, FlightRoundTripOutbound.display_total_price.asc())
            )
        )
        generated = 0
        updated = 0
        for ob in outbounds:
            key = f"ROUNDTRIP_CLUE|{ob.batch_no}|{ob.monitor_id}|{ob.depart_date}|{ob.id}"
            unique_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
            existing = db.scalar(select(FlightPlanResult).where(FlightPlanResult.unique_hash == unique_hash))
            title = f"往返线索 · {ob.from_city} ↔ {ob.to_city} · {ob.airline or ''} {ob.flight_no or ''} · CNY {ob.display_total_price:.0f}"
            status = ob.return_detail_status
            if status == RETURN_DETAIL_EXPAND_FAILED:
                reason = f"往返起价线索，去程 {ob.airline or '未知航司'} {ob.flight_no or ''} {ob.depart_time or ''}-{ob.arrive_time or ''}，返程展开失败"
                warning = "返程展开失败，仅保留去程列表中的往返起价线索，不能作为最终购票推荐。"
            elif status == RETURN_DETAIL_EXPANDING:
                reason = f"往返起价线索，去程 {ob.airline or '未知航司'} {ob.flight_no or ''} {ob.depart_time or ''}-{ob.arrive_time or ''}，返程展开中"
                warning = "返程展开进行中，价格可能不完整。"
            else:
                reason = f"往返起价线索，去程 {ob.airline or '未知航司'} {ob.flight_no or ''} {ob.depart_time or ''}-{ob.arrive_time or ''}，返程未展开"
                warning = "轻量扫描产生的往返起价线索，未展开返程明细，价格可能不完整。"
            row = existing or FlightPlanResult(
                batch_no=ob.batch_no,
                monitor_id=ob.monitor_id,
                depart_date=ob.depart_date,
                return_date=ob.return_date,
                trip_type=TRIP_ROUND_TRIP,
                plan_type="ROUNDTRIP_CLUE",
                source_task_ids=str(ob.task_id),
                source_price_ids=str(ob.id),
                unique_hash=unique_hash,
            )
            row.title = title
            row.trip_type = TRIP_ROUND_TRIP
            row.total_price = ob.display_total_price or 0
            row.currency = ob.currency
            row.total_duration_minutes = ob.duration_minutes
            row.transfer_count = ob.transfer_count or 0
            row.risk_level = RISK_LOW
            row.score = round(max(0.0, 60.0 - (ob.display_total_price or 0) / 100 - (ob.transfer_count or 0) * 8), 2)
            row.reason = reason
            row.warning = warning
            row.detail_json = json.dumps({
                "outbound_id": ob.id,
                "airline": ob.airline,
                "flight_no": ob.flight_no,
                "depart_time": ob.depart_time,
                "arrive_time": ob.arrive_time,
                "depart_airport": ob.depart_airport,
                "arrive_airport": ob.arrive_airport,
                "data_completeness": ob.data_completeness,
                "return_detail_status": ob.return_detail_status,
            }, ensure_ascii=False)
            if not existing:
                db.add(row)
                generated += 1
            else:
                updated += 1
        db.commit()
        return {"batch_no": batch_no, "generated": generated, "updated": updated, "source_count": len(outbounds)}


def list_plans(
    db: Session,
    batch_no: str | None = None,
    monitor_id: int | None = None,
    depart_date: date | None = None,
) -> list[FlightPlanResult]:
    stmt = select(FlightPlanResult).order_by(FlightPlanResult.batch_no.desc(), FlightPlanResult.score.desc())
    if batch_no:
        stmt = stmt.where(FlightPlanResult.batch_no == batch_no)
    if monitor_id:
        stmt = stmt.where(FlightPlanResult.monitor_id == monitor_id)
    if depart_date:
        stmt = stmt.where(FlightPlanResult.depart_date == depart_date)
    return list(db.scalars(stmt))
