import os
import unittest

from app import create_app


class TestCronKeepalive(unittest.TestCase):
    def setUp(self):
        self.app = create_app("testing")
        self.client = self.app.test_client()

    def test_ping_returns_200(self):
        resp = self.client.get("/ping")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["ok"])

    def test_keepalive_without_secret(self):
        resp = self.client.get("/cron/keepalive")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["purpose"], "keepalive")

    def test_keepalive_rejects_wrong_token_when_secret_set(self):
        self.app.config["CRON_SECRET"] = "test-cron-secret"
        resp = self.client.get("/cron/keepalive?token=wrong")
        self.assertEqual(resp.status_code, 401)

    def test_keepalive_accepts_token_query(self):
        self.app.config["CRON_SECRET"] = "test-cron-secret"
        resp = self.client.get("/cron/keepalive?token=test-cron-secret")
        self.assertEqual(resp.status_code, 200)

    def test_api_prefixed_keepalive_route(self):
        resp = self.client.get("/api/cron/keepalive")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["purpose"], "keepalive")


if __name__ == "__main__":
    unittest.main()
