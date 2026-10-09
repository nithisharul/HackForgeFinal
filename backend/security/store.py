"""Security storage: the signed audit log and the security events, in the same SQLite file as the accounts."""
import contextlib
import datetime as dt
import os
import secrets
import sqlite3
from pathlib import Path

from backend.brain import llm
from backend.pipeline.common import ROOT


def db():
    path = Path(os.getenv("AUTH_DB") or ROOT / "data" / "app.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=5)
    con.row_factory = sqlite3.Row
    con.executescript("""
        CREATE TABLE IF NOT EXISTS audit_log (seq INTEGER PRIMARY KEY, ts TEXT NOT NULL, actor TEXT NOT NULL,
            action TEXT NOT NULL, target TEXT NOT NULL, detail TEXT NOT NULL, files TEXT NOT NULL,
            previous_hash TEXT NOT NULL, current_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS security_events (id INTEGER PRIMARY KEY, ts TEXT NOT NULL, type TEXT NOT NULL,
            severity TEXT NOT NULL, source TEXT NOT NULL, actor TEXT NOT NULL, detail TEXT NOT NULL, action TEXT NOT NULL);
    """)
    return con


def open_db():
    return contextlib.closing(db())


def now():
    return dt.datetime.now().isoformat(timespec="seconds")


def secret():
    """The server's signing key (shared with session tokens). Created in .env the first time it is needed."""
    llm._env()
    key = os.getenv("AUTH_SECRET", "")
    if len(key) < 32:
        key = os.environ["AUTH_SECRET"] = secrets.token_urlsafe(48)
        env = llm.env_file()
        lines = env.read_text(encoding="utf-8-sig").splitlines() if env.exists() else []
        env.write_text("\n".join([l for l in lines if not l.startswith("AUTH_SECRET=")] + [f"AUTH_SECRET={key}"]) + "\n", encoding="utf-8")
    return key
