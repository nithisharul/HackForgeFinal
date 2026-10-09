"""Outbound notifications: Slack, Microsoft Teams and signed webhooks for case-management systems.

Configure in .env (all optional; with none set, nothing is sent and nothing slows down):
    SLACK_WEBHOOK_URL    a Slack incoming-webhook URL
    TEAMS_WEBHOOK_URL    a Microsoft Teams Workflows ("Post to a channel when a webhook request is received") URL
    WEBHOOK_URLS         comma-separated endpoints of other systems (case management, SIEM, data lake)
    WEBHOOK_SECRET       signs every generic webhook: X-CSN-Signature = sha256=HMAC(secret, "<timestamp>.<body>")
    APP_BASE_URL         public address of the app, so messages link straight to the case (e.g. https://siu.example.org)
    NOTIFY_EVENTS        comma-separated event types to send; default all

Events: verdict.recorded, precedent.revoked, source.approved, pattern.approved, security.alert, integration.test.

What leaves the server is deliberately small: event type, case and provider IDs, the verdict, who approved it,
when, and a link. No member IDs, no claim lines, no free-text reasoning, so a chat channel never holds PHI;
the receiving system follows the link or calls the API for detail under its own access control.

Delivery runs on one background thread: a slow or failing receiver never delays an investigator. Each delivery
is retried 3 times with backoff and the last 50 results are kept for GET /api/integrations.
"""
import collections
import datetime as dt
import hashlib
import hmac
import json
import os
import queue
import threading
import time
import urllib.parse
import urllib.request
import uuid

from backend.brain import llm

EVENTS = ("verdict.recorded", "precedent.revoked", "source.approved", "pattern.approved", "security.alert", "integration.test")
RETRIES, TIMEOUT = 3, 5
_queue = queue.Queue(maxsize=1000)
_log = collections.deque(maxlen=50)
_worker = None
_lock = threading.Lock()


def config():
    llm._env()  # loads the project .env once
    split = lambda v: [x.strip() for x in os.getenv(v, "").split(",") if x.strip()]
    return {"slack": os.getenv("SLACK_WEBHOOK_URL", "").strip(), "teams": os.getenv("TEAMS_WEBHOOK_URL", "").strip(),
            "webhooks": split("WEBHOOK_URLS"), "secret": os.getenv("WEBHOOK_SECRET", ""),
            "base": os.getenv("APP_BASE_URL", "").rstrip("/"), "events": set(split("NOTIFY_EVENTS")) or set(EVENTS)}


def allowed_url(url):
    """HTTPS only, except to this machine (local receivers and tests)."""
    u = urllib.parse.urlparse(url)
    return u.scheme == "https" or (u.scheme == "http" and u.hostname in ("localhost", "127.0.0.1", "::1"))


def mask(url):
    u = urllib.parse.urlparse(url)
    return f"{u.scheme}://{u.hostname}/…" if u.hostname else "(invalid)"


def channels(cfg=None):
    cfg = cfg or config()
    out = [("slack", cfg["slack"])] if cfg["slack"] else []
    out += [("teams", cfg["teams"])] if cfg["teams"] else []
    out += [("webhook", u) for u in cfg["webhooks"]]
    return out


# ------------------------------------------------------------------ messages ---
def envelope(event, data, region="us"):
    return {"id": str(uuid.uuid4()), "type": event, "occurred_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "region": region, "source": "claimshield-nexus", "schema": "csn.event.v1", "data": data}


def link(cfg, data):
    if not cfg["base"] or not data.get("case_id"):
        return ""
    return f"{cfg['base']}/#/case/{data['case_id']}"


def headline(env):
    d, t = env["data"], env["type"]
    if t == "verdict.recorded":
        return f"{d.get('case_id')} ({d.get('provider_id')}) closed as {d.get('verdict')} by {d.get('actor')}"
    if t == "precedent.revoked":
        return f"{d.get('case_id')} withdrawn as precedent by {d.get('actor')}; {d.get('cases_restored', 0)} open case(s) re-scored"
    if t in ("source.approved", "pattern.approved"):
        what = "New pattern" if t == "pattern.approved" else "Source document"
        return f"{what} {d.get('id')} approved by {d.get('actor')}: {d.get('title', '')}"
    if t == "security.alert":
        return f"{d.get('severity')} security event {d.get('event_id', '')}: {d.get('type')} ({d.get('action')})"
    return d.get("message", "ClaimShield Nexus test notification")


def slack_body(env, url=""):
    text = headline(env)
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": f"*ClaimShield Nexus* · {env['region'].upper()}\n{text}"}}]
    if url:
        blocks.append({"type": "actions", "elements": [{"type": "button", "text": {"type": "plain_text", "text": "Open case"}, "url": url}]})
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": f"{env['type']} · {env['occurred_at']} · event {env['id'][:8]}"}]})
    return {"text": text, "blocks": blocks}


def teams_body(env, url=""):
    card = {"type": "AdaptiveCard", "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "version": "1.4",
            "body": [{"type": "TextBlock", "text": f"ClaimShield Nexus · {env['region'].upper()}", "weight": "Bolder", "size": "Small"},
                     {"type": "TextBlock", "text": headline(env), "wrap": True},
                     {"type": "TextBlock", "text": f"{env['type']} · {env['occurred_at']}", "isSubtle": True, "size": "Small", "wrap": True}]}
    if url:
        card["actions"] = [{"type": "Action.OpenUrl", "title": "Open case", "url": url}]
    return {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": card}]}


def sign(secret, ts, body):
    return "sha256=" + hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()


def request_for(kind, url, env, cfg):
    """The HTTP request one channel receives for one event."""
    target = link(cfg, env["data"])
    payload = slack_body(env, target) if kind == "slack" else teams_body(env, target) if kind == "teams" else dict(env, link=target)
    body = json.dumps(payload, separators=(",", ":")).encode()
    headers = {"Content-Type": "application/json", "User-Agent": "claimshield-nexus/0.1"}
    if kind == "webhook":
        ts = str(int(time.time()))
        headers |= {"X-CSN-Event": env["type"], "X-CSN-Delivery": env["id"], "X-CSN-Timestamp": ts}
        if cfg["secret"]:
            headers["X-CSN-Signature"] = sign(cfg["secret"], ts, body)
    return urllib.request.Request(url, data=body, headers=headers, method="POST")


# ------------------------------------------------------------------ delivery ---
def _deliver(kind, url, env, cfg):
    error = "blocked: only https:// URLs (or localhost) are allowed" if not allowed_url(url) else None
    status = None
    for attempt in range(RETRIES if not error else 0):
        try:
            with urllib.request.urlopen(request_for(kind, url, env, cfg), timeout=TIMEOUT) as r:
                status, error = r.status, None
                break
        except Exception as e:  # noqa: BLE001 - any failure is retried, then recorded
            status, error = getattr(e, "code", None), str(e)[:200]
            if status and 400 <= status < 500 and status != 429:
                break  # the receiver rejected the message; retrying will not help
            time.sleep(min(8, 2 ** attempt * 0.5))
    _log.appendleft({"at": dt.datetime.now().isoformat(timespec="seconds"), "event": env["type"], "event_id": env["id"],
                     "channel": kind, "target": mask(url), "ok": error is None, "status": status, "error": error})


def _run():
    while True:
        kind, url, env, cfg = _queue.get()
        try:
            _deliver(kind, url, env, cfg)
        finally:
            _queue.task_done()


def emit(event, data, region="us"):
    """Queue an event for every configured channel. Never raises and never blocks the caller."""
    global _worker
    try:
        cfg = config()
        targets = channels(cfg)
        if not targets or event not in cfg["events"]:
            return None
        env = envelope(event, data, region)
        with _lock:
            if _worker is None or not _worker.is_alive():
                _worker = threading.Thread(target=_run, name="notify", daemon=True)
                _worker.start()
        for kind, url in targets:
            _queue.put_nowait((kind, url, env, cfg))
        return env["id"]
    except Exception as e:  # noqa: BLE001 - notifications must never break a write
        print(f"[notify] {event}: {e}")
        return None


def status():
    cfg = config()
    return {"channels": [{"kind": k, "target": mask(u), "allowed": allowed_url(u)} for k, u in channels(cfg)],
            "signed": bool(cfg["secret"]), "links": bool(cfg["base"]), "events": sorted(cfg["events"]),
            "pending": _queue.qsize(), "recent": list(_log)}


def flush(timeout=10):
    """Wait for queued deliveries (tests and the test endpoint)."""
    end = time.time() + timeout
    while _queue.unfinished_tasks and time.time() < end:
        time.sleep(0.05)
