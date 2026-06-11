import unittest

from app.crawler.ctrip import _should_warm_up_session
from app.services.settings_service import DEFAULTS


class CtripWarmupTest(unittest.TestCase):
    def test_warmup_is_disabled_by_default(self) -> None:
        self.assertFalse(DEFAULTS["browser_profile"]["browser_warmup_enabled"])

    def test_missing_warmup_flag_defaults_to_disabled(self) -> None:
        self.assertFalse(_should_warm_up_session({}))

    def test_explicit_warmup_flag_enables_warmup(self) -> None:
        self.assertTrue(_should_warm_up_session({"browser_warmup_enabled": True}))


if __name__ == "__main__":
    unittest.main()
