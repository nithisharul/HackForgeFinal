"""PrecedentGuard revocation through the API, on a throwaway copy of the Second Brain.

    python -m unittest discover -s backend/tests -t .
"""
import unittest

from fastapi.testclient import TestClient

from backend import region
from backend.app import store
from backend.app.main import app
from backend.brain import retrieve, wiki
from backend.tests.helpers import INVESTIGATOR, isolated_wiki, signed_in

REASON = {"reason": "Records show the referrals were independent; verdict was wrong."}


def influential_precedent():
    """A confirmed, unrevoked verdict that currently moves at least one open US case."""
    for m in wiki.case_metas():
        if m["verdict"] == "confirmed" and not m.get("revoked"):
            affected = store.influence(m["id"])
            if affected:
                return m["id"], affected
    raise AssertionError("no influential precedent in the US Second Brain")


class Revocation(unittest.TestCase):
    def setUp(self):
        isolated_wiki(self)
        self.auth = signed_in(self)
        self.client = TestClient(app)
        with region.use("us"):
            self.prec, self.affected = influential_precedent()

    def test_writes_need_a_valid_session(self):
        url = f"/api/precedents/{self.prec}/revoke?region=us"
        self.assertEqual(self.client.post(url, json=REASON).status_code, 401)
        forged = self.auth["Authorization"][:-4] + "AAAA"
        self.assertEqual(self.client.post(url, json=REASON, headers={"Authorization": forged}).status_code, 401)
        self.assertEqual(self.client.post(url, json=REASON, headers={"Authorization": "Bearer not.a-token"}).status_code, 401)
        with region.use("us"):
            self.assertFalse(wiki.read(self.prec)[0].get("revoked"))

    def test_influence_reports_scores_and_ranks_with_and_without(self):
        body = self.client.get(f"/api/precedents/{self.prec}/influence?region=us").json()
        self.assertEqual(body["revoked"], "")
        row = body["affected"][0]
        for key in ("score", "score_without", "tier", "tier_without", "rank", "rank_without"):
            self.assertIn(key, row)

    def test_revocation_reverses_downstream_effects_and_keeps_the_record(self):
        expected = {r["case_id"]: r["score_without"] for r in self.affected}
        r = self.client.post(f"/api/precedents/{self.prec}/revoke?region=us", json=REASON, headers=self.auth)
        self.assertEqual(r.status_code, 200, r.text)
        self.assertEqual(r.json()["revoked_by"], INVESTIGATOR)  # from the session, never the request body
        with region.use("us"):
            self.assertEqual(store.influence(self.prec), [])
            for cid, score_without in expected.items():
                case = store.data().CASES[cid]
                _, conf, _ = store.enrich(case)
                self.assertEqual(conf["score"], score_without)
                self.assertNotIn(self.prec, [p["case_id"] for p in retrieve.precedents(case)])
                self.assertIn(self.prec, [p["case_id"] for p in retrieve.revoked(case)])
            meta, body = wiki.read(self.prec)
            self.assertEqual((meta["verdict"], meta["revoked_by"]), ("confirmed", INVESTIGATOR))
            self.assertIn("## Revoked as precedent", body)
            self.assertIn(f"revoke | {self.prec} revoked", (region.current().know / "wiki" / "log.md").read_text(encoding="utf-8"))
        again = self.client.post(f"/api/precedents/{self.prec}/revoke?region=us", json=REASON, headers=self.auth)
        self.assertEqual(again.status_code, 409)

    def test_revoking_in_one_region_leaves_the_other_untouched(self):
        with region.use("in"):
            before = wiki.read(self.prec)[0]
        self.client.post(f"/api/precedents/{self.prec}/revoke?region=us", json=REASON, headers=self.auth)
        with region.use("in"):
            after = wiki.read(self.prec)[0]
        self.assertEqual(before, after)

    def test_unknown_precedent_is_404(self):
        self.assertEqual(self.client.get("/api/precedents/NOPE-1/influence?region=us").status_code, 404)
        self.assertEqual(self.client.post("/api/precedents/NOPE-1/revoke?region=in", json=REASON, headers=self.auth).status_code, 404)


if __name__ == "__main__":
    unittest.main()
