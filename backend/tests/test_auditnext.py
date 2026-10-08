"""AuditNext: expected information gain per hour, region-aware and read-only.

    python -m unittest discover -s backend/tests -t .
"""
import unittest

from fastapi.testclient import TestClient

from backend import region
from backend.app import store
from backend.app.main import app
from backend.brain import auditnext


class Math(unittest.TestCase):
    def test_information_gain_bounds(self):
        self.assertAlmostEqual(auditnext.expected_gain(0.5, 1.0), 1.0)  # a perfect test removes all uncertainty
        self.assertAlmostEqual(auditnext.expected_gain(0.5, 0.5), 0.0)  # a coin flip tells nothing
        for p in (0.05, 0.3, 0.7, 0.95):
            for acc in (0.6, 0.8, 0.95):
                self.assertLessEqual(auditnext.expected_gain(p, acc), auditnext.shannon_entropy(p) + 1e-9)

    def test_actions_are_ranked_by_gain_per_hour(self):
        plan = auditnext.plan_investigation(0.6, "upcoding")
        scores = [a["utility_score"] for a in plan["actions"]]
        self.assertEqual(scores, sorted(scores, reverse=True))
        self.assertEqual(sum(a["is_optimal"] for a in plan["actions"]), 1)
        self.assertIn("illustrative assumptions", plan["assumptions"])


class Route(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_prior_is_the_case_confidence(self):
        body = self.client.get("/api/cases/CASE-P209/audit-plan?region=us").json()
        with region.use("us"):
            _, conf, _ = store.enrich(store.data().CASES["CASE-P209"])
        self.assertEqual(body["prior_probability"], round(max(0.01, min(0.99, conf["score"])), 3))
        self.assertEqual(body["pattern_type"], "impossible_timing")

    def test_india_is_unavailable_and_unknown_cases_404(self):
        self.assertEqual(self.client.get("/api/cases/CASE-P104/audit-plan?region=in").json()["status"], "unavailable")
        self.assertEqual(self.client.get("/api/cases/P209/audit-plan?region=us").status_code, 404)  # no fuzzy matching
        self.assertEqual(self.client.get("/api/cases/CASE-P209/audit-plan?region=in").status_code, 404)


if __name__ == "__main__":
    unittest.main()
