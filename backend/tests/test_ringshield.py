import unittest

import pandas as pd

from backend.pipeline import ringshield


def fixture():
    members = ["A", "B", "C", "D"]
    edges = pd.DataFrame(
        [
            {"a": a, "b": b, "shared": 20, "lift": 4.0}
            for index, a in enumerate(members)
            for b in members[index + 1 :]
        ]
    )
    claims = pd.DataFrame(
        [
            {"provider_id": provider, "member_id": f"M-{provider}-{index}", "referred_by_agent_id": "AG-1"}
            for provider in members
            for index in range(5)
        ]
    )
    providers = pd.DataFrame(
        [{"provider_id": provider, "owner_id": "OWN-1"} for provider in members]
        + [{"provider_id": "E", "owner_id": "OWN-2"}]
    )
    referral_rows = []
    for source, target in zip(members, members[1:] + members[:1]):
        referral_rows.extend(
            {"from_provider_id": source, "to_provider_id": target, "member_id": f"R-{source}-{i}"}
            for i in range(15)
        )
    return members, edges, claims, providers, pd.DataFrame(referral_rows)


class RingShieldEngine(unittest.TestCase):
    def test_deterministic_and_separates_topology_from_corroboration(self):
        inputs = fixture()
        first = ringshield.evaluate_network("N-test", *inputs, trials=6)
        second = ringshield.evaluate_network("N-test", *inputs, trials=6)
        self.assertEqual(first, second)
        self.assertGreater(first["robustness_score"], 0)
        by_type = {row["relationship_type"]: row for row in first["exclusion_sensitivity"]}
        self.assertTrue(by_type["shared_beneficiaries"]["topology_affected"])
        for relationship in ("shared_agents", "referrals", "common_ownership", "administrative_hubs"):
            self.assertFalse(by_type[relationship]["topology_affected"])
            self.assertEqual(by_type[relationship]["membership_stability"], first["stability"]["mean_stability"])

    def test_small_network_and_missing_evidence_are_safe(self):
        result = ringshield.evaluate_network(
            "N-small",
            ["A", "B"],
            pd.DataFrame(columns=["a", "b", "shared", "lift"]),
            pd.DataFrame([{"provider_id": "A", "member_id": "M1"}]),
            pd.DataFrame(columns=["provider_id", "owner_id"]),
            pd.DataFrame(),
        )
        self.assertEqual(result["stability"]["mean_stability"], 0.0)
        self.assertTrue(any("Small networks" in item for item in result["limitations"]))
        agents = next(row for row in result["evidence_family_contributions"] if row["relationship_type"] == "shared_agents")
        self.assertFalse(agents["available"])

    def test_detector_evaluation_reports_exact_and_false_networks_without_tuning(self):
        scores = pd.DataFrame(
            {"cluster_id": ["N01", "N01", "N02", ""]}, index=["A", "B", "X", "Y"]
        )
        truth = pd.DataFrame(
            [
                {"provider_id": "A", "pattern": "collusive_ring"},
                {"provider_id": "B", "pattern": "collusive_ring"},
            ]
        )
        result = ringshield.detector_evaluation(scores, truth)
        self.assertTrue(result["exact_recovery"])
        self.assertEqual(result["precision"], 1.0)
        self.assertEqual(result["recall"], 1.0)
        self.assertEqual(result["false_ring_alerts"], 1)


if __name__ == "__main__":
    unittest.main()
