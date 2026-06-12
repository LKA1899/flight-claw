import unittest

from app.routers.api import prioritize_plan_dicts


class PlanListOrderingTest(unittest.TestCase):
    def test_prioritize_plan_dicts_sorts_by_price_after_dedupe(self) -> None:
        items = [
            {"id": 1, "monitor_id": 10, "source_type": "ONE_WAY_PLAN", "depart_date": "2026-06-20", "return_date": None, "flight_no": "MU100", "depart_time": "08:00", "arrive_time": "10:00", "depart_airport": "PKX", "arrive_airport": "KMG", "total_price": 500, "score": 80},
            {"id": 2, "monitor_id": 11, "source_type": "ONE_WAY_PLAN", "depart_date": "2026-06-21", "return_date": None, "flight_no": "MU200", "depart_time": "09:00", "arrive_time": "11:00", "depart_airport": "PKX", "arrive_airport": "CAN", "total_price": 340, "score": 90},
            {"id": 3, "monitor_id": 10, "source_type": "ONE_WAY_PLAN", "depart_date": "2026-06-20", "return_date": None, "flight_no": "MU100", "depart_time": "08:00", "arrive_time": "10:00", "depart_airport": "PKX", "arrive_airport": "KMG", "total_price": 520, "score": 95},
        ]

        result = prioritize_plan_dicts(items)

        self.assertEqual([item["id"] for item in result], [2, 3])


if __name__ == "__main__":
    unittest.main()
