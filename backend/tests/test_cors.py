import unittest

from fastapi.testclient import TestClient

from app.main import app


class CorsTestCase(unittest.TestCase):
    def test_vite_loopback_origin_is_allowed(self) -> None:
        with TestClient(app) as client:
            response = client.options(
                "/api/v1/settings",
                headers={
                    "Origin": "http://127.0.0.1:5173",
                    "Access-Control-Request-Method": "GET",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers["access-control-allow-origin"],
            "http://127.0.0.1:5173",
        )


if __name__ == "__main__":
    unittest.main()
