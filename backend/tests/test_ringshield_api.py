import unittest

from fastapi.testclient import TestClient

from backend.app.main import app


class RingShieldApi(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_india_network_is_region_aware_and_read_only(self):
        response = self.client.get("/api/graph/P059/ringshield?region=in")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["network_id"], "N01")
        self.assertEqual(body["member_hospitals"], ["P022", "P059", "P148", "P152", "P203"])
        self.assertIn("robustness_score", body)
        self.assertTrue(all("topology_affected" in row for row in body["exclusion_sensitivity"]))

    def test_us_network_remains_available(self):
        response = self.client.get("/api/graph/P081/ringshield?region=us")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["network_id"], "N01")

    def test_non_network_provider_returns_404(self):
        response = self.client.get("/api/graph/P001/ringshield?region=in")
        self.assertEqual(response.status_code, 404)
        self.assertIn("not in a detected network", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
