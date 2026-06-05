from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)
(DATA_DIR / "screenshots").mkdir(exist_ok=True)
(DATA_DIR / "text").mkdir(exist_ok=True)
(DATA_DIR / "html").mkdir(exist_ok=True)
(DATA_DIR / "xhr").mkdir(exist_ok=True)
(DATA_DIR / "browser_profile" / "ctrip").mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{DATA_DIR / 'flight_claw.db'}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all() -> None:
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    ensure_runtime_schema()
    from app.services.city_code_service import seed_default_city_codes

    with SessionLocal() as db:
        seed_default_city_codes(db)


def ensure_runtime_schema() -> None:
    monitor_columns = {
        "trip_type": "VARCHAR(30) DEFAULT 'ONE_WAY' NOT NULL",
        "roundtrip_data_level": "VARCHAR(50) DEFAULT 'OUTBOUND_ONLY' NOT NULL",
        "roundtrip_expand_return": "BOOLEAN DEFAULT 0 NOT NULL",
        "roundtrip_outbound_expand_mode": "VARCHAR(50) DEFAULT 'NONE' NOT NULL",
        "roundtrip_expand_top_n": "INTEGER DEFAULT 3 NOT NULL",
        "roundtrip_expand_ranks": "VARCHAR(100)",
        "roundtrip_return_fetch_limit": "INTEGER DEFAULT 10 NOT NULL",
        "roundtrip_return_sort_strategy": "VARCHAR(50) DEFAULT 'LOW_PRICE' NOT NULL",
        "roundtrip_save_all_outbounds": "BOOLEAN DEFAULT 1 NOT NULL",
        "roundtrip_expand_only_priced": "BOOLEAN DEFAULT 1 NOT NULL",
        "roundtrip_skip_expand_over_budget": "BOOLEAN DEFAULT 0 NOT NULL",
        "continue_on_expand_failed": "BOOLEAN DEFAULT 1 NOT NULL",
        "save_step_snapshot": "BOOLEAN DEFAULT 1 NOT NULL",
        "schedule_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
        "schedule_cron": "VARCHAR(100)",
        "schedule_timezone": "VARCHAR(100) DEFAULT 'Asia/Shanghai' NOT NULL",
        "schedule_remark": "VARCHAR(500)",
        "last_scan_id": "INTEGER",
        "last_scan_time": "DATETIME",
        "last_scan_status": "VARCHAR(30)",
        "next_scan_time": "DATETIME",
    }
    monitor_date_columns = {
        "return_date": "DATE",
    }
    task_columns = {
        "scan_id": "INTEGER",
        "text_path": "VARCHAR(300)",
        "return_date": "DATE",
        "trip_type": "VARCHAR(30) DEFAULT 'ONE_WAY' NOT NULL",
        "parse_status": "VARCHAR(30)",
        "parse_error_message": "TEXT",
        "parsed_time": "DATETIME",
        "strategy_snapshot_json": "TEXT",
        "data_completeness": "VARCHAR(50)",
        "roundtrip_stage": "VARCHAR(50)",
    }
    price_raw_columns = {
        "trip_type": "VARCHAR(30) DEFAULT 'ONE_WAY' NOT NULL",
        "leg_type": "VARCHAR(30) DEFAULT 'OUTBOUND' NOT NULL",
        "return_date": "DATE",
        "price_type": "VARCHAR(50) DEFAULT 'ONE_WAY_PRICE' NOT NULL",
        "data_completeness": "VARCHAR(50)",
        "is_complete_plan": "BOOLEAN DEFAULT 1 NOT NULL",
    }
    with engine.begin() as conn:
        monitor_existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(flight_monitor)").fetchall()
        }
        for name, column_type in monitor_columns.items():
            if name not in monitor_existing:
                conn.exec_driver_sql(f"ALTER TABLE flight_monitor ADD COLUMN {name} {column_type}")

        date_existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(flight_monitor_date)").fetchall()
        }
        for name, column_type in monitor_date_columns.items():
            if name not in date_existing:
                conn.exec_driver_sql(f"ALTER TABLE flight_monitor_date ADD COLUMN {name} {column_type}")
        _ensure_monitor_date_indexes(conn)

        existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(flight_query_task)").fetchall()
        }
        for name, column_type in task_columns.items():
            if name not in existing:
                conn.exec_driver_sql(f"ALTER TABLE flight_query_task ADD COLUMN {name} {column_type}")

        price_existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(flight_price_raw)").fetchall()
        }
        for name, column_type in price_raw_columns.items():
            if name not in price_existing:
                conn.exec_driver_sql(f"ALTER TABLE flight_price_raw ADD COLUMN {name} {column_type}")

        plan_result_existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(flight_plan_result)").fetchall()
        }
        plan_result_columns = {
            "trip_type": "VARCHAR(30) DEFAULT 'ONE_WAY' NOT NULL",
            "return_date": "DATE",
        }
        for name, column_type in plan_result_columns.items():
            if name not in plan_result_existing:
                conn.exec_driver_sql(f"ALTER TABLE flight_plan_result ADD COLUMN {name} {column_type}")

        report_existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(flight_report)").fetchall()
        }
        report_columns = {
            "scan_id": "INTEGER",
            "monitor_id": "INTEGER",
            "llm_content_md": "TEXT",
            "llm_enabled": "BOOLEAN DEFAULT 0 NOT NULL",
            "llm_error_message": "TEXT",
        }
        for name, column_type in report_columns.items():
            if name not in report_existing:
                conn.exec_driver_sql(f"ALTER TABLE flight_report ADD COLUMN {name} {column_type}")

        batch_existing = {
            row[1]
            for row in conn.exec_driver_sql("PRAGMA table_info(flight_query_batch)").fetchall()
        }
        batch_columns = {
            "scan_id": "INTEGER",
        }
        for name, column_type in batch_columns.items():
            if name not in batch_existing:
                conn.exec_driver_sql(f"ALTER TABLE flight_query_batch ADD COLUMN {name} {column_type}")

        _ensure_monitor_limits_nullable(conn)
        _ensure_oneway_default_strategy(conn)
        _ensure_task_artifact_table(conn)


def _ensure_task_artifact_table(conn) -> None:
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS flight_task_artifact (
            id INTEGER NOT NULL PRIMARY KEY,
            task_id INTEGER NOT NULL,
            stage VARCHAR(80) NOT NULL,
            artifact_type VARCHAR(30) NOT NULL,
            path VARCHAR(500) NOT NULL,
            label VARCHAR(120),
            meta_json TEXT,
            create_time DATETIME NOT NULL,
            FOREIGN KEY(task_id) REFERENCES flight_query_task (id)
        )
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_flight_task_artifact_task_id
        ON flight_task_artifact (task_id)
        """
    )
    conn.exec_driver_sql(
        """
        CREATE INDEX IF NOT EXISTS ix_task_artifact_task_stage_type
        ON flight_task_artifact (task_id, stage, artifact_type)
        """
    )


def _ensure_monitor_date_indexes(conn) -> None:
    indexes = conn.exec_driver_sql("PRAGMA index_list(flight_monitor_date)").fetchall()
    has_old_unique = any(row[1] == "sqlite_autoindex_flight_monitor_date_1" or row[1] == "uq_monitor_depart_date" for row in indexes)
    has_new_oneway = any(row[1] == "uq_monitor_oneway_depart_date" for row in indexes)
    has_new_roundtrip = any(row[1] == "uq_monitor_roundtrip_depart_return_date" for row in indexes)

    if has_old_unique and (not has_new_oneway or not has_new_roundtrip):
        conn.exec_driver_sql(
            """
            CREATE TABLE IF NOT EXISTS flight_monitor_date_new (
                id INTEGER NOT NULL PRIMARY KEY,
                monitor_id INTEGER NOT NULL,
                depart_date DATE NOT NULL,
                return_date DATE,
                enabled BOOLEAN NOT NULL DEFAULT 1,
                remark TEXT,
                create_time DATETIME NOT NULL,
                update_time DATETIME NOT NULL,
                FOREIGN KEY(monitor_id) REFERENCES flight_monitor (id)
            )
            """
        )
        conn.exec_driver_sql(
            """
            INSERT INTO flight_monitor_date_new (
                id, monitor_id, depart_date, return_date, enabled, remark, create_time, update_time
            )
            SELECT id, monitor_id, depart_date, return_date, enabled, remark, create_time, update_time
            FROM flight_monitor_date
            """
        )
        conn.exec_driver_sql("DROP TABLE flight_monitor_date")
        conn.exec_driver_sql("ALTER TABLE flight_monitor_date_new RENAME TO flight_monitor_date")
        indexes = []

    if not any(row[1] == "uq_monitor_oneway_depart_date" for row in indexes):
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_monitor_oneway_depart_date
            ON flight_monitor_date (monitor_id, depart_date)
            WHERE return_date IS NULL
            """
        )
    if not any(row[1] == "uq_monitor_roundtrip_depart_return_date" for row in indexes):
        conn.exec_driver_sql(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_monitor_roundtrip_depart_return_date
            ON flight_monitor_date (monitor_id, depart_date, return_date)
            WHERE return_date IS NOT NULL
            """
        )


def _ensure_monitor_limits_nullable(conn) -> None:
    columns = conn.exec_driver_sql("PRAGMA table_info(flight_monitor)").fetchall()
    max_transfer_column = next((row for row in columns if row[1] == "max_transfer_count"), None)
    if not max_transfer_column or not max_transfer_column[3]:
        return
    conn.exec_driver_sql(
        """
        CREATE TABLE IF NOT EXISTS flight_monitor_new (
            id INTEGER NOT NULL PRIMARY KEY,
            monitor_name VARCHAR(200) NOT NULL,
            from_city VARCHAR(80) NOT NULL,
            from_airports VARCHAR(200),
            to_city VARCHAR(80) NOT NULL,
            to_airports VARCHAR(200),
            platform VARCHAR(30) NOT NULL DEFAULT 'CTRIP',
            trip_type VARCHAR(30) NOT NULL DEFAULT 'ONE_WAY',
            allow_direct BOOLEAN NOT NULL DEFAULT 1,
            allow_transfer BOOLEAN NOT NULL DEFAULT 0,
            allow_train_positioning BOOLEAN NOT NULL DEFAULT 0,
            allow_hidden_city BOOLEAN NOT NULL DEFAULT 0,
            max_transfer_count INTEGER,
            max_total_hours INTEGER,
            max_price FLOAT,
            roundtrip_data_level VARCHAR(50) NOT NULL DEFAULT 'OUTBOUND_ONLY',
            roundtrip_expand_return BOOLEAN NOT NULL DEFAULT 0,
            roundtrip_outbound_expand_mode VARCHAR(50) NOT NULL DEFAULT 'NONE',
            roundtrip_expand_top_n INTEGER NOT NULL DEFAULT 3,
            roundtrip_expand_ranks VARCHAR(100),
            roundtrip_return_fetch_limit INTEGER NOT NULL DEFAULT 10,
            roundtrip_return_sort_strategy VARCHAR(50) NOT NULL DEFAULT 'LOW_PRICE',
            roundtrip_save_all_outbounds BOOLEAN NOT NULL DEFAULT 1,
            roundtrip_expand_only_priced BOOLEAN NOT NULL DEFAULT 1,
            roundtrip_skip_expand_over_budget BOOLEAN NOT NULL DEFAULT 0,
            continue_on_expand_failed BOOLEAN NOT NULL DEFAULT 1,
            save_step_snapshot BOOLEAN NOT NULL DEFAULT 1,
            schedule_enabled BOOLEAN NOT NULL DEFAULT 0,
            schedule_cron VARCHAR(100),
            schedule_timezone VARCHAR(100) NOT NULL DEFAULT 'Asia/Shanghai',
            schedule_remark VARCHAR(500),
            last_scan_id INTEGER,
            last_scan_time DATETIME,
            last_scan_status VARCHAR(30),
            next_scan_time DATETIME,
            enabled BOOLEAN NOT NULL DEFAULT 1,
            remark TEXT,
            create_time DATETIME NOT NULL,
            update_time DATETIME NOT NULL
        )
        """
    )
    conn.exec_driver_sql(
        """
        INSERT INTO flight_monitor_new (
            id, monitor_name, from_city, from_airports, to_city, to_airports, platform,
            trip_type, allow_direct, allow_transfer, allow_train_positioning, allow_hidden_city,
            max_transfer_count, max_total_hours, max_price, roundtrip_data_level,
            roundtrip_expand_return, roundtrip_outbound_expand_mode, roundtrip_expand_top_n,
            roundtrip_expand_ranks, roundtrip_return_fetch_limit, roundtrip_return_sort_strategy,
            roundtrip_save_all_outbounds, roundtrip_expand_only_priced, roundtrip_skip_expand_over_budget,
            continue_on_expand_failed, save_step_snapshot,
            schedule_enabled, schedule_cron, schedule_timezone, schedule_remark,
            last_scan_id, last_scan_time, last_scan_status, next_scan_time,
            enabled, remark, create_time, update_time
        )
        SELECT
            id, monitor_name, from_city, from_airports, to_city, to_airports, platform,
            trip_type, allow_direct, allow_transfer, allow_train_positioning, allow_hidden_city,
            max_transfer_count, max_total_hours, max_price, roundtrip_data_level,
            roundtrip_expand_return, roundtrip_outbound_expand_mode, roundtrip_expand_top_n,
            roundtrip_expand_ranks, roundtrip_return_fetch_limit, roundtrip_return_sort_strategy,
            roundtrip_save_all_outbounds, roundtrip_expand_only_priced, roundtrip_skip_expand_over_budget,
            continue_on_expand_failed, save_step_snapshot,
            schedule_enabled, schedule_cron, schedule_timezone, schedule_remark,
            last_scan_id, last_scan_time, last_scan_status, next_scan_time,
            enabled, remark, create_time, update_time
        FROM flight_monitor
        """
    )
    conn.exec_driver_sql("DROP TABLE flight_monitor")
    conn.exec_driver_sql("ALTER TABLE flight_monitor_new RENAME TO flight_monitor")


def _ensure_oneway_default_strategy(conn) -> None:
    conn.exec_driver_sql(
        """
        UPDATE flight_monitor
        SET allow_direct = 1
        WHERE trip_type = 'ONE_WAY'
          AND allow_direct = 0
          AND allow_transfer = 0
          AND allow_train_positioning = 0
        """
    )
