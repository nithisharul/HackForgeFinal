"""Tamper-evident audit log for the Second Brain.

Every approved change adds one entry: who, what, when, and the SHA-256 fingerprint of every knowledge file
that change wrote. Each entry also holds the previous entry's hash, and its own hash is an HMAC signed with
the server's key, so an entry cannot be edited, removed from the middle, or re-forged without the key.

verify() replays the chain and then compares every knowledge file on disk with its last signed fingerprint:
    modified   the file differs from what the last approved change wrote
    deleted    a recorded file is gone
    unlogged   a file exists that no approved change created

Extends the team's first hash-chain module (hash_log_entry / verify_log_chain) with signing, file
fingerprints and storage in the database.

Limits: the signing key is on the same machine as the data, so this detects edits by someone who can change
files or pages but does not hold the key. Removing the newest entries together with reverting the files is not
detectable without an external copy of the latest hash. Production would keep the key in a vault and ship
the log to append-only storage.
"""
import hashlib
import hmac
import json

from backend import region
from backend.pipeline.common import KNOW

from . import security_events
from .store import now, open_db, secret

ALWAYS = ("wiki/log.md", "learned_patterns.json")


def tracked_files():
    """Every knowledge file whose content the audit log vouches for, in every region, as paths relative to knowledge/
    (India's pages live under knowledge/india/, so they appear as india/wiki/...)."""
    files = []
    for root in {r.know for r in region.REGIONS.values()}:
        files += list((root / "wiki").rglob("*.md")) + list((root / "sources" / "documents").glob("*.md"))
        if (root / "learned_patterns.json").exists():
            files.append(root / "learned_patterns.json")
    return {str(p.relative_to(KNOW)).replace("\\", "/"): p for p in files}


def _prefix():
    """The active region's folder under knowledge/: '' for the US, 'india/' for India."""
    rel = region.current().know.relative_to(KNOW).as_posix()
    return "" if rel == "." else rel + "/"


def fingerprint(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def hash_log_entry(ts, actor, action, target, detail, files, previous_hash):
    body = json.dumps([ts, actor, action, target, detail, files, previous_hash], separators=(",", ":"), sort_keys=True)
    return hmac.new(secret().encode(), body.encode(), hashlib.sha256).hexdigest()


def append(actor, action, target, detail="", paths=()):
    """Record one approved change and the fingerprints of the files it wrote. A path that no longer exists is recorded as removed."""
    current = tracked_files()
    files = {p: (fingerprint(current[p]) if p in current else None) for p in sorted(set(paths))}
    with open_db() as con, con:
        last = con.execute("SELECT current_hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
        previous, ts, files_json = (last["current_hash"] if last else ""), now(), json.dumps(files, sort_keys=True)
        h = hash_log_entry(ts, actor, action, target, detail[:300], files_json, previous)
        cur = con.execute("INSERT INTO audit_log (ts, actor, action, target, detail, files, previous_hash, current_hash) "
                          "VALUES (?,?,?,?,?,?,?,?)", (ts, actor, action, target, detail[:300], files_json, previous, h))
        return cur.lastrowid


def record_change(actor, action, target, changes, extra=(), detail=""):
    """Called by the API after an approved Second Brain write. `changes` is the list the wiki returned."""
    pre, tracked = _prefix(), tracked_files()
    paths = [pre + c["path"] for c in changes] + [pre + p for p in ALWAYS if pre + p in tracked] + [pre + e for e in extra]
    return append(actor, action, target, detail, paths)


def seal(actor, reason):
    """Record the current state of every knowledge file as trusted. Used after the offline pipeline rebuilds the wiki."""
    return append(actor, "seal", "all knowledge files", reason, tracked_files())


def entries(limit=100):
    with open_db() as con:
        rows = con.execute("SELECT * FROM audit_log ORDER BY seq DESC LIMIT ?", (limit,)).fetchall()
    return [{**{k: r[k] for k in ("seq", "ts", "actor", "action", "target", "detail")},
             "files": len(json.loads(r["files"])), "hash": r["current_hash"][:16]} for r in rows]


def verify_log_chain():
    """Replay the chain. Returns (validity dict, {path: last signed fingerprint})."""
    with open_db() as con:
        rows = con.execute("SELECT * FROM audit_log ORDER BY seq").fetchall()
    state, previous = {}, ""
    for i, r in enumerate(rows, start=1):
        if r["seq"] != i:
            return {"valid": False, "broken_entry": i, "reason": "An entry is missing from the log"}, state
        if r["previous_hash"] != previous:
            return {"valid": False, "broken_entry": r["seq"], "reason": "Previous hash does not match"}, state
        expected = hash_log_entry(r["ts"], r["actor"], r["action"], r["target"], r["detail"], r["files"], r["previous_hash"])
        if not hmac.compare_digest(expected, r["current_hash"]):
            return {"valid": False, "broken_entry": r["seq"], "reason": "Entry data has been changed"}, state
        state.update(json.loads(r["files"]))
        previous = r["current_hash"]
    return {"valid": True, "broken_entry": None, "reason": "Log chain is valid", "entries": len(rows)}, state


def verify(raise_events=True):
    """Full integrity check: the chain, then every knowledge file against its last signed fingerprint."""
    with open_db() as con:
        unsealed = con.execute("SELECT COUNT(*) FROM audit_log WHERE action = 'seal'").fetchone()[0] == 0
    if unsealed:  # first run on this machine: take the current files as the starting point, and say so in the log
        seal("system", "First integrity check on this server: current files taken as the baseline.")
    chain, state = verify_log_chain()
    problems = []
    if not chain["valid"]:
        problems.append({"kind": "log", "page": "log", "path": "audit log",
                         "issue": f"audit log entry {chain['broken_entry']}: {chain['reason']}"})
    current = tracked_files()
    if not chain["valid"]:   # the fingerprints after the break cannot be trusted, so files are not compared
        state, current_for_new = {}, {}
    else:
        current_for_new = current
    for path, sha in state.items():
        name = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        if sha is None:
            if path in current:
                problems.append({"kind": "unlogged", "page": name, "path": path, "issue": "file reappeared after an approved removal"})
        elif path not in current:
            problems.append({"kind": "deleted", "page": name, "path": path, "issue": "file was deleted outside the app"})
        elif fingerprint(current[path]) != sha:
            problems.append({"kind": "modified", "page": name, "path": path, "issue": "content was changed outside the app"})
    for path in current_for_new:
        if path not in state:
            problems.append({"kind": "unlogged", "page": path.rsplit("/", 1)[-1].rsplit(".", 1)[0], "path": path,
                             "issue": "file was added outside the app"})
    if raise_events:
        for p in problems:
            security_events.record("LOG_INTEGRITY_FAILURE" if p["kind"] == "log" else "KNOWLEDGE_TAMPERING", "CRITICAL",
                                   "Integrity check", f"{p['path']}: {p['issue']}", "ALERT", once=True)
    return {"chain_valid": chain["valid"], "entries": chain.get("entries", 0), "files_checked": len(current),
            "problems": problems, "ok": not problems}
