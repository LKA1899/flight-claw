import sys
import unittest

from app.crawler.fingerprint_pool import select_browser_fingerprint


class FingerprintPoolTest(unittest.TestCase):
    def test_windows_runtime_uses_windows_fingerprint(self) -> None:
        fingerprint = select_browser_fingerprint(
            mode="per_monitor_daily",
            task_id=397,
            monitor_id=10,
            date_bucket="2026-06-09",
            penalty_index=0,
        )

        if sys.platform == "win32":
            self.assertTrue(fingerprint.name.startswith("win_"))
            self.assertIn("Windows NT", fingerprint.user_agent)


if __name__ == "__main__":
    unittest.main()
