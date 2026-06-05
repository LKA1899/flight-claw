from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.constants import (
    COMPLETENESS_OUTBOUND_WITH_STARTING_PRICE,
    COMPLETENESS_FULL_ROUND_TRIP,
    LEG_OUTBOUND,
    LEG_ROUND_TRIP_COMBO,
    PLATFORM_CTRIP,
    PRICE_ONE_WAY,
    PRICE_ROUND_TRIP_STARTING,
    PRICE_ROUND_TRIP_TOTAL,
    RETURN_DETAIL_NOT_EXPANDED,
    ROUNDTRIP_DATA_OUTBOUND_ONLY,
    ROUNDTRIP_EXPAND_NONE,
    STATUS_PENDING,
    TRIP_ONE_WAY,
)
from app.db import Base


def now() -> datetime:
    return datetime.now()


class TimestampMixin:
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)
    update_time: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now, nullable=False)


class FlightCityCode(Base, TimestampMixin):
    __tablename__ = "flight_city_code"
    __table_args__ = (UniqueConstraint("platform", "city_name", name="uq_flight_city_code_platform_city"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    platform: Mapped[str] = mapped_column(String(30), default=PLATFORM_CTRIP, nullable=False, index=True)
    city_name: Mapped[str] = mapped_column(String(80), nullable=False)
    city_code: Mapped[str] = mapped_column(String(20), nullable=False)
    aliases: Mapped[str | None] = mapped_column(String(500))
    country: Mapped[str | None] = mapped_column(String(80))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)


class FlightMonitor(Base, TimestampMixin):
    __tablename__ = "flight_monitor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_name: Mapped[str] = mapped_column(String(200), nullable=False)
    from_city: Mapped[str] = mapped_column(String(80), nullable=False)
    from_airports: Mapped[str | None] = mapped_column(String(200))
    to_city: Mapped[str] = mapped_column(String(80), nullable=False)
    to_airports: Mapped[str | None] = mapped_column(String(200))
    platform: Mapped[str] = mapped_column(String(30), default=PLATFORM_CTRIP, nullable=False)
    trip_type: Mapped[str] = mapped_column(String(30), default=TRIP_ONE_WAY, nullable=False)
    allow_direct: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_transfer: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_train_positioning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allow_hidden_city: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    max_transfer_count: Mapped[int | None] = mapped_column(Integer)
    max_total_hours: Mapped[int | None] = mapped_column(Integer)
    max_price: Mapped[float | None] = mapped_column(Float)
    roundtrip_data_level: Mapped[str] = mapped_column(String(50), default=ROUNDTRIP_DATA_OUTBOUND_ONLY, nullable=False)
    roundtrip_expand_return: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    roundtrip_outbound_expand_mode: Mapped[str] = mapped_column(String(50), default=ROUNDTRIP_EXPAND_NONE, nullable=False)
    roundtrip_expand_top_n: Mapped[int] = mapped_column(Integer, default=3, nullable=False)
    roundtrip_expand_ranks: Mapped[str | None] = mapped_column(String(100))
    roundtrip_return_fetch_limit: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    roundtrip_return_sort_strategy: Mapped[str] = mapped_column(String(50), default="LOW_PRICE", nullable=False)
    roundtrip_save_all_outbounds: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    roundtrip_expand_only_priced: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    roundtrip_skip_expand_over_budget: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    continue_on_expand_failed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    save_step_snapshot: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(100))
    schedule_timezone: Mapped[str] = mapped_column(String(100), default="Asia/Shanghai", nullable=False)
    schedule_remark: Mapped[str | None] = mapped_column(String(500))
    last_scan_id: Mapped[int | None] = mapped_column(Integer)
    last_scan_time: Mapped[datetime | None] = mapped_column(DateTime)
    last_scan_status: Mapped[str | None] = mapped_column(String(30))
    next_scan_time: Mapped[datetime | None] = mapped_column(DateTime)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)

    dates: Mapped[list["FlightMonitorDate"]] = relationship(
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="FlightMonitorDate.depart_date",
    )
    positionings: Mapped[list["FlightPositioningCity"]] = relationship(
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="FlightPositioningCity.sort_no",
    )
    transfers: Mapped[list["FlightTransferCity"]] = relationship(
        back_populates="monitor",
        cascade="all, delete-orphan",
        order_by="FlightTransferCity.sort_no",
    )


class FlightPositioningCity(Base, TimestampMixin):
    __tablename__ = "flight_positioning_city"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False, index=True)
    from_city: Mapped[str] = mapped_column(String(80), nullable=False)
    positioning_city: Mapped[str] = mapped_column(String(80), nullable=False)
    positioning_type: Mapped[str] = mapped_column(String(30), default="TRAIN", nullable=False)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_no: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)

    monitor: Mapped[FlightMonitor] = relationship(back_populates="positionings")


class FlightTransferCity(Base, TimestampMixin):
    __tablename__ = "flight_transfer_city"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False, index=True)
    transfer_city: Mapped[str] = mapped_column(String(80), nullable=False)
    transfer_airports: Mapped[str | None] = mapped_column(String(200))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_no: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)

    monitor: Mapped[FlightMonitor] = relationship(back_populates="transfers")


class FlightMonitorDate(Base, TimestampMixin):
    __tablename__ = "flight_monitor_date"
    __table_args__ = (
        Index(
            "uq_monitor_oneway_depart_date",
            "monitor_id",
            "depart_date",
            unique=True,
            sqlite_where=text("return_date IS NULL"),
        ),
        Index(
            "uq_monitor_roundtrip_depart_return_date",
            "monitor_id",
            "depart_date",
            "return_date",
            unique=True,
            sqlite_where=text("return_date IS NOT NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    remark: Mapped[str | None] = mapped_column(Text)

    monitor: Mapped[FlightMonitor] = relationship(back_populates="dates")


class FlightQueryBatch(Base):
    __tablename__ = "flight_query_batch"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("flight_scan.id"))
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=STATUS_PENDING, nullable=False)
    total_task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class FlightQueryTask(Base):
    __tablename__ = "flight_query_task"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("flight_scan.id"), index=True)
    batch_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date)
    trip_type: Mapped[str] = mapped_column(String(30), default=TRIP_ONE_WAY, nullable=False)
    query_type: Mapped[str] = mapped_column(String(40), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default=PLATFORM_CTRIP, nullable=False)
    from_city: Mapped[str] = mapped_column(String(80), nullable=False)
    to_city: Mapped[str] = mapped_column(String(80), nullable=False)
    transfer_city: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(30), default=STATUS_PENDING, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    screenshot_path: Mapped[str | None] = mapped_column(String(300))
    html_path: Mapped[str | None] = mapped_column(String(300))
    text_path: Mapped[str | None] = mapped_column(String(300))
    parse_status: Mapped[str | None] = mapped_column(String(30))
    parse_error_message: Mapped[str | None] = mapped_column(Text)
    parsed_time: Mapped[datetime | None] = mapped_column(DateTime)
    strategy_snapshot_json: Mapped[str | None] = mapped_column(Text)
    data_completeness: Mapped[str | None] = mapped_column(String(50))
    roundtrip_stage: Mapped[str | None] = mapped_column(String(50))
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    monitor: Mapped[FlightMonitor] = relationship()


class FlightTaskArtifact(Base):
    __tablename__ = "flight_task_artifact"
    __table_args__ = (
        Index("ix_task_artifact_task_stage_type", "task_id", "stage", "artifact_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("flight_query_task.id"), nullable=False, index=True)
    stage: Mapped[str] = mapped_column(String(80), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(30), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    label: Mapped[str | None] = mapped_column(String(120))
    meta_json: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    task: Mapped[FlightQueryTask] = relationship()


class FlightScan(Base):
    __tablename__ = "flight_scan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_no: Mapped[str] = mapped_column(String(40), unique=True, nullable=False)
    batch_no: Mapped[str | None] = mapped_column(String(40), index=True)
    monitor_id: Mapped[int | None] = mapped_column(ForeignKey("flight_monitor.id"), index=True)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=STATUS_PENDING, nullable=False)
    trip_type: Mapped[str | None] = mapped_column(String(30))
    total_task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failed_task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    partial_task_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    report_id: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    monitor: Mapped[FlightMonitor | None] = relationship()
    step_logs: Mapped[list["FlightScanStepLog"]] = relationship(
        cascade="all, delete-orphan",
        order_by="FlightScanStepLog.id",
    )


class FlightScanStepLog(Base):
    __tablename__ = "flight_scan_step_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int] = mapped_column(ForeignKey("flight_scan.id"), nullable=False, index=True)
    step_code: Mapped[str] = mapped_column(String(80), nullable=False)
    step_name: Mapped[str] = mapped_column(String(120), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default=STATUS_PENDING, nullable=False)
    input_json: Mapped[str | None] = mapped_column(Text)
    output_json: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    start_time: Mapped[datetime | None] = mapped_column(DateTime)
    end_time: Mapped[datetime | None] = mapped_column(DateTime)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class FlightReport(Base):
    __tablename__ = "flight_report"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    scan_id: Mapped[int | None] = mapped_column(ForeignKey("flight_scan.id"))
    monitor_id: Mapped[int | None] = mapped_column(ForeignKey("flight_monitor.id"))
    batch_no: Mapped[str | None] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    llm_content_md: Mapped[str | None] = mapped_column(Text)
    llm_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    llm_error_message: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class FlightPriceRaw(Base):
    __tablename__ = "flight_price_raw"
    __table_args__ = (UniqueConstraint("unique_hash", name="uq_flight_price_raw_unique_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("flight_query_task.id"), nullable=False, index=True)
    batch_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    trip_type: Mapped[str] = mapped_column(String(30), default=TRIP_ONE_WAY, nullable=False)
    leg_type: Mapped[str] = mapped_column(String(30), default=LEG_OUTBOUND, nullable=False)
    query_type: Mapped[str] = mapped_column(String(40), nullable=False)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False)
    return_date: Mapped[date | None] = mapped_column(Date)
    from_city: Mapped[str] = mapped_column(String(80), nullable=False)
    to_city: Mapped[str] = mapped_column(String(80), nullable=False)
    airline: Mapped[str | None] = mapped_column(String(120))
    flight_no: Mapped[str | None] = mapped_column(String(40))
    depart_time: Mapped[str | None] = mapped_column(String(20))
    arrive_time: Mapped[str | None] = mapped_column(String(20))
    depart_airport: Mapped[str | None] = mapped_column(String(120))
    arrive_airport: Mapped[str | None] = mapped_column(String(120))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    transfer_count: Mapped[int | None] = mapped_column(Integer)
    transfer_city: Mapped[str | None] = mapped_column(String(80))
    cabin_info: Mapped[str | None] = mapped_column(String(200))
    baggage_info: Mapped[str | None] = mapped_column(String(200))
    price: Mapped[float] = mapped_column(Float, nullable=False)
    price_type: Mapped[str] = mapped_column(String(50), default=PRICE_ONE_WAY, nullable=False)
    data_completeness: Mapped[str | None] = mapped_column(String(50))
    is_complete_plan: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    source_html_path: Mapped[str | None] = mapped_column(String(300))
    source_screenshot_path: Mapped[str | None] = mapped_column(String(300))
    raw_text: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[str | None] = mapped_column(Text)
    parse_status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    unique_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    task: Mapped[FlightQueryTask] = relationship()


class FlightRoundTripOutbound(Base):
    __tablename__ = "flight_roundtrip_outbound"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("flight_query_task.id"), nullable=False, index=True)
    batch_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False, index=True)
    platform: Mapped[str] = mapped_column(String(30), default=PLATFORM_CTRIP, nullable=False)
    from_city: Mapped[str] = mapped_column(String(80), nullable=False)
    to_city: Mapped[str] = mapped_column(String(80), nullable=False)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    return_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    outbound_rank: Mapped[int | None] = mapped_column(Integer)
    airline: Mapped[str | None] = mapped_column(String(120))
    flight_no: Mapped[str | None] = mapped_column(String(80))
    depart_time: Mapped[str | None] = mapped_column(String(20))
    arrive_time: Mapped[str | None] = mapped_column(String(20))
    depart_airport: Mapped[str | None] = mapped_column(String(120))
    arrive_airport: Mapped[str | None] = mapped_column(String(120))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    transfer_count: Mapped[int | None] = mapped_column(Integer)
    transfer_city: Mapped[str | None] = mapped_column(String(80))
    cabin_info: Mapped[str | None] = mapped_column(String(200))
    baggage_info: Mapped[str | None] = mapped_column(String(200))
    display_total_price: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    price_type: Mapped[str] = mapped_column(String(50), default=PRICE_ROUND_TRIP_STARTING, nullable=False)
    price_display_text: Mapped[str | None] = mapped_column(String(120))
    return_detail_status: Mapped[str] = mapped_column(String(50), default=RETURN_DETAIL_NOT_EXPANDED, nullable=False)
    data_completeness: Mapped[str] = mapped_column(
        String(50), default=COMPLETENESS_OUTBOUND_WITH_STARTING_PRICE, nullable=False
    )
    is_complete_plan: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    source_html_path: Mapped[str | None] = mapped_column(String(300))
    source_screenshot_path: Mapped[str | None] = mapped_column(String(300))
    raw_text: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    task: Mapped[FlightQueryTask] = relationship()
    monitor: Mapped[FlightMonitor] = relationship()


class FlightRoundTripReturn(Base):
    __tablename__ = "flight_roundtrip_return"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("flight_query_task.id"), nullable=False, index=True)
    batch_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False, index=True)
    outbound_id: Mapped[int] = mapped_column(ForeignKey("flight_roundtrip_outbound.id"), nullable=False, index=True)
    from_city: Mapped[str] = mapped_column(String(80), nullable=False)
    to_city: Mapped[str] = mapped_column(String(80), nullable=False)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    return_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    return_rank: Mapped[int | None] = mapped_column(Integer)
    airline: Mapped[str | None] = mapped_column(String(120))
    flight_no: Mapped[str | None] = mapped_column(String(80))
    depart_time: Mapped[str | None] = mapped_column(String(20))
    arrive_time: Mapped[str | None] = mapped_column(String(20))
    depart_airport: Mapped[str | None] = mapped_column(String(120))
    arrive_airport: Mapped[str | None] = mapped_column(String(120))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    transfer_count: Mapped[int | None] = mapped_column(Integer)
    transfer_city: Mapped[str | None] = mapped_column(String(80))
    cabin_info: Mapped[str | None] = mapped_column(String(200))
    baggage_info: Mapped[str | None] = mapped_column(String(200))
    total_price: Mapped[float | None] = mapped_column(Float)
    price_delta: Mapped[float | None] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    price_type: Mapped[str] = mapped_column(String(50), default=PRICE_ROUND_TRIP_TOTAL, nullable=False)
    price_display_text: Mapped[str | None] = mapped_column(String(120))
    source_html_path: Mapped[str | None] = mapped_column(String(300))
    source_screenshot_path: Mapped[str | None] = mapped_column(String(300))
    raw_text: Mapped[str | None] = mapped_column(Text)
    raw_json: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    task: Mapped[FlightQueryTask] = relationship()
    monitor: Mapped[FlightMonitor] = relationship()
    outbound: Mapped[FlightRoundTripOutbound] = relationship()


class FlightRoundTripPlan(Base):
    __tablename__ = "flight_roundtrip_plan"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("flight_query_task.id"), nullable=False, index=True)
    batch_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False, index=True)
    outbound_id: Mapped[int] = mapped_column(ForeignKey("flight_roundtrip_outbound.id"), nullable=False, index=True)
    return_id: Mapped[int] = mapped_column(ForeignKey("flight_roundtrip_return.id"), nullable=False, index=True)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    return_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    leg_type: Mapped[str] = mapped_column(String(30), default=LEG_ROUND_TRIP_COMBO, nullable=False)
    price_type: Mapped[str] = mapped_column(String(50), default=PRICE_ROUND_TRIP_TOTAL, nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    total_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    total_transfer_count: Mapped[int | None] = mapped_column(Integer)
    outbound_summary: Mapped[str | None] = mapped_column(Text)
    return_summary: Mapped[str | None] = mapped_column(Text)
    risk_level: Mapped[str | None] = mapped_column(String(20))
    score: Mapped[float | None] = mapped_column(Float)
    reason: Mapped[str | None] = mapped_column(Text)
    warning: Mapped[str | None] = mapped_column(Text)
    data_completeness: Mapped[str] = mapped_column(String(50), default=COMPLETENESS_FULL_ROUND_TRIP, nullable=False)
    is_complete_plan: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    task: Mapped[FlightQueryTask] = relationship()
    monitor: Mapped[FlightMonitor] = relationship()
    outbound: Mapped[FlightRoundTripOutbound] = relationship()
    return_flight: Mapped[FlightRoundTripReturn] = relationship()


class FlightPlanResult(Base):
    __tablename__ = "flight_plan_result"
    __table_args__ = (UniqueConstraint("unique_hash", name="uq_flight_plan_result_unique_hash"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False, index=True)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    return_date: Mapped[date | None] = mapped_column(Date)
    trip_type: Mapped[str] = mapped_column(String(30), default=TRIP_ONE_WAY, nullable=False)
    plan_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    total_price: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="CNY", nullable=False)
    total_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    transfer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(20), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    source_task_ids: Mapped[str] = mapped_column(String(300), nullable=False)
    source_price_ids: Mapped[str] = mapped_column(String(300), nullable=False)
    detail_json: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(Text)
    warning: Mapped[str | None] = mapped_column(Text)
    unique_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    monitor: Mapped[FlightMonitor] = relationship()


class FlightBestDaily(Base):
    __tablename__ = "flight_best_daily"
    __table_args__ = (UniqueConstraint("batch_no", "monitor_id", "depart_date", name="uq_best_daily_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_no: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    monitor_id: Mapped[int] = mapped_column(ForeignKey("flight_monitor.id"), nullable=False, index=True)
    depart_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    best_plan_id: Mapped[int | None] = mapped_column(ForeignKey("flight_plan_result.id"))
    cheapest_plan_id: Mapped[int | None] = mapped_column(ForeignKey("flight_plan_result.id"))
    safest_plan_id: Mapped[int | None] = mapped_column(ForeignKey("flight_plan_result.id"))
    aggressive_plan_id: Mapped[int | None] = mapped_column(ForeignKey("flight_plan_result.id"))
    best_price: Mapped[float | None] = mapped_column(Float)
    prev_best_price: Mapped[float | None] = mapped_column(Float)
    price_trend: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)

    monitor: Mapped[FlightMonitor] = relationship()
    best_plan: Mapped[FlightPlanResult | None] = relationship(foreign_keys=[best_plan_id])
    cheapest_plan: Mapped[FlightPlanResult | None] = relationship(foreign_keys=[cheapest_plan_id])
    safest_plan: Mapped[FlightPlanResult | None] = relationship(foreign_keys=[safest_plan_id])
    aggressive_plan: Mapped[FlightPlanResult | None] = relationship(foreign_keys=[aggressive_plan_id])


class FlightNotificationLog(Base):
    __tablename__ = "flight_notification_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    batch_no: Mapped[str | None] = mapped_column(String(40), index=True)
    channel: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(240), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)
    create_time: Mapped[datetime] = mapped_column(DateTime, default=now, nullable=False)


class FlightUser(Base, TimestampMixin):
    __tablename__ = "flight_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(80))
    role: Mapped[str] = mapped_column(String(20), default="ADMIN", nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    last_login_time: Mapped[datetime | None] = mapped_column(DateTime)
