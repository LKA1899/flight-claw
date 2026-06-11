from collections import defaultdict
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.constants import QUERY_DIRECT, QUERY_HIDDEN_CITY, RISK_HIGH, RISK_LOW, RISK_MEDIUM, TRIP_ROUND_TRIP
from app.db import SessionLocal
from app.models import FlightBestDaily, FlightPlanResult
from app.services.flight_identity_service import dedupe_plan_results

RISK_RANK = {RISK_LOW: 0, RISK_MEDIUM: 1, RISK_HIGH: 2}


def _trend(best_price: float | None, prev_price: float | None) -> int:
    if best_price is None or prev_price is None:
        return 0
    if best_price < prev_price:
        return -1
    if best_price > prev_price:
        return 1
    return 0


def _previous_best_price(db: Session, plan: FlightPlanResult) -> float | None:
    previous = db.scalar(
        select(FlightBestDaily)
        .where(
            FlightBestDaily.monitor_id == plan.monitor_id,
            FlightBestDaily.depart_date == plan.depart_date,
            FlightBestDaily.batch_no != plan.batch_no,
        )
        .order_by(FlightBestDaily.create_time.desc())
    )
    return previous.best_price if previous else None


def _safest_key(plan: FlightPlanResult) -> tuple[int, int, float, float]:
    direct_priority = 0 if plan.plan_type == QUERY_DIRECT else 1
    return (RISK_RANK.get(plan.risk_level, 9), direct_priority, plan.transfer_count, plan.total_price)


def _summary(best: FlightPlanResult, cheapest: FlightPlanResult, safest: FlightPlanResult, aggressive: FlightPlanResult | None) -> str:
    parts = [
        f"综合最优为 {best.title}，评分 {best.score:.1f}，价格 {best.currency} {best.total_price:.0f}。",
        f"最低价为 {cheapest.title}，价格 {cheapest.currency} {cheapest.total_price:.0f}。",
        f"最稳妥方案为 {safest.title}，风险 {safest.risk_level}。",
    ]
    if aggressive:
        parts.append(f"激进省钱方案为 {aggressive.title}，但风险高，不作为默认推荐。")
    return " ".join(parts)


def analyze_best_daily(batch_no: str) -> dict:
    with SessionLocal() as db:
        db.execute(delete(FlightBestDaily).where(FlightBestDaily.batch_no == batch_no))
        db.commit()
        plans = list(
            db.scalars(
                select(FlightPlanResult)
                .where(
                    FlightPlanResult.batch_no == batch_no,
                    FlightPlanResult.plan_type != "ROUNDTRIP_CLUE",
                )
                .order_by(FlightPlanResult.monitor_id, FlightPlanResult.depart_date, FlightPlanResult.score.desc())
            )
        )
        plans = dedupe_plan_results(plans)
        grouped: dict[tuple[int, date], list[FlightPlanResult]] = defaultdict(list)
        for plan in plans:
            grouped[(plan.monitor_id, plan.depart_date)].append(plan)

        saved_count = 0
        for (_monitor_id, _depart_date), group in grouped.items():
            cheapest = min(group, key=lambda item: item.total_price)
            safest = min(group, key=_safest_key)
            aggressive_candidates = [item for item in group if item.plan_type == QUERY_HIDDEN_CITY or item.risk_level == RISK_HIGH]
            aggressive = min(aggressive_candidates, key=lambda item: item.total_price) if aggressive_candidates else None
            best_candidates = [item for item in group if item.plan_type != QUERY_HIDDEN_CITY]
            best = max(best_candidates or group, key=lambda item: item.score)
            prev_price = _previous_best_price(db, best)
            row = FlightBestDaily(
                batch_no=batch_no,
                monitor_id=best.monitor_id,
                depart_date=best.depart_date,
            )
            row.best_plan_id = best.id
            row.cheapest_plan_id = cheapest.id
            row.safest_plan_id = safest.id
            row.aggressive_plan_id = aggressive.id if aggressive else None
            row.best_price = best.total_price
            row.prev_best_price = prev_price
            row.price_trend = _trend(best.total_price, prev_price)
            row.summary = _summary(best, cheapest, safest, aggressive)
            db.add(row)
            try:
                db.commit()
                saved_count += 1
            except IntegrityError:
                db.rollback()

        return {
            "batch_no": batch_no,
            "source_plan_count": len(plans),
            "best_daily_count": saved_count,
        }


def list_best_daily(db: Session, batch_no: str | None = None) -> list[FlightBestDaily]:
    stmt = select(FlightBestDaily).order_by(FlightBestDaily.batch_no.desc(), FlightBestDaily.depart_date.asc())
    if batch_no:
        stmt = stmt.where(FlightBestDaily.batch_no == batch_no)
    return list(db.scalars(stmt))
