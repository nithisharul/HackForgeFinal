"""Outbound notifications (Slack, Teams, signed webhooks) and the operations layer (headers, request IDs, probes, CSV export).

    python -m unittest discover -s backend/tests -t .
"""
import asyncio
import hashlib
import hmac
import http.server
import json
import os
import threading
import unittest
from unittest import mock

from backend.integrations import notify

os.environ.setdefault("LOG_FORMAT", "off")  # keep test output clean; set before the app builds its middleware


def call(app, path, headers=()):
    """One GET straight through the ASGI app, middleware included, without an HTTP client dependency."""
    out, body = {}, []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(m):
        if m["type"] == "http.response.start":
            out["status"], out["headers"] = m["status"], {k.decode().lower(): v.decode() for k, v in m["headers"]}
        elif m["type"] == "http.response.body":
            body.append(m.get("body", b""))

    p, _, q = path.partition("?")
    scope = {"type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET", "scheme": "http", "path": p,
             "raw_path": p.encode(), "query_string": q.encode(), "root_path": "", "client": ("127.0.0.1", 1), "server": ("test", 80),
             "headers": [(k.lower().encode(), v.encode()) for k, v in headers]}
    asyncio.run(app(scope, receive, send))
    out["body"] = b"".join(body)
    return out


class Messages(unittest.TestCase):
    def setUp(self):
        self.env = notify.envelope("verdict.recorded", {"case_id": "CASE-P209", "provider_id": "P209", "verdict": "confirmed", "actor": "Asha Rao"})
        self.cfg = {"secret": "k" * 32, "base": "https://siu.example.org", "slack": "", "teams": "", "webhooks": [], "events": set(notify.EVENTS)}

    def test_envelope_is_versioned_and_unique(self):
        other = notify.envelope("verdict.recorded", {})
        self.assertEqual(self.env["schema"], "csn.event.v1")
        self.assertNotEqual(self.env["id"], other["id"])

    def test_slack_and_teams_shapes_link_to_the_case(self):
        link = notify.link(self.cfg, self.env["data"])
        self.assertEqual(link, "https://siu.example.org/#/case/CASE-P209")
        slack = notify.slack_body(self.env, link)
        self.assertIn("CASE-P209", slack["text"])
        self.assertEqual(slack["blocks"][1]["elements"][0]["url"], link)
        teams = notify.teams_body(self.env, link)
        card = teams["attachments"][0]
        self.assertEqual(card["contentType"], "application/vnd.microsoft.card.adaptive")
        self.assertEqual(card["content"]["actions"][0]["url"], link)

    def test_webhook_signature_verifies(self):
        req = notify.request_for("webhook", "https://x.example.org/h", self.env, self.cfg)
        h = {k.lower(): v for k, v in req.header_items()}
        expected = "sha256=" + hmac.new(self.cfg["secret"].encode(), f"{h['x-csn-timestamp']}.".encode() + req.data, hashlib.sha256).hexdigest()
        self.assertEqual(h["x-csn-signature"], expected)
        self.assertEqual(h["x-csn-event"], "verdict.recorded")
        self.assertEqual(json.loads(req.data)["link"], "https://siu.example.org/#/case/CASE-P209")

    def test_only_https_or_localhost(self):
        self.assertTrue(notify.allowed_url("https://hooks.slack.com/services/x"))
        self.assertTrue(notify.allowed_url("http://127.0.0.1:9000/h"))
        self.assertFalse(notify.allowed_url("http://hooks.example.org/h"))
        self.assertFalse(notify.allowed_url("file:///etc/passwd"))

    def test_masked_targets_hide_the_secret_path(self):
        self.assertEqual(notify.mask("https://hooks.slack.com/services/T000/B000/XXXX"), "https://hooks.slack.com/…")

    def test_nothing_configured_sends_nothing(self):
        with mock.patch.dict(os.environ, {"SLACK_WEBHOOK_URL": "", "TEAMS_WEBHOOK_URL": "", "WEBHOOK_URLS": ""}):
            self.assertIsNone(notify.emit("verdict.recorded", {"case_id": "CASE-P1"}))


class Delivery(unittest.TestCase):
    def test_signed_webhook_reaches_a_receiver(self):
        got = []

        class Receiver(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                got.append(({k.lower(): v for k, v in self.headers.items()}, self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(204)
                self.end_headers()

            def log_message(self, *a):
                pass

        srv = http.server.HTTPServer(("127.0.0.1", 0), Receiver)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        url = f"http://127.0.0.1:{srv.server_port}/hook"
        try:
            with mock.patch.dict(os.environ, {"WEBHOOK_URLS": url, "WEBHOOK_SECRET": "s" * 32, "SLACK_WEBHOOK_URL": "", "TEAMS_WEBHOOK_URL": "",
                                              "NOTIFY_EVENTS": ""}):
                event_id = notify.emit("verdict.recorded", {"case_id": "CASE-P209", "verdict": "cleared", "actor": "Asha Rao"})
                notify.flush()
        finally:
            srv.shutdown()
        self.assertEqual(len(got), 1)
        headers, body = got[0]
        self.assertEqual(json.loads(body)["id"], event_id)
        sig = "sha256=" + hmac.new(b"s" * 32, f"{headers['x-csn-timestamp']}.".encode() + body, hashlib.sha256).hexdigest()
        self.assertEqual(headers["x-csn-signature"], sig)
        self.assertTrue(notify.status()["recent"][0]["ok"])

    def test_filtered_events_are_not_sent(self):
        with mock.patch.dict(os.environ, {"WEBHOOK_URLS": "https://x.example.org/h", "NOTIFY_EVENTS": "security.alert"}):
            self.assertIsNone(notify.emit("verdict.recorded", {"case_id": "CASE-P1"}))


class Operations(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from backend.app.main import app
        cls.app = app

    def test_security_headers_and_request_id(self):
        r = call(self.app, "/api/health/live")
        self.assertEqual(r["status"], 200)
        h = r["headers"]
        self.assertEqual(h["x-frame-options"], "DENY")
        self.assertEqual(h["x-content-type-options"], "nosniff")
        self.assertEqual(h["cache-control"], "no-store")
        self.assertRegex(h["x-request-id"], r"^[0-9a-f]{32}$")

    def test_caller_request_id_is_kept_and_unsafe_ones_replaced(self):
        self.assertEqual(call(self.app, "/api/health/live", [("X-Request-ID", "trace-123")])["headers"]["x-request-id"], "trace-123")
        self.assertNotIn("<", call(self.app, "/api/health/live", [("X-Request-ID", "<script>")])["headers"]["x-request-id"])

    def test_readiness_checks_both_regions(self):
        r = call(self.app, "/api/health/ready")
        body = json.loads(r["body"])
        self.assertEqual(r["status"], 200, body)
        self.assertEqual(set(body["checks"]), {"data_us", "data_in", "database"})

    def test_queue_export_is_csv_in_queue_order(self):
        r = call(self.app, "/api/queue/export?region=us")
        self.assertTrue(r["headers"]["content-type"].startswith("text/csv"))
        lines = r["body"].decode().splitlines()
        self.assertTrue(lines[0].startswith("rank,case_id,"))
        self.assertTrue(lines[1].startswith("1,"))

    def test_csv_cells_cannot_run_as_formulas(self):
        from backend.app import store
        row = {"rank": 1, "case_id": "CASE-X", "provider_name": "=HYPERLINK(\"http://evil\")", "city": "+1", "status": "open"}
        with mock.patch.object(store, "queue", return_value={"cases": [row]}):
            body = call(self.app, "/api/queue/export")["body"].decode()
        self.assertIn("'=HYPERLINK", body)
        self.assertIn("'+1", body)

    def test_integrations_need_an_admin(self):
        self.assertIn(call(self.app, "/api/integrations")["status"], (401, 503))


if __name__ == "__main__":
    unittest.main()
