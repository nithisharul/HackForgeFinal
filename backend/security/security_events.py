"""Security event log: what the defences caught. Each event has a type, a severity and the action taken."""
from .store import now, open_db

SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")


def record(type_, severity, source, detail, action, actor="", once=False):
    """Add an event. With once=True an identical unresolved event is not repeated on every check."""
    with open_db() as con, con:
        if once and con.execute("SELECT 1 FROM security_events WHERE type = ? AND detail = ? AND id > COALESCE((SELECT MAX(id) FROM security_events WHERE type = 'KNOWLEDGE_RESEALED'), 0)", (type_, detail)).fetchone():
            return None
        cur = con.execute("INSERT INTO security_events (ts, type, severity, source, actor, detail, action) VALUES (?,?,?,?,?,?,?)",
                          (now(), type_, severity, source, actor or "", detail[:500], action))
        event_id = f"SEC-{cur.lastrowid:03d}"
    if severity in ("HIGH", "CRITICAL"):  # leads hear about it where they already work; the detail stays on the server
        from backend import region
        from backend.integrations import notify
        notify.emit("security.alert", {"event_id": event_id, "type": type_, "severity": severity, "source": source,
                                       "action": action, "actor": actor or ""}, region.current().code)
    return event_id


def recent(limit=50):
    with open_db() as con:
        rows = con.execute("SELECT * FROM security_events ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [{**dict(r), "event_id": f"SEC-{r['id']:03d}"} for r in rows]


def counts():
    with open_db() as con:
        return {r["severity"]: r["n"] for r in con.execute("SELECT severity, COUNT(*) n FROM security_events GROUP BY severity")}
