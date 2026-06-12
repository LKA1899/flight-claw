import unittest
from datetime import datetime
from types import SimpleNamespace

from app.routers.api import scan_option_dict


class ScanOptionsTest(unittest.TestCase):
    def test_scan_option_dict_uses_short_route_scan_label(self) -> None:
        scan = SimpleNamespace(
            id=42,
            scan_no="S202606120930000000",
            batch_no="B202606120930000000",
            monitor_id=7,
            monitor=SimpleNamespace(monitor_name="SHA-BKK", from_city="上海", to_city="曼谷"),
            trigger_type="MANUAL",
            status="SUCCESS",
            total_task_count=12,
            success_task_count=11,
            failed_task_count=1,
            start_time=datetime(2026, 6, 12, 9, 30),
            create_time=datetime(2026, 6, 12, 9, 29),
        )

        result = scan_option_dict(scan)

        self.assertEqual(result["scan_id"], 42)
        self.assertEqual(result["batch_no"], "B202606120930000000")
        self.assertEqual(result["monitor_id"], 7)
        self.assertEqual(result["route_label"], "SHA-BKK / 上海 -> 曼谷")
        self.assertEqual(result["label"], "2026-06-12 09:30 · 手动 · 成功 · 11/12")
        self.assertNotIn("B202606120930000000", result["label"])


if __name__ == "__main__":
    unittest.main()
