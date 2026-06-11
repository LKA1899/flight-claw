import unittest
from unittest.mock import patch

from app.crawler.browser_engine import BrowserProfile


class BrowserProfileUserAgentTest(unittest.TestCase):
    def _build_settings(self, **overrides) -> dict:
        settings = {
            "fingerprint_pool_enabled": True,
            "fingerprint_mode": "fixed",
            "fingerprint_profile_strategy": "pool",
            "browser_session_mode": "persistent",
            "browser_fallback_mode": "isolated_ephemeral",
            "locale": "zh-CN",
            "timezone_id": "Asia/Shanghai",
            "viewport_width": 1440,
            "viewport_height": 900,
            "device_scale_factor": 1.0,
            "user_agent": "",
            "force_fingerprint_user_agent": False,
            "extra_headers": {},
            "block_resource_types": [],
            "blocked_domains": [],
            "capture_xhr_enabled": True,
            "capture_xhr_pattern": "flight|search|price|list|ota|batch",
        }
        settings.update(overrides)
        return settings

    @patch("app.crawler.browser_engine.get_browser_profile_settings")
    def test_defaults_to_fingerprint_user_agent_when_no_override(self, mock_get_settings) -> None:
        mock_get_settings.return_value = self._build_settings()

        profile = BrowserProfile.from_settings(headless=True, task_id=1)

        self.assertIsNotNone(profile.user_agent)
        self.assertIn("Mozilla/5.0", profile.user_agent)

    @patch("app.crawler.browser_engine.get_browser_profile_settings")
    def test_prefers_configured_user_agent_without_force_flag(self, mock_get_settings) -> None:
        mock_get_settings.return_value = self._build_settings(user_agent="custom-agent/1.0")

        profile = BrowserProfile.from_settings(headless=True, task_id=1)

        self.assertEqual(profile.user_agent, "custom-agent/1.0")

    @patch("app.crawler.browser_engine.get_browser_profile_settings")
    def test_force_flag_overrides_configured_user_agent(self, mock_get_settings) -> None:
        mock_get_settings.return_value = self._build_settings(
            user_agent="custom-agent/1.0",
            force_fingerprint_user_agent=True,
        )

        profile = BrowserProfile.from_settings(headless=True, task_id=1)

        self.assertNotEqual(profile.user_agent, "custom-agent/1.0")
        self.assertIsNotNone(profile.user_agent)
        self.assertIn("Mozilla/5.0", profile.user_agent)


if __name__ == "__main__":
    unittest.main()
