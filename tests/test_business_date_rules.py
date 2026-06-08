import unittest
from datetime import date, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.constants import QUERY_DIRECT, TRIP_ONE_WAY, TRIP_ROUND_TRIP
from app.db import Base
from app.models import FlightMonitor, FlightMonitorDate, FlightQueryTask
from app.routers.api import DatePayload
from app.services import date_service
from app.services.task_service import generate_tasks_for_monitors


class BusinessDateRuleTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:", future=True)
        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _create_monitor(self, trip_type: str) -> FlightMonitor:
        monitor = FlightMonitor(
            monitor_name=f"monitor-{trip_type}",
            from_city="SHA",
            to_city="BKK",
            platform="CTRIP",
            trip_type=trip_type,
            allow_direct=True,
            allow_transfer=False,
            allow_train_positioning=False,
            allow_hidden_city=False,
            enabled=True,
            create_time=datetime.now(),
            update_time=datetime.now(),
        )
        self.db.add(monitor)
        self.db.commit()
        self.db.refresh(monitor)
        return monitor

    def test_date_payload_rejects_return_before_depart(self):
        with self.assertRaises(ValueError):
            DatePayload(depart_date=date(2026, 6, 10), return_date=date(2026, 6, 9))

    def test_add_date_rejects_oneway_return_date(self):
        monitor = self._create_monitor(TRIP_ONE_WAY)
        with self.assertRaisesRegex(ValueError, "One-way monitor dates cannot include return_date"):
            date_service.add_date(
                self.db,
                monitor.id,
                depart_date=date(2026, 6, 10),
                return_date=date(2026, 6, 12),
            )

    def test_add_date_rejects_roundtrip_without_return_date(self):
        monitor = self._create_monitor(TRIP_ROUND_TRIP)
        with self.assertRaisesRegex(ValueError, "Round-trip monitor dates require return_date"):
            date_service.add_date(self.db, monitor.id, depart_date=date(2026, 6, 10))

    def test_batch_roundtrip_dates_skip_invalid_return_before_depart(self):
        monitor = self._create_monitor(TRIP_ROUND_TRIP)
        created, skipped = date_service.batch_add_dates(
            self.db,
            monitor.id,
            start_date=date(2026, 6, 10),
            end_date=date(2026, 6, 11),
            weekdays=set(),
            return_start_date=date(2026, 6, 9),
            return_end_date=date(2026, 6, 11),
        )
        self.assertEqual((created, skipped), (3, 3))
        rows = self.db.query(FlightMonitorDate).all()
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row.return_date >= row.depart_date for row in rows if row.return_date is not None))

    def test_generate_tasks_dedupes_dirty_oneway_dates(self):
        monitor = self._create_monitor(TRIP_ONE_WAY)
        self.db.add_all(
            [
                FlightMonitorDate(
                    monitor_id=monitor.id,
                    depart_date=date(2026, 6, 10),
                    return_date=None,
                    enabled=True,
                    create_time=datetime.now(),
                    update_time=datetime.now(),
                ),
                FlightMonitorDate(
                    monitor_id=monitor.id,
                    depart_date=date(2026, 6, 10),
                    return_date=date(2026, 6, 12),
                    enabled=True,
                    create_time=datetime.now(),
                    update_time=datetime.now(),
                ),
            ]
        )
        self.db.commit()

        batch, task_count, warnings = generate_tasks_for_monitors(self.db, [monitor])

        self.assertEqual(task_count, 1)
        tasks = self.db.query(FlightQueryTask).filter(FlightQueryTask.batch_no == batch.batch_no).all()
        self.assertEqual(len(tasks), 1)
        self.assertEqual(tasks[0].query_type, QUERY_DIRECT)
        self.assertTrue(any("duplicate one-way date rows" in warning for warning in warnings))


if __name__ == "__main__":
    unittest.main()
