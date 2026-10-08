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


if __name__ == "__main__":
    unittest.main()
