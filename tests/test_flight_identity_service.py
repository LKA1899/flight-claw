import json
import unittest
from datetime import date
from types import SimpleNamespace

from app.services.flight_identity_service import (
    dedupe_plan_results,
    plan_flight_identity_key,
    price_flight_identity_key,
)


class FlightIdentityServiceTest(unittest.TestCase):
    def test_price_identity_does_not_include_price_or_task(self) -> None:
        base = {
            "monitor_id": 10,
            "platform": "CTRIP",
            "trip_type": "ONE_WAY",
            "leg_type": "OUTBOUND",
            "query_type": "DIRECT",
            "depart_date": date(2026, 6, 20),
            "return_date": None,
            "from_city": "北京",
            "to_city": "昆明",
            "flight_no": "MU1234",
            "depart_time": "08:30",
            "arrive_time": "12:05",
            "depart_airport": "大兴机场",
            "arrive_airport": "长水机场",
            "transfer_count": 0,
            "transfer_city": None,
        }
        first = SimpleNamespace(**base, id=1, task_id=100, price=620)
        second = SimpleNamespace(**base, id=2, task_id=101, price=580)

        self.assertEqual(price_flight_identity_key(first), price_flight_identity_key(second))

    def test_plan_dedupe_keeps_better_same_flight_instance(self) -> None:
        detail = {
            "flight_no": "MU1234",
            "depart_time": "08:30",
            "arrive_time": "12:05",
            "depart_airport": "大兴机场",
            "arrive_airport": "长水机场",
        }
        expensive = SimpleNamespace(
            id=1,
            monitor_id=10,
            depart_date=date(2026, 6, 20),
            return_date=None,
            plan_type="DIRECT",
            score=80,
            total_price=680,
            detail_json=json.dumps(detail, ensure_ascii=False),
        )
        cheaper = SimpleNamespace(
            id=2,
            monitor_id=10,
            depart_date=date(2026, 6, 20),
            return_date=None,
            plan_type="DIRECT",
            score=90,
            total_price=580,
            detail_json=json.dumps(detail, ensure_ascii=False),
        )

        self.assertEqual(plan_flight_identity_key(expensive), plan_flight_identity_key(cheaper))
        self.assertEqual(dedupe_plan_results([expensive, cheaper]), [cheaper])


if __name__ == "__main__":
    unittest.main()
