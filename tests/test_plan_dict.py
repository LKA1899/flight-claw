import json
import unittest
from datetime import date, datetime
from types import SimpleNamespace

from app.routers.api import plan_dict


class PlanDictTest(unittest.TestCase):
    def test_one_way_plan_includes_depart_and_arrive_time(self) -> None:
        item = SimpleNamespace(
            id=1,
            batch_no="B1",
            monitor_id=10,
            monitor=SimpleNamespace(monitor_name="测试路线", from_city="北京", to_city="昆明"),
            depart_date=date(2026, 6, 20),
            return_date=None,
            trip_type="ONE_WAY",
            plan_type="DIRECT",
            title="DIRECT · 北京 → 昆明",
            total_price=520.0,
            currency="CNY",
            total_duration_minutes=210,
            transfer_count=0,
            risk_level="LOW",
            score=92.5,
            reason="test",
            warning=None,
            create_time=datetime(2026, 6, 11, 10, 0, 0),
            detail_json=json.dumps(
                {
                    "airline": "东方航空",
                    "flight_no": "MU1234",
                    "depart_time": "08:30",
                    "arrive_time": "12:05",
                    "depart_airport": "大兴机场",
                    "arrive_airport": "长水机场",
                },
                ensure_ascii=False,
            ),
        )

        result = plan_dict(item)

        self.assertEqual(result["airline"], "东方航空")
        self.assertEqual(result["flight_no"], "MU1234")
        self.assertEqual(result["depart_time"], "08:30")
        self.assertEqual(result["arrive_time"], "12:05")
        self.assertEqual(result["depart_airport"], "大兴机场")
        self.assertEqual(result["arrive_airport"], "长水机场")

    def test_roundtrip_plan_includes_outbound_and_return_times(self) -> None:
        item = SimpleNamespace(
            id=2,
            batch_no="B2",
            monitor_id=11,
            monitor=SimpleNamespace(monitor_name="测试往返", from_city="北京", to_city="昆明"),
            depart_date=date(2026, 6, 20),
            return_date=date(2026, 6, 25),
            trip_type="ROUND_TRIP",
            plan_type="ROUNDTRIP_TICKET",
            title="ROUNDTRIP_TICKET",
            total_price=1280.0,
            currency="CNY",
            total_duration_minutes=520,
            transfer_count=0,
            risk_level="LOW",
            score=95.0,
            reason="test",
            warning=None,
            create_time=datetime(2026, 6, 11, 10, 0, 0),
            detail_json=json.dumps(
                {
                    "outbound_summary": "MU1234 08:30-12:05",
                    "return_summary": "MU5678 18:20-22:10",
                    "outbound_airline": "东方航空",
                    "outbound_flight_no": "MU1234",
                    "outbound_depart_time": "08:30",
                    "outbound_arrive_time": "12:05",
                    "outbound_depart_airport": "大兴机场",
                    "outbound_arrive_airport": "长水机场",
                    "return_airline": "东方航空",
                    "return_flight_no": "MU5678",
                    "return_depart_time": "18:20",
                    "return_arrive_time": "22:10",
                    "return_depart_airport": "长水机场",
                    "return_arrive_airport": "大兴机场",
                    "data_completeness": "FULL_ROUND_TRIP",
                    "roundtrip_plan_id": 200,
                },
                ensure_ascii=False,
            ),
        )

        result = plan_dict(item)

        self.assertEqual(result["outbound_depart_time"], "08:30")
        self.assertEqual(result["outbound_arrive_time"], "12:05")
        self.assertEqual(result["return_depart_time"], "18:20")
        self.assertEqual(result["return_arrive_time"], "22:10")
        self.assertEqual(result["outbound_depart_airport"], "大兴机场")
        self.assertEqual(result["return_arrive_airport"], "大兴机场")


if __name__ == "__main__":
    unittest.main()
