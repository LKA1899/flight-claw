import json
import math
import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.constants import (
    ROUNDTRIP_EXPAND_ALL,
    ROUNDTRIP_EXPAND_LOWEST_TOP_N,
    ROUNDTRIP_EXPAND_NONE,
    ROUNDTRIP_EXPAND_SPECIFIC_RANKS,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_RUNNING,
    STATUS_SUCCESS,
    TRIGGER_MANUAL,
    TRIP_ONE_WAY,
    TRIP_ROUND_TRIP,
)
from app.db import DATA_DIR, get_db
from app.models import (
    FlightUser,
    FlightBestDaily,
    FlightCityCode,
    FlightMonitor,
    FlightMonitorDate,
    FlightPositioningCity,
    FlightPlanResult,
    FlightPriceRaw,
    FlightQueryBatch,
    FlightQueryTask,
    FlightRoundTripOutbound,
    FlightRoundTripPlan,
    FlightRoundTripReturn,
    FlightScan,
    FlightScanStepLog,
    FlightTransferCity,
)
from app.services import date_service, monitor_service, positioning_service, transfer_service
from app.services.price_parse_service import parse_task_price
from app.services.scan_runner import cancel_running_monitor_scan, cancel_scan, restart_scan, scan_monitor
from app.services.scan_service import scan_dict, step_log_dict
from app.services.scheduler_service import refresh_scheduler, validate_schedule_cron
from app.services.task_service import cancel_task, reset_task
from app.services.city_code_service import seed_default_city_codes, sync_ourairports_city_codes
from app.services.flight_identity_service import dedupe_plan_dicts
from app.crawler.ctrip import run_ctrip_task
from app.security.auth import require_admin

router = APIRouter(prefix="/api", tags=["api"], dependencies=[Depends(require_admin)])


class ApiError(Exception):
    pass


class MonitorPayload(BaseModel):
    monitor_name: str = Field(min_length=1, max_length=200)
    from_city: str = Field(min_length=1, max_length=80)
    from_airports: str | None = None
    to_city: str = Field(min_length=1, max_length=80)
    to_airports: str | None = None
    platform: str = Field(default="CTRIP", pattern="^CTRIP$")
    trip_type: str = Field(default=TRIP_ONE_WAY, pattern="^(ONE_WAY|ROUND_TRIP)$")
    allow_direct: bool = True
    allow_transfer: bool = False
    allow_train_positioning: bool = False
    allow_hidden_city: bool = False
    max_transfer_count: int | None = Field(default=None, ge=0, le=5)
    max_total_hours: int | None = Field(default=None, ge=1, le=72)
    max_price: float | None = Field(default=None, gt=0)
    roundtrip_data_level: str = Field(default="OUTBOUND_ONLY", pattern="^(OUTBOUND_ONLY|FULL_COMBINATION)$")
    roundtrip_expand_return: bool = False
    roundtrip_outbound_expand_mode: str = Field(
        default=ROUNDTRIP_EXPAND_NONE,
        pattern="^(NONE|LOWEST_TOP_N|SPECIFIC_RANKS|ALL)$",
    )
    roundtrip_expand_top_n: int = Field(default=3, ge=1, le=20)
    roundtrip_expand_ranks: str | None = Field(default=None, max_length=100)
    roundtrip_return_fetch_limit: int = Field(default=10, ge=1, le=50)
    roundtrip_return_sort_strategy: str = Field(default="LOW_PRICE", max_length=50)
    roundtrip_save_all_outbounds: bool = True
    roundtrip_expand_only_priced: bool = True
    roundtrip_skip_expand_over_budget: bool = False
    continue_on_expand_failed: bool = True
    save_step_snapshot: bool = True
    enabled: bool = True
    remark: str | None = None

    @field_validator(
        "monitor_name",
        "from_city",
        "to_city",
        "from_airports",
        "to_airports",
        "roundtrip_expand_ranks",
        "roundtrip_return_sort_strategy",
        "remark",
        mode="before",
    )
    @classmethod
    def trim_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value

    @model_validator(mode="after")
    def validate_query_strategy(self):
        if self.trip_type == TRIP_ONE_WAY and not (
            self.allow_direct or self.allow_transfer or self.allow_train_positioning
        ):
            raise ValueError("单程路线至少需要启用一种查询方式：直飞、中转或火车/高铁接驳")
        return self

class DatePayload(BaseModel):
    depart_date: date
    return_date: date | None = None
    remark: str | None = None

    @model_validator(mode="after")
    def validate_date_order(self):
        if self.return_date is not None and self.return_date < self.depart_date:
            raise ValueError("return_date must be greater than or equal to depart_date")
        return self


class DateBatchPayload(BaseModel):
    start_date: date
    end_date: date
    return_start_date: date | None = None
    return_end_date: date | None = None
    weekdays: list[int] = []

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(item < 1 or item > 7 for item in value):
            raise ValueError("weekdays must use ISO weekday numbers from 1 to 7")
        return value

    @model_validator(mode="after")
    def validate_return_range(self):
        has_start = self.return_start_date is not None
        has_end = self.return_end_date is not None
        if has_start != has_end:
            raise ValueError("return_start_date and return_end_date must be provided together")
        if has_start and has_end and self.return_end_date < self.return_start_date:
            raise ValueError("return_end_date must be greater than or equal to return_start_date")
        if has_start and self.return_end_date < self.start_date:
            raise ValueError("return_end_date must be greater than or equal to start_date")
        return self


class PositioningPayload(BaseModel):
    positioning_city: str = Field(min_length=1, max_length=80)
    positioning_type: str = Field(default="TRAIN", pattern="^(TRAIN|BUS|SELF)$")
    estimated_cost: float = Field(default=0, ge=0)
    estimated_minutes: int = Field(default=0, ge=0, le=1440)
    enabled: bool = True
    sort_no: int = Field(default=100, ge=0, le=10000)
    remark: str | None = None


class MonitorSchedulePayload(BaseModel):
    schedule_enabled: bool = False
    schedule_cron: str | None = Field(default=None, max_length=100)
    schedule_timezone: str = Field(default="Asia/Shanghai", max_length=100)
    schedule_remark: str | None = Field(default=None, max_length=500)

    @field_validator("schedule_cron", "schedule_timezone", "schedule_remark", mode="before")
    @classmethod
    def trim_schedule_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class TransferPayload(BaseModel):
    transfer_city: str = Field(min_length=1, max_length=80)
    transfer_airports: str | None = None
    enabled: bool = True
    sort_no: int = Field(default=100, ge=0, le=10000)
    remark: str | None = None


class CityCodePayload(BaseModel):
    platform: str = Field(default="CTRIP", pattern="^CTRIP$")
    city_name: str = Field(min_length=1, max_length=80)
    city_code: str = Field(min_length=2, max_length=20)
    aliases: str | None = Field(default=None, max_length=500)
    country: str | None = Field(default=None, max_length=80)
    enabled: bool = True
    remark: str | None = None

    @field_validator("city_name", "city_code", "aliases", "country", "remark", mode="before")
    @classmethod
    def trim_city_code_text(cls, value):
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


def ok(data: Any = None) -> dict[str, Any]:
    return {"success": True, "data": data}


def dt(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return str(value)


def duration(start: datetime | None, end: datetime | None) -> int | None:
    if not start or not end:
        return None
    return int((end - start).total_seconds())


def pages(total: int, page_size: int) -> int:
    return max(1, math.ceil(total / page_size)) if total else 0


def page_result(items: list[Any], total: int, page: int, page_size: int) -> dict[str, Any]:
    return {"items": items, "total": total, "page": page, "page_size": page_size, "pages": pages(total, page_size)}


def paginate(db: Session, stmt, page: int, page_size: int) -> tuple[list[Any], int]:
    page = max(1, page)
    page_size = min(max(1, page_size), 100)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(db.scalars(stmt.offset((page - 1) * page_size).limit(page_size)))
    return rows, total


def parse_date(value: str | None) -> date | None:
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


def resolve_batch_no(db: Session, value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    scan = db.scalar(select(FlightScan).where(FlightScan.scan_no == normalized))
    return scan.batch_no if scan and scan.batch_no else normalized


def prioritize_plan_dicts(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped = dedupe_plan_dicts(items)
    deduped.sort(key=lambda item: (float(item.get("total_price") or 0), -float(item.get("score") or 0)))
    return deduped


def scan_option_dict(item: FlightScan) -> dict[str, Any]:
    started_at = item.start_time or item.create_time
    scan_time = started_at.strftime("%Y-%m-%d %H:%M") if started_at else "-"
    trigger_label = {
        "MANUAL": "手动",
        "SCHEDULED": "定时",
        "SCAN": "扫描",
    }.get(item.trigger_type, item.trigger_type)
    status_label = {
        "SUCCESS": "成功",
        "FAILED": "失败",
        "RUNNING": "运行中",
        "PARTIAL_SUCCESS": "部分成功",
        "CANCELLED": "已取消",
        "QUEUED": "排队中",
    }.get(item.status, item.status)
    monitor_name = item.monitor.monitor_name if item.monitor else None
    from_city = item.monitor.from_city if item.monitor else None
    to_city = item.monitor.to_city if item.monitor else None
    route_text = " -> ".join(part for part in [from_city, to_city] if part)
    route_label = " / ".join(part for part in [monitor_name, route_text] if part) or "未关联路线"
    task_summary = f"{item.success_task_count}/{item.total_task_count}"
    return {
        "scan_id": item.id,
        "scan_no": item.scan_no,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "monitor_name": monitor_name,
        "from_city": from_city,
        "to_city": to_city,
        "route_label": route_label,
        "label": f"{scan_time} · {trigger_label} · {status_label} · {task_summary}",
        "start_time": dt(item.start_time),
        "create_time": dt(item.create_time),
        "trigger_type": item.trigger_type,
        "status": item.status,
        "total_task_count": item.total_task_count,
        "success_task_count": item.success_task_count,
        "failed_task_count": item.failed_task_count,
    }


def monitor_dict(monitor: FlightMonitor, date_count: int | None = None, enabled_date_count: int | None = None) -> dict[str, Any]:
    if date_count is None:
        date_count = len(monitor.dates or [])
    if enabled_date_count is None:
        enabled_date_count = len([item for item in monitor.dates or [] if item.enabled])
    return {
        "id": monitor.id,
        "monitor_name": monitor.monitor_name,
        "from_city": monitor.from_city,
        "from_airports": monitor.from_airports,
        "to_city": monitor.to_city,
        "to_airports": monitor.to_airports,
        "platform": monitor.platform,
        "trip_type": monitor.trip_type,
        "allow_direct": monitor.allow_direct,
        "allow_transfer": monitor.allow_transfer,
        "allow_train_positioning": monitor.allow_train_positioning,
        "allow_hidden_city": monitor.allow_hidden_city,
        "max_transfer_count": monitor.max_transfer_count,
        "max_total_hours": monitor.max_total_hours,
        "max_price": monitor.max_price,
        "roundtrip_data_level": monitor.roundtrip_data_level,
        "roundtrip_expand_return": monitor.roundtrip_expand_return,
        "roundtrip_outbound_expand_mode": monitor.roundtrip_outbound_expand_mode,
        "roundtrip_expand_top_n": monitor.roundtrip_expand_top_n,
        "roundtrip_expand_ranks": monitor.roundtrip_expand_ranks,
        "roundtrip_return_fetch_limit": monitor.roundtrip_return_fetch_limit,
        "roundtrip_return_sort_strategy": monitor.roundtrip_return_sort_strategy,
        "roundtrip_save_all_outbounds": monitor.roundtrip_save_all_outbounds,
        "roundtrip_expand_only_priced": monitor.roundtrip_expand_only_priced,
        "roundtrip_skip_expand_over_budget": monitor.roundtrip_skip_expand_over_budget,
        "continue_on_expand_failed": monitor.continue_on_expand_failed,
        "save_step_snapshot": monitor.save_step_snapshot,
        "schedule_enabled": monitor.schedule_enabled,
        "schedule_cron": monitor.schedule_cron,
        "schedule_timezone": monitor.schedule_timezone,
        "schedule_remark": monitor.schedule_remark,
        "last_scan_id": monitor.last_scan_id,
        "last_scan_time": dt(monitor.last_scan_time),
        "last_scan_status": monitor.last_scan_status,
        "next_scan_time": dt(monitor.next_scan_time),
        "enabled": monitor.enabled,
        "remark": monitor.remark,
        "date_count": date_count,
        "enabled_date_count": enabled_date_count,
        "create_time": dt(monitor.create_time),
        "update_time": dt(monitor.update_time),
    }


def file_response(path_value: str | None, not_found_message: str) -> FileResponse:
    if not path_value:
        raise HTTPException(status_code=404, detail=not_found_message)
    path = Path(path_value).resolve()
    data_root = DATA_DIR.resolve()
    if data_root not in path.parents:
        raise HTTPException(status_code=403, detail="File path is outside the data directory")
    if not path.exists():
        raise HTTPException(status_code=404, detail=not_found_message)
    return FileResponse(path)


def positioning_dict(item: FlightPositioningCity) -> dict[str, Any]:
    return {
        "id": item.id,
        "monitor_id": item.monitor_id,
        "from_city": item.from_city,
        "positioning_city": item.positioning_city,
        "positioning_type": item.positioning_type,
        "estimated_cost": item.estimated_cost,
        "estimated_minutes": item.estimated_minutes,
        "enabled": item.enabled,
        "sort_no": item.sort_no,
        "remark": item.remark,
        "create_time": dt(item.create_time),
        "update_time": dt(item.update_time),
    }


def transfer_dict(item: FlightTransferCity) -> dict[str, Any]:
    return {
        "id": item.id,
        "monitor_id": item.monitor_id,
        "transfer_city": item.transfer_city,
        "transfer_airports": item.transfer_airports,
        "enabled": item.enabled,
        "sort_no": item.sort_no,
        "remark": item.remark,
        "create_time": dt(item.create_time),
        "update_time": dt(item.update_time),
    }


def city_code_dict(item: FlightCityCode) -> dict[str, Any]:
    return {
        "id": item.id,
        "platform": item.platform,
        "city_name": item.city_name,
        "city_code": item.city_code,
        "aliases": item.aliases,
        "country": item.country,
        "enabled": item.enabled,
        "remark": item.remark,
        "create_time": dt(item.create_time),
        "update_time": dt(item.update_time),
    }


def batch_dict(item: FlightQueryBatch) -> dict[str, Any]:
    return {
        "id": item.id,
        "scan_id": item.scan_id,
        "batch_no": item.batch_no,
        "trigger_type": item.trigger_type,
        "status": item.status,
        "total_task_count": item.total_task_count,
        "success_task_count": item.success_task_count,
        "failed_task_count": item.failed_task_count,
        "start_time": dt(item.start_time),
        "end_time": dt(item.end_time),
        "duration_seconds": duration(item.start_time, item.end_time),
        "error_message": item.error_message,
        "create_time": dt(item.create_time),
    }


def task_dict(item: FlightQueryTask) -> dict[str, Any]:
    return {
        "id": item.id,
        "scan_id": item.scan_id,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "monitor_name": item.monitor.monitor_name if item.monitor else None,
        "depart_date": dt(item.depart_date),
        "return_date": dt(item.return_date),
        "trip_type": item.trip_type,
        "query_type": item.query_type,
        "platform": item.platform,
        "from_city": item.from_city,
        "to_city": item.to_city,
        "transfer_city": item.transfer_city,
        "status": item.status,
        "error_message": item.error_message,
        "screenshot_path": item.screenshot_path,
        "html_path": None,
        "text_path": item.text_path,
        "parse_status": item.parse_status,
        "parse_error_message": item.parse_error_message,
        "parsed_time": dt(item.parsed_time),
        "strategy_snapshot_json": item.strategy_snapshot_json,
        "data_completeness": item.data_completeness,
        "roundtrip_stage": item.roundtrip_stage,
        "start_time": dt(item.start_time),
        "end_time": dt(item.end_time),
        "create_time": dt(item.create_time),
    }


def price_dict(item: FlightPriceRaw, price_change: dict[str, Any] | None = None) -> dict[str, Any]:
    result = {
        "id": item.id,
        "task_id": item.task_id,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "platform": item.platform,
        "trip_type": item.trip_type,
        "leg_type": item.leg_type,
        "query_type": item.query_type,
        "depart_date": dt(item.depart_date),
        "return_date": dt(item.return_date),
        "from_city": item.from_city,
        "to_city": item.to_city,
        "airline": item.airline,
        "flight_no": item.flight_no,
        "depart_time": item.depart_time,
        "arrive_time": item.arrive_time,
        "depart_airport": item.depart_airport,
        "arrive_airport": item.arrive_airport,
        "duration_minutes": item.duration_minutes,
        "transfer_count": item.transfer_count,
        "transfer_city": item.transfer_city,
        "cabin_info": item.cabin_info,
        "baggage_info": item.baggage_info,
        "price": item.price,
        "price_type": item.price_type,
        "data_completeness": item.data_completeness,
        "is_complete_plan": item.is_complete_plan,
        "currency": item.currency,
        "source_html_path": None,
        "source_screenshot_path": item.source_screenshot_path,
        "parse_status": item.parse_status,
        "error_message": item.error_message,
        "create_time": dt(item.create_time),
    }
    if price_change:
        result.update(price_change)
    return result


def price_change_dict(db: Session, item: FlightPriceRaw) -> dict[str, Any]:
    previous = db.scalar(
        select(FlightPriceRaw)
        .where(
            FlightPriceRaw.id != item.id,
            FlightPriceRaw.monitor_id == item.monitor_id,
            FlightPriceRaw.platform == item.platform,
            FlightPriceRaw.trip_type == item.trip_type,
            FlightPriceRaw.leg_type == item.leg_type,
            FlightPriceRaw.query_type == item.query_type,
            FlightPriceRaw.depart_date == item.depart_date,
            FlightPriceRaw.return_date == item.return_date,
            FlightPriceRaw.from_city == item.from_city,
            FlightPriceRaw.to_city == item.to_city,
            FlightPriceRaw.flight_no == item.flight_no,
            FlightPriceRaw.depart_time == item.depart_time,
            FlightPriceRaw.arrive_time == item.arrive_time,
            FlightPriceRaw.depart_airport == item.depart_airport,
            FlightPriceRaw.arrive_airport == item.arrive_airport,
            FlightPriceRaw.transfer_count == item.transfer_count,
            FlightPriceRaw.transfer_city == item.transfer_city,
            or_(
                FlightPriceRaw.create_time < item.create_time,
                and_(FlightPriceRaw.create_time == item.create_time, FlightPriceRaw.id < item.id),
            ),
        )
        .order_by(FlightPriceRaw.create_time.desc(), FlightPriceRaw.id.desc())
    )
    if not previous:
        return {
            "previous_price": None,
            "price_delta": None,
            "price_trend": 0,
            "previous_price_time": None,
        }
    delta = item.price - previous.price
    trend = -1 if delta < 0 else 1 if delta > 0 else 0
    return {
        "previous_price": previous.price,
        "price_delta": round(delta, 2),
        "price_trend": trend,
        "previous_price_time": dt(previous.create_time),
    }


def roundtrip_outbound_dict(item: FlightRoundTripOutbound) -> dict[str, Any]:
    return {
        "id": item.id,
        "task_id": item.task_id,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "monitor_name": item.monitor.monitor_name if item.monitor else None,
        "platform": item.platform,
        "from_city": item.from_city,
        "to_city": item.to_city,
        "depart_date": dt(item.depart_date),
        "return_date": dt(item.return_date),
        "outbound_rank": item.outbound_rank,
        "airline": item.airline,
        "flight_no": item.flight_no,
        "depart_time": item.depart_time,
        "arrive_time": item.arrive_time,
        "depart_airport": item.depart_airport,
        "arrive_airport": item.arrive_airport,
        "duration_minutes": item.duration_minutes,
        "transfer_count": item.transfer_count,
        "transfer_city": item.transfer_city,
        "cabin_info": item.cabin_info,
        "baggage_info": item.baggage_info,
        "display_total_price": item.display_total_price,
        "currency": item.currency,
        "price_type": item.price_type,
        "price_display_text": item.price_display_text,
        "return_detail_status": item.return_detail_status,
        "data_completeness": item.data_completeness,
        "is_complete_plan": item.is_complete_plan,
        "source_html_path": None,
        "source_screenshot_path": item.source_screenshot_path,
        "raw_text": item.raw_text,
        "raw_json": item.raw_json,
        "create_time": dt(item.create_time),
    }


def roundtrip_return_dict(item: FlightRoundTripReturn) -> dict[str, Any]:
    return {
        "id": item.id,
        "task_id": item.task_id,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "outbound_id": item.outbound_id,
        "from_city": item.from_city,
        "to_city": item.to_city,
        "depart_date": dt(item.depart_date),
        "return_date": dt(item.return_date),
        "return_rank": item.return_rank,
        "airline": item.airline,
        "flight_no": item.flight_no,
        "depart_time": item.depart_time,
        "arrive_time": item.arrive_time,
        "depart_airport": item.depart_airport,
        "arrive_airport": item.arrive_airport,
        "duration_minutes": item.duration_minutes,
        "transfer_count": item.transfer_count,
        "transfer_city": item.transfer_city,
        "cabin_info": item.cabin_info,
        "baggage_info": item.baggage_info,
        "total_price": item.total_price,
        "price_delta": item.price_delta,
        "currency": item.currency,
        "price_type": item.price_type,
        "price_display_text": item.price_display_text,
        "source_html_path": None,
        "source_screenshot_path": item.source_screenshot_path,
        "raw_text": item.raw_text,
        "raw_json": item.raw_json,
        "create_time": dt(item.create_time),
    }


def roundtrip_plan_dict(item: FlightRoundTripPlan) -> dict[str, Any]:
    return {
        "id": item.id,
        "task_id": item.task_id,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "monitor_name": item.monitor.monitor_name if item.monitor else None,
        "outbound_id": item.outbound_id,
        "return_id": item.return_id,
        "depart_date": dt(item.depart_date),
        "return_date": dt(item.return_date),
        "leg_type": item.leg_type,
        "price_type": item.price_type,
        "total_price": item.total_price,
        "currency": item.currency,
        "total_duration_minutes": item.total_duration_minutes,
        "total_transfer_count": item.total_transfer_count,
        "outbound_summary": item.outbound_summary,
        "return_summary": item.return_summary,
        "risk_level": item.risk_level,
        "score": item.score,
        "reason": item.reason,
        "warning": item.warning,
        "data_completeness": item.data_completeness,
        "is_complete_plan": item.is_complete_plan,
        "outbound": roundtrip_outbound_dict(item.outbound) if item.outbound else None,
        "return_flight": roundtrip_return_dict(item.return_flight) if item.return_flight else None,
        "create_time": dt(item.create_time),
    }


def plan_dict(item: FlightPlanResult) -> dict[str, Any]:
    if item.plan_type == "ROUNDTRIP_CLUE":
        source_type = "ROUNDTRIP_CLUE"
    elif item.plan_type == "ROUNDTRIP_TICKET":
        source_type = "ROUNDTRIP_PLAN"
    else:
        source_type = "ONE_WAY_PLAN"
    result: dict[str, Any] = {
        "id": item.id,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "monitor_name": item.monitor.monitor_name if item.monitor else None,
        "depart_date": dt(item.depart_date),
        "return_date": dt(item.return_date),
        "trip_type": "ROUND_TRIP" if source_type in {"ROUNDTRIP_CLUE", "ROUNDTRIP_PLAN"} else item.trip_type,
        "plan_type": item.plan_type,
        "source_type": source_type,
        "price_type": (
            "ROUND_TRIP_STARTING_PRICE"
            if source_type == "ROUNDTRIP_CLUE"
            else "ROUND_TRIP_TOTAL"
            if source_type == "ROUNDTRIP_PLAN"
            else "ONE_WAY_PRICE"
        ),
        "title": item.title,
        "from_city": item.monitor.from_city if item.monitor else None,
        "to_city": item.monitor.to_city if item.monitor else None,
        "total_price": item.total_price,
        "currency": item.currency,
        "total_duration_minutes": item.total_duration_minutes,
        "transfer_count": item.transfer_count,
        "risk_level": item.risk_level,
        "score": item.score,
        "reason": item.reason,
        "warning": item.warning,
        "detail_json": item.detail_json,
        "create_time": dt(item.create_time),
    }
    if item.detail_json:
        try:
            detail = json.loads(item.detail_json)
            result["airline"] = detail.get("airline")
            result["flight_no"] = detail.get("flight_no")
            result["depart_time"] = detail.get("depart_time")
            result["arrive_time"] = detail.get("arrive_time")
            result["depart_airport"] = detail.get("depart_airport")
            result["arrive_airport"] = detail.get("arrive_airport")
            result["data_completeness"] = detail.get("data_completeness")
            if source_type == "ROUNDTRIP_CLUE":
                result["outbound_airline"] = detail.get("airline")
                result["outbound_flight_no"] = detail.get("flight_no")
                result["outbound_depart_time"] = detail.get("depart_time")
                result["outbound_arrive_time"] = detail.get("arrive_time")
                result["outbound_depart_airport"] = detail.get("depart_airport")
                result["outbound_arrive_airport"] = detail.get("arrive_airport")
                result["return_detail_status"] = detail.get("return_detail_status")
            else:
                result["return_detail_status"] = "EXPANDED"
                result["outbound_summary"] = detail.get("outbound_summary")
                result["return_summary"] = detail.get("return_summary")
                result["roundtrip_plan_id"] = detail.get("roundtrip_plan_id")
                result["outbound_airline"] = detail.get("outbound_airline")
                result["outbound_flight_no"] = detail.get("outbound_flight_no")
                result["outbound_depart_time"] = detail.get("outbound_depart_time")
                result["outbound_arrive_time"] = detail.get("outbound_arrive_time")
                result["outbound_depart_airport"] = detail.get("outbound_depart_airport")
                result["outbound_arrive_airport"] = detail.get("outbound_arrive_airport")
                result["return_airline"] = detail.get("return_airline")
                result["return_flight_no"] = detail.get("return_flight_no")
                result["return_depart_time"] = detail.get("return_depart_time")
                result["return_arrive_time"] = detail.get("return_arrive_time")
                result["return_depart_airport"] = detail.get("return_depart_airport")
                result["return_arrive_airport"] = detail.get("return_arrive_airport")
        except (json.JSONDecodeError, TypeError):
            pass
    return result


def roundtrip_plan_as_plan_dict(item: FlightRoundTripPlan) -> dict[str, Any]:
    ob = item.outbound
    from_city = ob.from_city if ob else None
    to_city = ob.to_city if ob else None
    title_parts = ["完整往返"]
    if from_city and to_city:
        title_parts.append(f"{from_city} ⇄ {to_city}")
    return {
        "id": item.id,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "monitor_name": item.monitor.monitor_name if item.monitor else None,
        "depart_date": dt(item.depart_date),
        "return_date": dt(item.return_date),
        "trip_type": "ROUND_TRIP",
        "plan_type": "ROUNDTRIP_TICKET",
        "source_type": "ROUNDTRIP_PLAN",
        "price_type": item.price_type,
        "title": " · ".join(title_parts),
        "from_city": from_city,
        "to_city": to_city,
        "total_price": item.total_price,
        "currency": item.currency,
        "total_duration_minutes": item.total_duration_minutes,
        "transfer_count": item.total_transfer_count,
        "risk_level": item.risk_level,
        "score": item.score,
        "reason": item.reason,
        "warning": item.warning,
        "detail_json": None,
        "return_detail_status": "EXPANDED",
        "data_completeness": item.data_completeness,
        "outbound_summary": item.outbound_summary,
        "return_summary": item.return_summary,
        "create_time": dt(item.create_time),
    }


def best_dict(item: FlightBestDaily) -> dict[str, Any]:
    return {
        "id": item.id,
        "batch_no": item.batch_no,
        "monitor_id": item.monitor_id,
        "monitor_name": item.monitor.monitor_name if item.monitor else None,
        "depart_date": dt(item.depart_date),
        "best_price": item.best_price,
        "prev_best_price": item.prev_best_price,
        "price_trend": item.price_trend,
        "summary": item.summary,
        "best_plan": plan_dict(item.best_plan) if item.best_plan else None,
        "cheapest_plan": plan_dict(item.cheapest_plan) if item.cheapest_plan else None,
        "safest_plan": plan_dict(item.safest_plan) if item.safest_plan else None,
        "aggressive_plan": plan_dict(item.aggressive_plan) if item.aggressive_plan else None,
        "create_time": dt(item.create_time),
    }


def latest_best_daily_ids():
    return (
        select(func.max(FlightBestDaily.id))
        .group_by(FlightBestDaily.monitor_id, FlightBestDaily.depart_date)
    )


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    today = datetime.now().date()
    active_monitors = db.scalar(select(func.count(FlightMonitor.id)).where(FlightMonitor.enabled.is_(True))) or 0
    today_tasks = db.scalar(select(func.count(FlightQueryTask.id)).where(func.date(FlightQueryTask.create_time) == today.isoformat())) or 0
    success_today = db.scalar(select(func.count(FlightQueryTask.id)).where(func.date(FlightQueryTask.create_time) == today.isoformat(), FlightQueryTask.status == STATUS_SUCCESS)) or 0
    success_rate = round((success_today / today_tasks) * 100, 1) if today_tasks else 0
    status_distribution = {
        status: db.scalar(select(func.count(FlightQueryTask.id)).where(FlightQueryTask.status == status)) or 0
        for status in [STATUS_PENDING, STATUS_RUNNING, STATUS_SUCCESS, STATUS_FAILED]
    }
    today_scan_count = db.scalar(select(func.count(FlightScan.id)).where(func.date(FlightScan.create_time) == today.isoformat())) or 0
    running_scan_count = db.scalar(select(func.count(FlightScan.id)).where(FlightScan.status == STATUS_RUNNING)) or 0
    recent_scans = list(db.scalars(select(FlightScan).options(selectinload(FlightScan.monitor)).order_by(FlightScan.id.desc()).limit(5)))
    next_scheduled_monitor = db.scalar(
        select(FlightMonitor)
        .where(FlightMonitor.schedule_enabled.is_(True), FlightMonitor.next_scan_time.is_not(None))
        .order_by(FlightMonitor.next_scan_time.asc())
    )
    latest_best_ids = latest_best_daily_ids()
    best_items = list(
        db.scalars(
            select(FlightBestDaily)
            .options(selectinload(FlightBestDaily.monitor), selectinload(FlightBestDaily.best_plan))
            .where(FlightBestDaily.id.in_(latest_best_ids))
            .order_by(FlightBestDaily.create_time.desc())
            .limit(6)
        )
    )
    price_drops = db.scalar(
        select(func.count(FlightBestDaily.id))
        .where(FlightBestDaily.id.in_(latest_best_ids), FlightBestDaily.price_trend < 0)
    ) or 0
    return ok(
        {
            "active_monitors": active_monitors,
            "today_tasks": today_tasks,
            "today_scan_count": today_scan_count,
            "running_scan_count": running_scan_count,
            "recent_scans": [scan_dict(item) for item in recent_scans],
            "next_scheduled_scan": monitor_dict(next_scheduled_monitor) if next_scheduled_monitor else None,
            "success_rate": success_rate,
            "price_drops": price_drops,
            "task_status_distribution": status_distribution,
            "best_opportunities": [best_dict(item) for item in best_items],
            "manual_attention_count": status_distribution[STATUS_FAILED],
        }
    )


@router.get("/monitors")
def monitors(
    page: int = 1,
    page_size: int = 12,
    keyword: str | None = None,
    enabled: str | None = None,
    platform: str | None = None,
    trip_type: str | None = None,
    strategy: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(FlightMonitor).options(selectinload(FlightMonitor.dates)).order_by(FlightMonitor.id.desc())
    conditions = []
    if keyword:
        like = f"%{keyword}%"
        conditions.append(or_(FlightMonitor.monitor_name.like(like), FlightMonitor.from_city.like(like), FlightMonitor.to_city.like(like)))
    if enabled in {"true", "false"}:
        conditions.append(FlightMonitor.enabled.is_(enabled == "true"))
    if platform:
        conditions.append(FlightMonitor.platform == platform)
    if trip_type:
        conditions.append(FlightMonitor.trip_type == trip_type)
    if strategy == "direct":
        conditions.append(FlightMonitor.allow_direct.is_(True))
    elif strategy == "transfer":
        conditions.append(FlightMonitor.allow_transfer.is_(True))
    elif strategy == "train":
        conditions.append(FlightMonitor.allow_train_positioning.is_(True))
    elif strategy == "hidden":
        conditions.append(FlightMonitor.allow_hidden_city.is_(True))
    if conditions:
        stmt = stmt.where(and_(*conditions))
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([monitor_dict(item) for item in rows], total, page, page_size))


@router.get("/monitors/{monitor_id}")
def monitor_detail(monitor_id: int, db: Session = Depends(get_db)):
    item = db.get(FlightMonitor, monitor_id, options=[selectinload(FlightMonitor.dates)])
    if not item:
        raise HTTPException(status_code=404, detail="Monitor not found")
    return ok(monitor_dict(item))


@router.post("/monitors")
def create_monitor(payload: MonitorPayload, db: Session = Depends(get_db)):
    return ok(monitor_dict(monitor_service.create_monitor(db, payload.model_dump())))


@router.put("/monitors/{monitor_id}")
def update_monitor(monitor_id: int, payload: MonitorPayload, db: Session = Depends(get_db)):
    return ok(monitor_dict(monitor_service.update_monitor(db, monitor_id, payload.model_dump())))


@router.delete("/monitors/{monitor_id}")
def delete_monitor(monitor_id: int, db: Session = Depends(get_db)):
    monitor_service.delete_monitor(db, monitor_id)
    return ok({"deleted": True})


@router.post("/monitors/{monitor_id}/toggle")
def toggle_monitor(monitor_id: int, db: Session = Depends(get_db)):
    return ok(monitor_dict(monitor_service.toggle_monitor(db, monitor_id)))


@router.post("/monitors/{monitor_id}/scan-now")
def scan_monitor_now(monitor_id: int, db: Session = Depends(get_db)):
    try:
        scan = scan_monitor(db, monitor_id, TRIGGER_MANUAL)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok({"scan_id": scan.id, "scan_no": scan.scan_no, "status": scan.status})


@router.post("/monitors/{monitor_id}/cancel-running-scan")
def cancel_monitor_running_scan(monitor_id: int, db: Session = Depends(get_db)):
    scan = cancel_running_monitor_scan(db, monitor_id)
    if not scan:
        raise HTTPException(status_code=404, detail="No active scan for this monitor")
    return ok(scan_dict(scan))


@router.get("/monitors/{monitor_id}/schedule")
def get_monitor_schedule(monitor_id: int, db: Session = Depends(get_db)):
    monitor = monitor_service.get_monitor(db, monitor_id)
    return ok(
        {
            "monitor_id": monitor.id,
            "schedule_enabled": monitor.schedule_enabled,
            "schedule_cron": monitor.schedule_cron,
            "schedule_timezone": monitor.schedule_timezone,
            "schedule_remark": monitor.schedule_remark,
            "last_scan_id": monitor.last_scan_id,
            "last_scan_time": dt(monitor.last_scan_time),
            "last_scan_status": monitor.last_scan_status,
            "next_scan_time": dt(monitor.next_scan_time),
        }
    )


@router.put("/monitors/{monitor_id}/schedule")
def update_monitor_schedule(monitor_id: int, payload: MonitorSchedulePayload, db: Session = Depends(get_db)):
    monitor = monitor_service.get_monitor(db, monitor_id)
    try:
        validate_schedule_cron(payload.schedule_cron, payload.schedule_timezone)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    monitor.schedule_enabled = payload.schedule_enabled
    monitor.schedule_cron = payload.schedule_cron
    monitor.schedule_timezone = payload.schedule_timezone or "Asia/Shanghai"
    monitor.schedule_remark = payload.schedule_remark
    db.commit()
    refresh_scheduler()
    db.refresh(monitor)
    return ok(monitor_dict(monitor))


@router.post("/monitors/{monitor_id}/schedule/toggle")
def toggle_monitor_schedule(monitor_id: int, db: Session = Depends(get_db)):
    monitor = monitor_service.get_monitor(db, monitor_id)
    monitor.schedule_enabled = not monitor.schedule_enabled
    db.commit()
    refresh_scheduler()
    db.refresh(monitor)
    return ok(monitor_dict(monitor))


@router.post("/scheduler/reload")
def reload_scheduler():
    return ok(refresh_scheduler())


@router.get("/monitors/{monitor_id}/dates")
def monitor_dates(
    monitor_id: int,
    page: int = 1,
    page_size: int = 20,
    enabled: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = (
        select(FlightMonitorDate)
        .where(FlightMonitorDate.monitor_id == monitor_id)
        .order_by(FlightMonitorDate.depart_date, FlightMonitorDate.return_date)
    )
    if enabled in {"true", "false"}:
        stmt = stmt.where(FlightMonitorDate.enabled.is_(enabled == "true"))
    if start := parse_date(start_date):
        stmt = stmt.where(FlightMonitorDate.depart_date >= start)
    if end := parse_date(end_date):
        stmt = stmt.where(FlightMonitorDate.depart_date <= end)
    rows, total = paginate(db, stmt, page, page_size)
    items = [
        {
            "id": x.id,
            "monitor_id": x.monitor_id,
            "depart_date": dt(x.depart_date),
            "return_date": dt(x.return_date),
            "enabled": x.enabled,
            "remark": x.remark,
            "create_time": dt(x.create_time),
            "update_time": dt(x.update_time),
        }
        for x in rows
    ]
    return ok(page_result(items, total, page, page_size))


@router.post("/monitors/{monitor_id}/dates")
def add_monitor_date(monitor_id: int, payload: DatePayload, db: Session = Depends(get_db)):
    created = date_service.add_date(db, monitor_id, payload.depart_date, payload.remark, payload.return_date)
    return ok({"created": created})


@router.post("/monitors/{monitor_id}/dates/batch")
def batch_monitor_dates(monitor_id: int, payload: DateBatchPayload, db: Session = Depends(get_db)):
    created, skipped = date_service.batch_add_dates(
        db,
        monitor_id,
        payload.start_date,
        payload.end_date,
        set(payload.weekdays),
        payload.return_start_date,
        payload.return_end_date,
    )
    return ok({"created": created, "skipped": skipped})


@router.put("/monitor-dates/{date_id}/toggle")
def toggle_monitor_date(date_id: int, db: Session = Depends(get_db)):
    monitor_id = date_service.toggle_date(db, date_id)
    return ok({"monitor_id": monitor_id})


@router.delete("/monitor-dates/{date_id}")
def delete_monitor_date(date_id: int, db: Session = Depends(get_db)):
    monitor_id = date_service.delete_date(db, date_id)
    return ok({"monitor_id": monitor_id, "deleted": True})


@router.get("/monitors/{monitor_id}/positionings")
def monitor_positionings(monitor_id: int, db: Session = Depends(get_db)):
    monitor_service.get_monitor(db, monitor_id)
    return ok([positioning_dict(item) for item in positioning_service.list_positionings(db, monitor_id)])


@router.post("/monitors/{monitor_id}/positionings")
def create_positioning(monitor_id: int, payload: PositioningPayload, db: Session = Depends(get_db)):
    item = positioning_service.create_positioning(db, monitor_id, payload.model_dump())
    return ok(positioning_dict(item))


@router.put("/positionings/{positioning_id}")
def update_positioning(positioning_id: int, payload: PositioningPayload, db: Session = Depends(get_db)):
    item = positioning_service.update_positioning(db, positioning_id, payload.model_dump())
    return ok(positioning_dict(item))


@router.put("/positionings/{positioning_id}/toggle")
def toggle_positioning(positioning_id: int, db: Session = Depends(get_db)):
    monitor_id = positioning_service.toggle_positioning(db, positioning_id)
    return ok({"monitor_id": monitor_id})


@router.delete("/positionings/{positioning_id}")
def delete_positioning(positioning_id: int, db: Session = Depends(get_db)):
    monitor_id = positioning_service.delete_positioning(db, positioning_id)
    return ok({"monitor_id": monitor_id, "deleted": True})


@router.get("/monitors/{monitor_id}/transfers")
def monitor_transfers(monitor_id: int, db: Session = Depends(get_db)):
    monitor_service.get_monitor(db, monitor_id)
    return ok([transfer_dict(item) for item in transfer_service.list_transfers(db, monitor_id)])


@router.post("/monitors/{monitor_id}/transfers")
def create_transfer(monitor_id: int, payload: TransferPayload, db: Session = Depends(get_db)):
    item = transfer_service.create_transfer(db, monitor_id, payload.model_dump())
    return ok(transfer_dict(item))


@router.put("/transfers/{transfer_id}")
def update_transfer(transfer_id: int, payload: TransferPayload, db: Session = Depends(get_db)):
    item = transfer_service.update_transfer(db, transfer_id, payload.model_dump())
    return ok(transfer_dict(item))


@router.put("/transfers/{transfer_id}/toggle")
def toggle_transfer(transfer_id: int, db: Session = Depends(get_db)):
    monitor_id = transfer_service.toggle_transfer(db, transfer_id)
    return ok({"monitor_id": monitor_id})


@router.delete("/transfers/{transfer_id}")
def delete_transfer(transfer_id: int, db: Session = Depends(get_db)):
    monitor_id = transfer_service.delete_transfer(db, transfer_id)
    return ok({"monitor_id": monitor_id, "deleted": True})


@router.get("/scan-options")
def scan_options(monitor_id: int | None = None, limit: int = Query(default=80, ge=1, le=200), db: Session = Depends(get_db)):
    stmt = (
        select(FlightScan)
        .options(selectinload(FlightScan.monitor))
        .where(FlightScan.batch_no.isnot(None))
        .order_by(FlightScan.start_time.desc().nullslast(), FlightScan.id.desc())
        .limit(limit)
    )
    if monitor_id:
        stmt = stmt.where(FlightScan.monitor_id == monitor_id)
    return ok([scan_option_dict(item) for item in db.scalars(stmt)])


@router.get("/scans")
def scans(page: int = 1, page_size: int = 20, keyword: str | None = None, monitor_id: int | None = None, status: str | None = None, trigger_type: str | None = None, trip_type: str | None = None, start_date: str | None = None, end_date: str | None = None, db: Session = Depends(get_db)):
    stmt = select(FlightScan).options(selectinload(FlightScan.monitor)).order_by(FlightScan.id.desc())
    if keyword:
        stmt = stmt.where(FlightScan.scan_no.like(f"%{keyword}%"))
    if monitor_id:
        stmt = stmt.where(FlightScan.monitor_id == monitor_id)
    if status:
        stmt = stmt.where(FlightScan.status == status)
    if trigger_type:
        stmt = stmt.where(FlightScan.trigger_type == trigger_type)
    if trip_type:
        stmt = stmt.where(FlightScan.trip_type == trip_type)
    if start := parse_date(start_date):
        stmt = stmt.where(FlightScan.create_time >= datetime.combine(start, datetime.min.time()))
    if end := parse_date(end_date):
        stmt = stmt.where(FlightScan.create_time <= datetime.combine(end, datetime.max.time()))
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([scan_dict(item) for item in rows], total, page, page_size))


@router.get("/scans/{scan_id}")
def scan_detail(scan_id: int, db: Session = Depends(get_db)):
    item = db.get(FlightScan, scan_id, options=[selectinload(FlightScan.monitor)])
    if not item:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ok(scan_dict(item))


@router.post("/scans/{scan_id}/cancel")
def cancel_scan_api(scan_id: int, db: Session = Depends(get_db)):
    try:
        return ok(scan_dict(cancel_scan(db, scan_id)))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/scans/{scan_id}/restart")
def restart_scan_api(scan_id: int, db: Session = Depends(get_db)):
    try:
        return ok(scan_dict(restart_scan(db, scan_id)))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/scans/{scan_id}/steps")
def scan_steps(scan_id: int, db: Session = Depends(get_db)):
    if not db.get(FlightScan, scan_id):
        raise HTTPException(status_code=404, detail="Scan not found")
    logs = db.scalars(select(FlightScanStepLog).where(FlightScanStepLog.scan_id == scan_id).order_by(FlightScanStepLog.id))
    return ok([step_log_dict(item) for item in logs])


@router.get("/scans/{scan_id}/tasks")
def scan_tasks(scan_id: int, db: Session = Depends(get_db)):
    rows = db.scalars(select(FlightQueryTask).options(selectinload(FlightQueryTask.monitor)).where(FlightQueryTask.scan_id == scan_id).order_by(FlightQueryTask.id))
    return ok([task_dict(item) for item in rows])


@router.get("/batches")
def batches(page: int = 1, page_size: int = 20, keyword: str | None = None, status: str | None = None, trigger_type: str | None = None, db: Session = Depends(get_db)):
    stmt = select(FlightQueryBatch).order_by(FlightQueryBatch.id.desc())
    if keyword:
        stmt = stmt.where(FlightQueryBatch.batch_no.like(f"%{keyword}%"))
    if status:
        stmt = stmt.where(FlightQueryBatch.status == status)
    if trigger_type:
        stmt = stmt.where(FlightQueryBatch.trigger_type == trigger_type)
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([batch_dict(item) for item in rows], total, page, page_size))


@router.get("/tasks")
def tasks(page: int = 1, page_size: int = 20, scan_id: int | None = None, batch_no: str | None = None, monitor_id: int | None = None, status: str | None = None, trip_type: str | None = None, query_type: str | None = None, platform: str | None = None, depart_date: str | None = None, return_date: str | None = None, db: Session = Depends(get_db)):
    stmt = select(FlightQueryTask).options(selectinload(FlightQueryTask.monitor)).order_by(FlightQueryTask.id.desc())
    if scan_id:
        stmt = stmt.where(FlightQueryTask.scan_id == scan_id)
    if batch_no:
        stmt = stmt.where(FlightQueryTask.batch_no == batch_no)
    if monitor_id:
        stmt = stmt.where(FlightQueryTask.monitor_id == monitor_id)
    if status:
        stmt = stmt.where(FlightQueryTask.status == status)
    if trip_type:
        stmt = stmt.where(FlightQueryTask.trip_type == trip_type)
    if query_type:
        stmt = stmt.where(FlightQueryTask.query_type == query_type)
    if platform:
        stmt = stmt.where(FlightQueryTask.platform == platform)
    if parsed := parse_date(depart_date):
        stmt = stmt.where(FlightQueryTask.depart_date == parsed)
    if parsed_return := parse_date(return_date):
        stmt = stmt.where(FlightQueryTask.return_date == parsed_return)
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([task_dict(item) for item in rows], total, page, page_size))


@router.get("/tasks/{task_id}")
def task_detail(task_id: int, db: Session = Depends(get_db)):
    task = db.get(FlightQueryTask, task_id, options=[selectinload(FlightQueryTask.monitor)])
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return ok(task_dict(task))


@router.post("/tasks/{task_id}/run")
def run_task_api(task_id: int):
    return ok(run_ctrip_task(task_id))


@router.post("/tasks/{task_id}/reset")
def reset_task_api(task_id: int, db: Session = Depends(get_db)):
    return ok(task_dict(reset_task(db, task_id)))


@router.post("/tasks/{task_id}/cancel")
def cancel_task_api(task_id: int, db: Session = Depends(get_db)):
    return ok(task_dict(cancel_task(db, task_id)))


@router.post("/tasks/{task_id}/parse-price")
def parse_price_api(task_id: int):
    return ok(parse_task_price(task_id))


@router.get("/tasks/{task_id}/screenshot")
def task_screenshot_api(task_id: int, db: Session = Depends(get_db)):
    task = db.get(FlightQueryTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return file_response(task.screenshot_path, "Screenshot not found")


@router.get("/tasks/{task_id}/html")
def task_html_api(task_id: int, db: Session = Depends(get_db)):
    task = db.get(FlightQueryTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return file_response(task.html_path, "HTML snapshot not found")


@router.get("/prices")
def prices(page: int = 1, page_size: int = 20, batch_no: str | None = None, monitor_id: int | None = None, depart_date: str | None = None, platform: str | None = None, query_type: str | None = None, keyword: str | None = None, min_price: float | None = None, max_price: float | None = None, db: Session = Depends(get_db)):
    stmt = select(FlightPriceRaw).options(selectinload(FlightPriceRaw.task)).order_by(FlightPriceRaw.depart_date.asc(), FlightPriceRaw.price.asc())
    if batch_no:
        stmt = stmt.where(FlightPriceRaw.batch_no == batch_no)
    if monitor_id:
        stmt = stmt.where(FlightPriceRaw.monitor_id == monitor_id)
    if parsed := parse_date(depart_date):
        stmt = stmt.where(FlightPriceRaw.depart_date == parsed)
    if platform:
        stmt = stmt.where(FlightPriceRaw.platform == platform)
    if query_type:
        stmt = stmt.where(FlightPriceRaw.query_type == query_type)
    if keyword:
        stmt = stmt.where(or_(FlightPriceRaw.airline.like(f"%{keyword}%"), FlightPriceRaw.flight_no.like(f"%{keyword}%")))
    if min_price is not None:
        stmt = stmt.where(FlightPriceRaw.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(FlightPriceRaw.price <= max_price)
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([price_dict(item, price_change_dict(db, item)) for item in rows], total, page, page_size))


@router.get("/plans")
def plans(
    page: int = 1,
    page_size: int = 20,
    batch_no: str | None = None,
    monitor_id: int | None = None,
    depart_date: str | None = None,
    plan_type: str | None = None,
    risk_level: str | None = None,
    trip_type: str | None = None,
    source_type: str | None = None,
    return_date: str | None = None,
    include_roundtrip_plans: bool = False,
    latest_scan_only: bool = True,
    db: Session = Depends(get_db),
):
    batch_no = resolve_batch_no(db, batch_no)
    scan_time_q = (
        select(
            FlightScan.batch_no,
            func.max(FlightScan.start_time).label("scan_start_time"),
        )
        .where(FlightScan.batch_no.isnot(None))
        .where(FlightScan.start_time.isnot(None))
        .group_by(FlightScan.batch_no)
    )

    latest_batches = None
    if latest_scan_only:
        latest_per_monitor = (
            select(
                FlightScan.monitor_id,
                func.max(FlightScan.start_time).label("max_start"),
            )
            .where(FlightScan.monitor_id.isnot(None))
            .where(FlightScan.start_time.isnot(None))
            .where(FlightScan.batch_no.isnot(None))
            .group_by(FlightScan.monitor_id)
        ).subquery()
        latest_batches = select(FlightScan.batch_no).join(
            latest_per_monitor,
            and_(
                FlightScan.monitor_id == latest_per_monitor.c.monitor_id,
                FlightScan.start_time == latest_per_monitor.c.max_start,
            ),
        )
        scan_time_q = scan_time_q.where(FlightScan.batch_no.in_(latest_batches))

    scan_time_subq = scan_time_q.subquery()

    stmt = (
        select(FlightPlanResult)
        .options(selectinload(FlightPlanResult.monitor))
        .join(scan_time_subq, FlightPlanResult.batch_no == scan_time_subq.c.batch_no)
        .order_by(
            scan_time_subq.c.scan_start_time.desc(),
            FlightPlanResult.total_price.asc(),
        )
    )
    if batch_no:
        stmt = stmt.where(FlightPlanResult.batch_no == batch_no)
    if monitor_id:
        stmt = stmt.where(FlightPlanResult.monitor_id == monitor_id)
    if parsed := parse_date(depart_date):
        stmt = stmt.where(FlightPlanResult.depart_date == parsed)
    if plan_type:
        stmt = stmt.where(FlightPlanResult.plan_type == plan_type)
    if risk_level:
        stmt = stmt.where(FlightPlanResult.risk_level == risk_level)
    if trip_type:
        stmt = stmt.where(FlightPlanResult.trip_type == trip_type)
    if parsed_return := parse_date(return_date):
        stmt = stmt.where(FlightPlanResult.return_date == parsed_return)

    if source_type == "ONE_WAY_PLAN":
        stmt = stmt.where(FlightPlanResult.plan_type.not_in(["ROUNDTRIP_CLUE", "ROUNDTRIP_TICKET"]))
    elif source_type == "ROUNDTRIP_CLUE":
        stmt = stmt.where(FlightPlanResult.plan_type == "ROUNDTRIP_CLUE")
    elif source_type == "ROUNDTRIP_PLAN":
        stmt = stmt.where(FlightPlanResult.plan_type == "ROUNDTRIP_TICKET")

    plan_rows = list(db.scalars(stmt))
    all_items = prioritize_plan_dicts([plan_dict(p) for p in plan_rows])

    total = len(all_items)
    p = max(1, page)
    ps = min(max(1, page_size), 100)
    start = (p - 1) * ps
    end = start + ps
    items = all_items[start:end] if start < total else []
    return ok(page_result(items, total, p, ps))


@router.get("/round-trips/outbounds")
def roundtrip_outbounds(
    page: int = 1,
    page_size: int = 20,
    task_id: int | None = None,
    monitor_id: int | None = None,
    batch_no: str | None = None,
    return_detail_status: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = (
        select(FlightRoundTripOutbound)
        .options(selectinload(FlightRoundTripOutbound.monitor))
        .order_by(FlightRoundTripOutbound.create_time.desc(), FlightRoundTripOutbound.outbound_rank.asc())
    )
    if task_id:
        stmt = stmt.where(FlightRoundTripOutbound.task_id == task_id)
    if monitor_id:
        stmt = stmt.where(FlightRoundTripOutbound.monitor_id == monitor_id)
    if batch_no:
        stmt = stmt.where(FlightRoundTripOutbound.batch_no == batch_no)
    if return_detail_status:
        stmt = stmt.where(FlightRoundTripOutbound.return_detail_status == return_detail_status)
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([roundtrip_outbound_dict(item) for item in rows], total, page, page_size))


@router.get("/round-trips/outbounds/{outbound_id}")
def roundtrip_outbound_detail(outbound_id: int, db: Session = Depends(get_db)):
    item = db.get(FlightRoundTripOutbound, outbound_id, options=[selectinload(FlightRoundTripOutbound.monitor)])
    if not item:
        raise HTTPException(status_code=404, detail="Round-trip outbound not found")
    return ok(roundtrip_outbound_dict(item))


@router.post("/round-trips/outbounds/{outbound_id}/expand-return")
def expand_roundtrip_return(outbound_id: int, db: Session = Depends(get_db)):
    item = db.get(FlightRoundTripOutbound, outbound_id)
    if not item:
        raise HTTPException(status_code=404, detail="Round-trip outbound not found")
    raise HTTPException(status_code=501, detail="Round-trip return expansion will be implemented in stage 7")


@router.get("/round-trips/returns")
def roundtrip_returns(
    page: int = 1,
    page_size: int = 20,
    outbound_id: int | None = None,
    task_id: int | None = None,
    db: Session = Depends(get_db),
):
    stmt = select(FlightRoundTripReturn).order_by(FlightRoundTripReturn.create_time.desc(), FlightRoundTripReturn.return_rank.asc())
    if outbound_id:
        stmt = stmt.where(FlightRoundTripReturn.outbound_id == outbound_id)
    if task_id:
        stmt = stmt.where(FlightRoundTripReturn.task_id == task_id)
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([roundtrip_return_dict(item) for item in rows], total, page, page_size))


@router.get("/round-trips/plans")
def roundtrip_plans(
    page: int = 1,
    page_size: int = 20,
    task_id: int | None = None,
    monitor_id: int | None = None,
    batch_no: str | None = None,
    risk_level: str | None = None,
    db: Session = Depends(get_db),
):
    stmt = (
        select(FlightRoundTripPlan)
        .options(
            selectinload(FlightRoundTripPlan.monitor),
            selectinload(FlightRoundTripPlan.outbound),
            selectinload(FlightRoundTripPlan.return_flight),
        )
        .order_by(FlightRoundTripPlan.score.desc(), FlightRoundTripPlan.total_price.asc())
    )
    if task_id:
        stmt = stmt.where(FlightRoundTripPlan.task_id == task_id)
    if monitor_id:
        stmt = stmt.where(FlightRoundTripPlan.monitor_id == monitor_id)
    if batch_no:
        stmt = stmt.where(FlightRoundTripPlan.batch_no == batch_no)
    if risk_level:
        stmt = stmt.where(FlightRoundTripPlan.risk_level == risk_level)
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([roundtrip_plan_dict(item) for item in rows], total, page, page_size))


@router.get("/round-trips/plans/{plan_id}")
def roundtrip_plan_detail(plan_id: int, db: Session = Depends(get_db)):
    item = db.get(
        FlightRoundTripPlan,
        plan_id,
        options=[
            selectinload(FlightRoundTripPlan.monitor),
            selectinload(FlightRoundTripPlan.outbound),
            selectinload(FlightRoundTripPlan.return_flight),
        ],
    )
    if not item:
        raise HTTPException(status_code=404, detail="Round-trip plan not found")
    return ok(roundtrip_plan_dict(item))


@router.get("/best")
def best(
    page: int = 1,
    page_size: int = 20,
    batch_no: str | None = None,
    monitor_id: int | None = None,
    depart_date: str | None = None,
    latest_only: bool = True,
    db: Session = Depends(get_db),
):
    batch_no = resolve_batch_no(db, batch_no)
    stmt = select(FlightBestDaily).options(selectinload(FlightBestDaily.monitor), selectinload(FlightBestDaily.best_plan), selectinload(FlightBestDaily.cheapest_plan), selectinload(FlightBestDaily.safest_plan), selectinload(FlightBestDaily.aggressive_plan)).order_by(FlightBestDaily.create_time.desc())
    if latest_only and not batch_no:
        stmt = stmt.where(FlightBestDaily.id.in_(latest_best_daily_ids()))
    if batch_no:
        stmt = stmt.where(FlightBestDaily.batch_no == batch_no)
    if monitor_id:
        stmt = stmt.where(FlightBestDaily.monitor_id == monitor_id)
    if parsed := parse_date(depart_date):
        stmt = stmt.where(FlightBestDaily.depart_date == parsed)
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([best_dict(item) for item in rows], total, page, page_size))


@router.get("/city-codes")
def city_codes(page: int = 1, page_size: int = 100, platform: str = "CTRIP", keyword: str | None = None, enabled: bool | None = None, db: Session = Depends(get_db)):
    stmt = select(FlightCityCode).order_by(FlightCityCode.platform.asc(), FlightCityCode.city_name.asc())
    if platform:
        stmt = stmt.where(FlightCityCode.platform == platform)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        stmt = stmt.where(
            or_(
                FlightCityCode.city_name.like(pattern),
                FlightCityCode.city_code.like(pattern),
                FlightCityCode.aliases.like(pattern),
                FlightCityCode.country.like(pattern),
            )
        )
    if enabled is not None:
        stmt = stmt.where(FlightCityCode.enabled.is_(enabled))
    rows, total = paginate(db, stmt, page, page_size)
    return ok(page_result([city_code_dict(item) for item in rows], total, page, page_size))


@router.post("/city-codes/seed")
def seed_city_codes(db: Session = Depends(get_db)):
    return ok({"inserted": seed_default_city_codes(db)})


@router.post("/city-codes/sync-ourairports")
def sync_city_codes_from_ourairports(limit: int | None = Query(default=None, ge=1, le=20000), db: Session = Depends(get_db)):
    return ok(sync_ourairports_city_codes(db, limit=limit))


@router.post("/city-codes")
def create_city_code(payload: CityCodePayload, db: Session = Depends(get_db)):
    existing = db.scalar(
        select(FlightCityCode).where(
            FlightCityCode.platform == payload.platform,
            FlightCityCode.city_name == payload.city_name,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="City code already exists for this platform and city")
    item = FlightCityCode(**payload.model_dump())
    item.city_code = item.city_code.lower()
    db.add(item)
    db.commit()
    db.refresh(item)
    return ok(city_code_dict(item))


@router.put("/city-codes/{city_code_id}")
def update_city_code(city_code_id: int, payload: CityCodePayload, db: Session = Depends(get_db)):
    item = db.get(FlightCityCode, city_code_id)
    if not item:
        raise HTTPException(status_code=404, detail="City code not found")
    for key, value in payload.model_dump().items():
        setattr(item, key, value.lower() if key == "city_code" and isinstance(value, str) else value)
    db.commit()
    db.refresh(item)
    return ok(city_code_dict(item))


@router.delete("/city-codes/{city_code_id}")
def delete_city_code(city_code_id: int, db: Session = Depends(get_db)):
    item = db.get(FlightCityCode, city_code_id)
    if not item:
        raise HTTPException(status_code=404, detail="City code not found")
    db.delete(item)
    db.commit()
    return ok({"deleted": city_code_id})


@router.get("/settings")
def get_settings():
    from app.services.settings_service import (
        SCAN_INTERVAL_MAX_ALLOWED,
        SCAN_INTERVAL_MIN_ALLOWED,
        get_scan_interval_range,
        load_settings,
    )

    s = load_settings()
    production = os.getenv("APP_ENV", "development").strip().lower() in {"production", "prod"}
    interval_min_seconds, interval_max_seconds = get_scan_interval_range()
    pushplus = (os.getenv("PUSHPLUS_TOKEN") or "").strip()
    wework = (os.getenv("WEWORK_WEBHOOK_URL") or "").strip()
    return ok(
        {
            "browser": {
                "profile_path": None if production else str(DATA_DIR / "browser_profile" / "ctrip"),
                "headless": s.get("headless", False),
                "query_interval": f"{interval_min_seconds}-{interval_max_seconds} seconds",
                "scan_interval_min_seconds": interval_min_seconds,
                "scan_interval_max_seconds": interval_max_seconds,
                "scan_interval_min_allowed": SCAN_INTERVAL_MIN_ALLOWED,
                "scan_interval_max_allowed": SCAN_INTERVAL_MAX_ALLOWED,
            },
            "storage": None
            if production
            else {
                "sqlite_path": str(DATA_DIR / "flight_claw.db"),
                "screenshots_path": str(DATA_DIR / "screenshots"),
                "text_path": str(DATA_DIR / "text"),
            },
            "notification": {
                "pushplus_configured": bool(pushplus),
                "wecom_configured": bool(wework),
            },
            "safety_policy": [
                "不绕过验证码",
                "不使用代理池",
                "不抓取非公开 API",
                "个人低频使用",
                "不自动下单",
            ],
        }
    )


class SettingsPayload(BaseModel):
    headless: bool = False
    scan_interval_min_seconds: int = 30
    scan_interval_max_seconds: int = 90


@router.put("/settings")
def update_settings(payload: SettingsPayload):
    from app.services.settings_service import save_settings

    try:
        saved = save_settings(
            {
                "headless": payload.headless,
                "scan_interval_min_seconds": payload.scan_interval_min_seconds,
                "scan_interval_max_seconds": payload.scan_interval_max_seconds,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ok(saved)
