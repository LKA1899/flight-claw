import secrets
import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.constants import (
    PLATFORM_CTRIP,
    QUERY_DIRECT,
    QUERY_HIDDEN_CITY,
    QUERY_TRAIN_PLUS_FLIGHT,
    QUERY_TRANSFER,
    COMPLETENESS_SNAPSHOT_ONLY,
    ROUNDTRIP_DATA_OUTBOUND_ONLY,
    ROUNDTRIP_EXPAND_NONE,
    STATUS_FAILED,
    STATUS_PENDING,
    STATUS_PARTIAL_SUCCESS,
    STATUS_RUNNING,
    STATUS_SKIPPED,
    STATUS_SUCCESS,
    TRIP_ONE_WAY,
    TRIP_ROUND_TRIP,
    TRIGGER_SCAN,
)
from app.models import FlightMonitor, FlightQueryBatch, FlightQueryTask
from app.services.date_service import enabled_dates_for_monitor
from app.services.positioning_service import enabled_positionings
from app.services.transfer_service import enabled_transfers


def make_batch_no() -> str:
    return f"BATCH_{datetime.now():%Y%m%d%H%M%S%f}_{secrets.token_hex(2)}"


def list_batches(db: Session) -> list[FlightQueryBatch]:
    return list(db.scalars(select(FlightQueryBatch).order_by(FlightQueryBatch.id.desc())))


def list_tasks(db: Session, batch_no: str | None = None) -> list[FlightQueryTask]:
    stmt = select(FlightQueryTask).order_by(FlightQueryTask.id.desc())
    if batch_no:
        stmt = stmt.where(FlightQueryTask.batch_no == batch_no)
    return list(db.scalars(stmt))


def get_task(db: Session, task_id: int) -> FlightQueryTask:
    task = db.get(FlightQueryTask, task_id)
    if not task:
        raise ValueError(f"Query task not found: {task_id}")
    return task


def reset_task(db: Session, task_id: int) -> FlightQueryTask:
    task = get_task(db, task_id)
    task.status = STATUS_PENDING
    task.error_message = None
    task.parse_status = None
    task.parse_error_message = None
    task.parsed_time = None
    task.data_completeness = None
    task.roundtrip_stage = None
    task.start_time = None
    task.end_time = None
    db.commit()
    db.refresh(task)
    return task


def pending_ctrip_tasks_for_batch(db: Session, batch_no: str) -> list[FlightQueryTask]:
    return list(
        db.scalars(
            select(FlightQueryTask)
            .where(
                FlightQueryTask.batch_no == batch_no,
                FlightQueryTask.platform == PLATFORM_CTRIP,
                FlightQueryTask.status == STATUS_PENDING,
            )
            .order_by(FlightQueryTask.id)
        )
    )


def successful_tasks_with_snapshot_for_batch(db: Session, batch_no: str) -> list[FlightQueryTask]:
    return list(
        db.scalars(
            select(FlightQueryTask)
            .where(
                FlightQueryTask.batch_no == batch_no,
                FlightQueryTask.status == STATUS_SUCCESS,
                (FlightQueryTask.text_path.is_not(None) | FlightQueryTask.html_path.is_not(None)),
            )
            .order_by(FlightQueryTask.id)
        )
    )


successful_tasks_with_html_for_batch = successful_tasks_with_snapshot_for_batch


def refresh_batch_counts(db: Session, batch_no: str) -> None:
    batch = db.scalar(select(FlightQueryBatch).where(FlightQueryBatch.batch_no == batch_no))
    if not batch:
        return
    tasks = list(db.scalars(select(FlightQueryTask).where(FlightQueryTask.batch_no == batch_no)))
    batch.total_task_count = len(tasks)
    partial_count = sum(1 for task in tasks if task.status == STATUS_PARTIAL_SUCCESS)
    batch.success_task_count = sum(1 for task in tasks if task.status == STATUS_SUCCESS)
    batch.failed_task_count = sum(1 for task in tasks if task.status == STATUS_FAILED)
    running_count = sum(1 for task in tasks if task.status == STATUS_RUNNING)
    pending_count = sum(1 for task in tasks if task.status == STATUS_PENDING)
    completed_count = batch.success_task_count + partial_count + batch.failed_task_count
    if running_count or (pending_count and completed_count):
        batch.status = STATUS_RUNNING
        batch.end_time = None
    elif pending_count:
        batch.status = STATUS_PENDING
        batch.end_time = None
    elif tasks and batch.success_task_count == len(tasks):
        batch.status = STATUS_SUCCESS
        batch.end_time = datetime.now()
    elif tasks and batch.failed_task_count == len(tasks):
        batch.status = STATUS_FAILED
        batch.end_time = datetime.now()
    elif tasks:
        batch.status = STATUS_PARTIAL_SUCCESS
        batch.end_time = datetime.now()
    elif not tasks:
        batch.status = STATUS_SKIPPED
        batch.end_time = datetime.now()
    db.commit()


def _query_types(monitor: FlightMonitor) -> list[str]:
    values: list[str] = []
    if monitor.allow_direct:
        values.append(QUERY_DIRECT)
    if monitor.allow_hidden_city:
        # Hidden-city ticketing needs an explicit throwaway destination or segment model.
        # This version intentionally avoids generating mislabeled normal route queries.
        pass
    return values


def _roundtrip_strategy_snapshot(monitor: FlightMonitor) -> str:
    return json.dumps(
        {
            "roundtrip_data_level": monitor.roundtrip_data_level or ROUNDTRIP_DATA_OUTBOUND_ONLY,
            "roundtrip_expand_return": bool(monitor.roundtrip_expand_return),
            "roundtrip_outbound_expand_mode": monitor.roundtrip_outbound_expand_mode or ROUNDTRIP_EXPAND_NONE,
            "roundtrip_expand_top_n": monitor.roundtrip_expand_top_n,
            "roundtrip_expand_ranks": monitor.roundtrip_expand_ranks,
            "roundtrip_return_fetch_limit": monitor.roundtrip_return_fetch_limit,
            "roundtrip_return_sort_strategy": monitor.roundtrip_return_sort_strategy,
            "roundtrip_save_all_outbounds": bool(monitor.roundtrip_save_all_outbounds),
            "roundtrip_expand_only_priced": bool(monitor.roundtrip_expand_only_priced),
            "roundtrip_skip_expand_over_budget": bool(monitor.roundtrip_skip_expand_over_budget),
            "continue_on_expand_failed": bool(monitor.continue_on_expand_failed),
            "save_step_snapshot": bool(monitor.save_step_snapshot),
            "manual_takeover_enabled": bool(monitor.manual_takeover_enabled),
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def _add_oneway_task(
    db: Session,
    batch: FlightQueryBatch,
    monitor: FlightMonitor,
    depart_date,
    query_type: str,
    from_city: str | None = None,
    transfer_city: str | None = None,
) -> None:
    db.add(
        FlightQueryTask(
            scan_id=batch.scan_id,
            batch_no=batch.batch_no,
            monitor_id=monitor.id,
            depart_date=depart_date,
            return_date=None,
            trip_type=TRIP_ONE_WAY,
            query_type=query_type,
            platform=monitor.platform,
            from_city=from_city or monitor.from_city,
            to_city=monitor.to_city,
            transfer_city=transfer_city,
            status=STATUS_PENDING,
        )
    )


def _add_roundtrip_task(db: Session, batch: FlightQueryBatch, monitor: FlightMonitor, monitor_date) -> None:
    db.add(
        FlightQueryTask(
            scan_id=batch.scan_id,
            batch_no=batch.batch_no,
            monitor_id=monitor.id,
            depart_date=monitor_date.depart_date,
            return_date=monitor_date.return_date,
            trip_type=TRIP_ROUND_TRIP,
            query_type=QUERY_DIRECT,
            platform=monitor.platform,
            from_city=monitor.from_city,
            to_city=monitor.to_city,
            transfer_city=None,
            strategy_snapshot_json=_roundtrip_strategy_snapshot(monitor),
            data_completeness=COMPLETENESS_SNAPSHOT_ONLY,
            status=STATUS_PENDING,
        )
    )


def generate_tasks_for_monitors(
    db: Session,
    monitors: list[FlightMonitor],
    scan_id: int | None = None,
    trigger_type: str = TRIGGER_SCAN,
) -> tuple[FlightQueryBatch, int, list[str]]:
    batch = FlightQueryBatch(
        batch_no=make_batch_no(),
        scan_id=scan_id,
        trigger_type=trigger_type,
        status=STATUS_PENDING,
        start_time=datetime.now(),
    )
    db.add(batch)
    db.flush()

    task_count = 0
    warnings: list[str] = []
    for monitor in monitors:
        dates = enabled_dates_for_monitor(db, monitor.id)
        if not dates:
            warnings.append(f"Monitor {monitor.id} has no enabled depart dates; no tasks generated")
            continue
        if monitor.allow_hidden_city:
            warnings.append(
                f"Monitor {monitor.id} has allow_hidden_city=true but hidden-city route modeling is not implemented; skipped HIDDEN_CITY tasks"
            )
        if monitor.trip_type != TRIP_ROUND_TRIP and not (
            monitor.allow_direct or monitor.allow_transfer or monitor.allow_train_positioning
        ):
            warnings.append(
                f"Monitor {monitor.id} has no implemented query strategy enabled; no tasks can be generated"
            )
            continue
        for monitor_date in dates:
            if monitor.trip_type == TRIP_ROUND_TRIP:
                if not monitor_date.return_date:
                    warnings.append(
                        f"Monitor {monitor.id} is ROUND_TRIP but date {monitor_date.depart_date} has no return_date; skipped task"
                    )
                    continue
                if monitor.allow_transfer or monitor.allow_train_positioning:
                    warnings.append(
                        f"Monitor {monitor.id} is ROUND_TRIP; transfer and train positioning task generation is deferred, generated DIRECT round-trip only"
                    )
                _add_roundtrip_task(db, batch, monitor, monitor_date)
                task_count += 1
                continue

            for query_type in _query_types(monitor):
                _add_oneway_task(db, batch, monitor, monitor_date.depart_date, query_type)
                task_count += 1
            if monitor.allow_transfer:
                transfers = enabled_transfers(db, monitor.id)
                if not transfers:
                    warnings.append(
                        f"Monitor {monitor.id} has allow_transfer=true but no enabled transfer city; generated generic TRANSFER task"
                    )
                    _add_oneway_task(db, batch, monitor, monitor_date.depart_date, QUERY_TRANSFER)
                    task_count += 1
                for transfer in transfers:
                    _add_oneway_task(
                        db,
                        batch,
                        monitor,
                        monitor_date.depart_date,
                        QUERY_TRANSFER,
                        transfer_city=transfer.transfer_city,
                    )
                    task_count += 1
            if monitor.allow_train_positioning:
                positionings = enabled_positionings(db, monitor.id)
                if not positionings:
                    warnings.append(f"Monitor {monitor.id} has allow_train_positioning=true but no enabled positioning city")
                for positioning in positionings:
                    _add_oneway_task(
                        db,
                        batch,
                        monitor,
                        monitor_date.depart_date,
                        QUERY_TRAIN_PLUS_FLIGHT,
                        from_city=positioning.positioning_city,
                    )
                    task_count += 1

    batch.total_task_count = task_count
    if task_count == 0:
        batch.status = STATUS_SKIPPED
        batch.end_time = datetime.now()
    db.commit()
    db.refresh(batch)
    return batch, task_count, warnings
