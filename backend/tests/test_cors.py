import unittest

from fastapi.testclient import TestClient

from app.main import app


class CorsMiddlewareTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_allows_frontend_development_origin(self) -> None:
        response = self.client.get(
            "/api/v1/health",
            headers={"Origin": "http://127.0.0.1:5173"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://127.0.0.1:5173",
        )

    def test_allows_preflight_request(self) -> None:
        response = self.client.options(
            "/api/v1/settings",
            headers={
                "Origin": "http://127.0.0.1:5173",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://127.0.0.1:5173",
        )
        self.assertIn("PUT", response.headers["access-control-allow-methods"])


if __name__ == "__main__":
    unittest.main()
