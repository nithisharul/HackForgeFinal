"""Clinical record audit: right record for the right case, no invented findings, model output kept separate.

    python -m unittest discover -s backend/tests -t .
"""
import json
import os
import shutil
import tempfile
import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from backend import region
from backend.app import store
from backend.app.main import app
from backend.brain import clinical_audit as ca
from backend.brain import llm

NOTES = region.ROOT / "data" / "clinical_notes" / "us"


def note(name):
    return (NOTES / name).read_text(encoding="utf-8-sig")


def us_case(case_id):
    with region.use("us"):
        return store.data().CASES[case_id]


class Base(unittest.TestCase):
    env = {"CLINICAL_LLM_ENABLED": "0"}

    def setUp(self):
        llm._env()
        patcher = mock.patch.dict(os.environ, self.env)
        patcher.start()
        self.addCleanup(patcher.stop)
        llm._STATUS.clear()
        ca._LLM_CACHE.clear()
        self.client = TestClient(app)

    def notes_dir(self, files):
        """Fixture records in a temporary notes folder; the real notes are never modified."""
        tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "us").mkdir()
        for name, text in files.items():
            (tmp / "us" / name).write_text(text, encoding="utf-8")
        patcher = mock.patch.object(ca, "NOTES", tmp)
        patcher.start()
        self.addCleanup(patcher.stop)

    def audit(self, case_id, reg="us", **params):
        r = self.client.get(f"/api/cases/{case_id}/clinical-audit", params={"region": reg, **params})
        self.assertEqual(r.status_code, 200, r.text)
        return r.json()


class Records(Base):
    def test_own_record_loads_but_uncorroborated_conflict_is_not_a_finding(self):
        b = self.audit("CASE-P209")
        self.assertEqual(b["source"]["name"], "CASE-P209.txt")
        self.assertEqual(b["document_facts"]["date_of_service"], "2026-03-14")
        checks = {c["id"]: c["result"] for c in b["checks"]}
        self.assertEqual(checks, {"identity": "match", "claims_on_date": "no_claims", "presence": "conflict"})
        self.assertEqual(b["status"], "insufficient_evidence")
        self.assertFalse(b["discrepancy_found"])
        self.assertTrue(all(not f["corroborated_by_claims"] for f in b["findings"]))
        self.assertNotIn("statute", json.dumps(b).lower())
        self.assertTrue(b["read_only"])

    def test_case_without_a_record_never_borrows_one(self):
        b = self.audit("CASE-P001")  # same pattern as CASE-P209, which has a record
        self.assertEqual((b["status"], b["discrepancy_found"], b["source"], b["findings"]), ("unavailable", False, None, []))
        self.assertIsNone(b["text"])

    def test_india_never_uses_us_records(self):
        b = self.audit("CASE-P104", reg="in")  # a US record named CASE-P104.txt exists
        self.assertEqual((b["status"], b["source"], b["text"]), ("unavailable", None, None))
        self.assertIn("not used as PM-JAY evidence", b["status_reason"])

    def test_unknown_case_and_region_are_rejected(self):
        self.assertEqual(self.client.get("/api/cases/CASE-P104/clinical-audit?region=us").status_code, 404)
        self.assertEqual(self.client.get("/api/cases/CASE-P209/clinical-audit?region=in").status_code, 404)
        self.assertEqual(self.client.get("/api/cases/CASE-P209/clinical-audit?region=uk").status_code, 422)

    def test_paths_outside_the_notes_folder_are_refused(self):
        for bad in ("../CASE-P209", "CASE-P209/../../.env", "CASE-P2090", "case-p209", "..", "", "CASE-P209.txt"):
            with self.assertRaises(ca.InvalidCaseId):
                ca.note_path("us", bad)

    def test_record_naming_another_provider_is_not_read_further(self):
        self.notes_dir({"CASE-P001.txt": note("CASE-P209.txt")})  # Dr. Hannah Hayes's log filed under Dr. Maria Ellis
        b = self.audit("CASE-P001")
        self.assertEqual(b["status"], "insufficient_evidence")
        self.assertEqual([c["id"] for c in b["checks"]], ["identity", "claims_on_date"])
        self.assertEqual((b["findings"], b["text"], b["llm"]["status"]), ([], None, "not_run"))

    def test_missing_date_is_not_filled_in(self):
        facts = ca.extract("=== NOTE ===\nATTENDING PHYSICIAN: Dr. A B\nNo date here.")
        self.assertIsNone(facts["date_of_service"])
        self.assertEqual(facts["events"], [])


class Checks(Base):
    def test_time_based_visit_level_check(self):
        text = note("CASE-P104.txt")
        c = ca.em_time_check(ca.extract(text), text)
        self.assertEqual(c["result"], "conflict")
        self.assertIn("7 minutes", c["detail"])
        self.assertTrue(all(e for e in c["evidence"]))

    def test_bundling_check_says_where_the_pair_comes_from(self):
        text = note("CASE-P164.txt")
        with region.use("us"):
            c = ca.bundling_check(ca.extract(text), text)
        self.assertEqual(c["result"], "conflict")
        self.assertIn("80053/80048", c["detail"])
        self.assertIn("not from the CMS file", c["detail"])

    def test_corroborated_conflict_is_a_finding(self):
        case = us_case("CASE-P040")  # Dr. Carlos Ibarra, upcoding; has claims on 2026-09-04
        text = (note("CASE-P104.txt").replace("Dr. Hannah Hayes, MD", case["provider_name"])
                .replace("2026-02-18", "2026-09-04"))
        self.notes_dir({"CASE-P040.txt": text})
        b = self.audit("CASE-P040")
        self.assertEqual(b["status"], "discrepancy_found")
        self.assertTrue(b["discrepancy_found"])
        self.assertEqual(b["findings"][0]["basis"], "deterministic check")
        self.assertTrue(b["findings"][0]["corroborated_by_claims"])
        self.assertTrue(b["recommended_verification"])


class FakeOllama(BaseHTTPRequestHandler):
    mode = "good"

    def log_message(self, *a):
        pass

    def _send(self, body):
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        self._send({"models": [{"name": "llama3.2:latest"}]})

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if FakeOllama.mode == "slow":
            time.sleep(2.5)
        content = "this is {not json" if FakeOllama.mode == "malformed" else json.dumps({
            "discrepancy": True, "type": "Impossible presence", "finding": "Provider was badged in San Antonio.",
            "quotes": ["[13:30:00 CST] CONCURRENT BILLED CLAIM ENCOUNTER", "Provider admitted the fraud in writing."]})
        try:
            self._send({"message": {"content": content}})
        except OSError:
            pass  # the client gave up (timeout test)


class ModelReading(Base):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), FakeOllama)
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def setUp(self):
        self.env = {"CLINICAL_LLM_ENABLED": "1", "CLINICAL_LLM_TIMEOUT": "1",
                    "CLINICAL_LLM_BASE_URL": f"http://127.0.0.1:{self.server.server_address[1]}"}
        super().setUp()
        FakeOllama.mode = "good"

    def test_model_cannot_change_the_status_and_invented_quotes_are_dropped(self):
        b = self.audit("CASE-P209")
        self.assertEqual(b["status"], "insufficient_evidence")  # the model says discrepancy; the checks decide
        m = b["llm"]
        self.assertEqual((m["status"], m["discrepancy"], m["quotes_rejected"]), ("completed", True, 1))
        self.assertEqual(m["quotes_verified"], ["[13:30:00 CST] CONCURRENT BILLED CLAIM ENCOUNTER"])

    def test_malformed_json_is_reported_not_guessed(self):
        FakeOllama.mode = "malformed"
        b = self.audit("CASE-P209")
        self.assertEqual((b["llm"]["status"], b["status"]), ("error", "insufficient_evidence"))
        self.assertIn("malformed", b["llm"]["reason"])

    def test_timeout_is_reported(self):
        FakeOllama.mode = "slow"
        b = self.audit("CASE-P209")
        self.assertEqual(b["llm"]["status"], "error")
        self.assertIn("did not answer", b["llm"]["reason"])

    def test_model_can_be_skipped(self):
        self.assertEqual(self.audit("CASE-P209", llm="false")["llm"]["status"], "not_run")


class ModelOffline(Base):
    env = {"CLINICAL_LLM_ENABLED": "1", "CLINICAL_LLM_BASE_URL": "http://127.0.0.1:9"}  # nothing listens on port 9

    def test_offline_model_is_unavailable_and_checks_still_run(self):
        b = self.audit("CASE-P209")
        self.assertEqual(b["llm"]["status"], "unavailable")
        self.assertEqual(b["status"], "insufficient_evidence")


if __name__ == "__main__":
    unittest.main()
