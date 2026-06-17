from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class FrontendAuthFlowTests(unittest.TestCase):
    def test_login_success_refreshes_auth_query_before_redirect(self):
        source = (ROOT / "frontend" / "src" / "pages" / "auth" / "LoginPage.tsx").read_text(encoding="utf-8")

        self.assertIn("useQueryClient", source)
        self.assertIn('setQueryData(["auth-me"]', source)
        self.assertIn('invalidateQueries({ queryKey: ["auth-me"] })', source)

    def test_frontend_env_example_uses_same_origin_proxy_by_default(self):
        source = (ROOT / "frontend" / ".env.example").read_text(encoding="utf-8")

        self.assertNotIn("VITE_API_BASE_URL=http://localhost:8000", source)
        self.assertIn("# VITE_API_BASE_URL=", source)


if __name__ == "__main__":
    unittest.main()
