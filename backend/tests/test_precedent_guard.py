"""PrecedentGuard checks on hand-built precedents.

    python -m unittest discover -s backend/tests -t .
"""
import datetime as dt
import unittest

from backend.brain import confidence

TODAY = str(dt.date.today())


def case(**kw):
    return {"case_id": "CASE-X", "provider_id": "P1", "pattern": "collusive_ring", "evidence_strength": 0.5,
            "signals": {"graph": 1.0}, "rule_counts": {}, "network": {"cluster_id": "N01"}, **kw}


def prec(cid, verdict, provider="P2", evidence=None, closed=TODAY, network="N01"):
    return {"case_id": cid, "provider_id": provider, "pattern": "collusive_ring", "verdict": verdict, "closed": closed,
            "network": network, "evidence": evidence, "similarity": 1.0, "why": ["same network N01"]}


class Guard(unittest.TestCase):
    def test_contradicting_network_verdicts_cancel(self):
        precs = [prec("A", "confirmed"), prec("B", "cleared", provider="P3")]
        on, off = confidence.score(case(), precs, guard=True), confidence.score(case(), precs, guard=False)
        self.assertEqual(on["contradictions"], ["A", "B"])
        self.assertEqual(on["precedent_adjustment"], 0)
        self.assertNotEqual(off["precedent_adjustment"], 0)

    def test_network_bonus_needs_shared_evidence(self):
        rules_only = [prec("A", "confirmed", evidence=["R4 unit limit (MUE)"])]
        self.assertAlmostEqual(confidence.score(case(), rules_only, guard=False)["precedent_adjustment"], 0.25)
        self.assertAlmostEqual(confidence.score(case(), rules_only, guard=True)["precedent_adjustment"], 0.10)
        shared = [prec("A", "confirmed", evidence=["graph"])]
        self.assertAlmostEqual(confidence.score(case(), shared, guard=True)["precedent_adjustment"], 0.25)

    def test_old_precedent_weighs_half_per_half_life(self):
        old = str(dt.date.today() - dt.timedelta(days=confidence.HALF_LIFE_DAYS))
        self.assertAlmostEqual(confidence.score(case(), [prec("A", "confirmed", closed=old)], guard=True)
                               ["precedent_adjustment"], 0.125, places=3)

    def test_each_precedent_is_explained(self):
        old = str(dt.date.today() - dt.timedelta(days=confidence.HALF_LIFE_DAYS))
        precs = [prec("A", "confirmed", evidence=["graph"]), prec("B", "confirmed", provider="P4", closed=old, network="N02"),
                 prec("C", "inconclusive", network="N03"), prec("D", "confirmed", evidence=["R3 bundling edit pair (PTP)"])]
        effects = {e["case_id"]: e for e in confidence.score(case(), precs, guard=True)["precedent_effects"]}
        self.assertEqual(effects["A"]["status"], "accepted")
        self.assertEqual((effects["B"]["status"], effects["B"]["weight"]), ("reduced", 0.5))
        self.assertEqual(effects["C"]["status"], "rejected")
        self.assertEqual(effects["D"]["status"], "reduced")
        self.assertIn("no network bonus", effects["D"]["why"][0])

    def test_contradiction_is_explained_and_names_the_other_verdict(self):
        precs = [prec("A", "confirmed"), prec("B", "cleared", provider="P3")]
        effects = confidence.score(case(), precs, guard=True)["precedent_effects"]
        self.assertEqual([e["status"] for e in effects], ["rejected", "rejected"])
        self.assertIn("B", effects[0]["why"][0])
        self.assertEqual(sum(e["delta"] for e in effects), 0)

    def test_approved_evidence_backed_precedent_still_lifts_eligible_case(self):
        on = confidence.score(case(evidence_strength=0.5), [prec("A", "confirmed", evidence=["graph"])], guard=True)
        self.assertEqual((on["score"], on["tier"]), (0.75, "high"))


if __name__ == "__main__":
    unittest.main()
