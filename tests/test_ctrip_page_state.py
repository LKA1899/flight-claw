import unittest

from app.constants import PAGE_LOGIN_REQUIRED, PAGE_VERIFICATION_REQUIRED
from app.crawler.ctrip import _classify_visible_text


class CtripPageStateTest(unittest.TestCase):
    def test_classifies_whaleguard_block_as_verification_required(self) -> None:
        self.assertEqual(_classify_visible_text("whaleguard block"), PAGE_VERIFICATION_REQUIRED)

    def test_classifies_short_block_page_as_verification_required(self) -> None:
        self.assertEqual(_classify_visible_text("request blocked"), PAGE_VERIFICATION_REQUIRED)

    def test_empty_login_modal_is_login_required(self) -> None:
        self.assertEqual(_classify_visible_text("", login_modal=True), PAGE_LOGIN_REQUIRED)

    def test_empty_non_login_page_is_unknown(self) -> None:
        self.assertIsNone(_classify_visible_text(""))


if __name__ == "__main__":
    unittest.main()
