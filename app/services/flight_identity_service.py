import json
from datetime import date
from typing import Any

from app.models import FlightPlanResult, FlightPriceRaw


def _norm(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip().lower()


def _detail(plan: FlightPlanResult) -> dict[str, Any]:
    if not plan.detail_json:
        return {}
    try:
        value = json.loads(plan.detail_json)
    except (TypeError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def price_flight_identity_key(item: FlightPriceRaw) -> tuple[str, ...]:
    return (
        _norm(item.monitor_id),
        _norm(item.trip_type),
        _norm(item.leg_type),
        _norm(item.query_type),
        _norm(item.depart_date),
        _norm(item.return_date),
        _norm(item.from_city),
        _norm(item.to_city),
        _norm(item.flight_no),
        _norm(item.depart_time),
        _norm(item.arrive_time),
        _norm(item.depart_airport),
        _norm(item.arrive_airport),
        _norm(item.transfer_count),
        _norm(item.transfer_city),
    )


def plan_flight_identity_key(item: FlightPlanResult) -> tuple[str, ...]:
    detail = _detail(item)
    source_type = (
        "ROUNDTRIP_CLUE"
        if item.plan_type == "ROUNDTRIP_CLUE"
        else "ROUNDTRIP_PLAN"
        if item.plan_type == "ROUNDTRIP_TICKET"
        else "ONE_WAY_PLAN"
    )
    if source_type == "ROUNDTRIP_PLAN":
        return (
            _norm(item.monitor_id),
            _norm(source_type),
            _norm(item.depart_date),
            _norm(item.return_date),
            _norm(detail.get("outbound_flight_no")),
            _norm(detail.get("outbound_depart_time")),
            _norm(detail.get("outbound_arrive_time")),
            _norm(detail.get("outbound_depart_airport")),
            _norm(detail.get("outbound_arrive_airport")),
            _norm(detail.get("return_flight_no")),
            _norm(detail.get("return_depart_time")),
            _norm(detail.get("return_arrive_time")),
            _norm(detail.get("return_depart_airport")),
            _norm(detail.get("return_arrive_airport")),
        )
    if source_type == "ROUNDTRIP_CLUE":
        return (
            _norm(item.monitor_id),
            _norm(source_type),
            _norm(item.depart_date),
            _norm(item.return_date),
            _norm(detail.get("flight_no")),
            _norm(detail.get("depart_time")),
            _norm(detail.get("arrive_time")),
            _norm(detail.get("depart_airport")),
            _norm(detail.get("arrive_airport")),
        )
    return (
        _norm(item.monitor_id),
        _norm(source_type),
        _norm(item.depart_date),
        _norm(item.return_date),
        _norm(detail.get("flight_no")),
        _norm(detail.get("depart_time")),
        _norm(detail.get("arrive_time")),
        _norm(detail.get("depart_airport")),
        _norm(detail.get("arrive_airport")),
        _norm(detail.get("transfer_count")),
        _norm(detail.get("transfer_city")),
    )


def plan_dict_flight_identity_key(item: dict[str, Any]) -> tuple[str, ...]:
    source_type = item.get("source_type") or "ONE_WAY_PLAN"
    if source_type == "ROUNDTRIP_PLAN":
        return (
            _norm(item.get("monitor_id")),
            _norm(source_type),
            _norm(item.get("depart_date")),
            _norm(item.get("return_date")),
            _norm(item.get("outbound_flight_no")),
            _norm(item.get("outbound_depart_time")),
            _norm(item.get("outbound_arrive_time")),
            _norm(item.get("outbound_depart_airport")),
            _norm(item.get("outbound_arrive_airport")),
            _norm(item.get("return_flight_no")),
            _norm(item.get("return_depart_time")),
            _norm(item.get("return_arrive_time")),
            _norm(item.get("return_depart_airport")),
            _norm(item.get("return_arrive_airport")),
        )
    if source_type == "ROUNDTRIP_CLUE":
        return (
            _norm(item.get("monitor_id")),
            _norm(source_type),
            _norm(item.get("depart_date")),
            _norm(item.get("return_date")),
            _norm(item.get("outbound_flight_no")),
            _norm(item.get("outbound_depart_time")),
            _norm(item.get("outbound_arrive_time")),
            _norm(item.get("outbound_depart_airport")),
            _norm(item.get("outbound_arrive_airport")),
        )
    return (
        _norm(item.get("monitor_id")),
        _norm(source_type),
        _norm(item.get("depart_date")),
        _norm(item.get("return_date")),
        _norm(item.get("flight_no")),
        _norm(item.get("depart_time")),
        _norm(item.get("arrive_time")),
        _norm(item.get("depart_airport")),
        _norm(item.get("arrive_airport")),
    )


def dedupe_plan_results(items: list[FlightPlanResult]) -> list[FlightPlanResult]:
    selected: dict[tuple[str, ...], FlightPlanResult] = {}
    for item in items:
        key = plan_flight_identity_key(item)
        current = selected.get(key)
        if current is None or _is_better_plan(item, current):
            selected[key] = item
    return list(selected.values())


def dedupe_plan_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[tuple[str, ...], dict[str, Any]] = {}
    for item in items:
        key = plan_dict_flight_identity_key(item)
        current = selected.get(key)
        if current is None or _is_better_plan_dict(item, current):
            selected[key] = item
    return list(selected.values())


def _is_better_plan(candidate: FlightPlanResult, current: FlightPlanResult) -> bool:
    return (
        float(candidate.score or 0),
        -float(candidate.total_price or 0),
        candidate.id or 0,
    ) > (
        float(current.score or 0),
        -float(current.total_price or 0),
        current.id or 0,
    )


def _is_better_plan_dict(candidate: dict[str, Any], current: dict[str, Any]) -> bool:
    return (
        float(candidate.get("score") or 0),
        -float(candidate.get("total_price") or 0),
        int(candidate.get("id") or 0),
    ) > (
        float(current.get("score") or 0),
        -float(current.get("total_price") or 0),
        int(current.get("id") or 0),
    )
