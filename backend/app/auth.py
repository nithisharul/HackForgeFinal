"""Sign-in for writes to the Second Brain: verdicts, kept answers and source documents.

Reads and previews stay open. Every write needs a session token from POST /api/auth/login, checked on
this server, so a request sent straight to the API is refused too.

Accounts live in a SQLite database (data/app.db, git-ignored): name, PBKDF2 passcode hash and role.
    POST /api/auth/register   create an account. The first account becomes the admin; every later
                              account starts as a read-only viewer until an admin gives it a role.
    POST /api/auth/login      exchange name and passcode for a session token
    GET  /api/auth/users      admin: list accounts        POST /api/auth/users/role   admin: change a role

Roles, each including the ones before it:
    viewer        read only
    investigator  record verdicts, keep answers
    lead          approve source documents and new patterns
    admin         manage accounts

The role is read from the database on every request, so a change takes effect at once.

    AUTH_SECRET    random key that signs session tokens (.env; created automatically at first registration)
    INVESTIGATORS  optional legacy accounts in .env, "name:hash" separated by ";". They are admins.

Add an investigator or change a passcode (prompts for it; restart the API afterwards):

    python -m backend.app.auth add "Investigator Name"

Rotate the signing key (signs out every current session; restart the API afterwards):

    python -m backend.app.auth rotate-secret

Without both variables every write is refused (fail closed).
"""
import base64
import contextlib
import datetime as dt
import functools
import hashlib
import hmac
import json
import os
import secrets
import sqlite3
import sys
import threading
import time

from pathlib import Path

from fastapi import Header, HTTPException

from backend.brain import llm
from backend.pipeline.common import ROOT

ITERATIONS = 310_000            # PBKDF2-HMAC-SHA256 work factor (OWASP recommendation)
SESSION_SECONDS = 8 * 3600
MAX_FAILURES, LOCKOUT_SECONDS = 5, 300
DISABLED = "Writes are disabled: no account exists on this server yet. Register the first account to become the admin."
ROLES = ("viewer", "investigator", "lead", "admin")
MAX_ACCOUNTS = 200
_failures, _lock = {}, threading.Lock()


# ------------------------------------------------------------------- accounts ---
def _db():
    path = Path(os.getenv("AUTH_DB") or ROOT / "data" / "app.db")
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path, timeout=5)
    con.execute("CREATE TABLE IF NOT EXISTS users (key TEXT PRIMARY KEY, name TEXT NOT NULL, passcode_hash TEXT NOT NULL, "
                "role TEXT NOT NULL, created TEXT NOT NULL, created_by TEXT NOT NULL)")
    return con


def _db_users():
    with contextlib.closing(_db()) as con:
        return {k: (name, stored, role if role in ROLES else "viewer")
                for k, name, stored, role in con.execute("SELECT key, name, passcode_hash, role FROM users")}


# ------------------------------------------------------------------ passcodes ---
def hash_passcode(passcode, salt=None, iterations=ITERATIONS):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", passcode.encode(), bytes.fromhex(salt), iterations).hex()
    return f"pbkdf2_sha256${iterations}${salt}${digest}"


def check_passcode(passcode, stored):
    try:
        algo, iterations, salt, digest = stored.split("$")
        return algo == "pbkdf2_sha256" and hmac.compare_digest(hash_passcode(passcode, salt, int(iterations)), stored)
    except ValueError:
        return False


@functools.cache
def _decoy():
    """Checked when the name is unknown, so a wrong name takes as long as a wrong passcode."""
    return hash_passcode(secrets.token_hex(8))


def _key(name):
    return " ".join(str(name).split()).casefold()


def _config():
    llm._env()  # loads the project .env once, like the LLM settings
    users = _db_users()
    for item in os.getenv("INVESTIGATORS", "").split(";"):
        name, _, stored = item.strip().rpartition(":")
        if name.strip() and stored:
            users[_key(name)] = (" ".join(name.split()), stored, "admin")  # .env accounts are admins and win on a name clash
    return os.getenv("AUTH_SECRET", ""), users


def _env_keys():
    return {_key(i.strip().rpartition(":")[0]) for i in os.getenv("INVESTIGATORS", "").split(";") if i.strip().rpartition(":")[0].strip()}


def register(name, passcode, env_path=None):
    """Create an account. The first account on the server is the admin; later ones are read-only viewers."""
    name = " ".join(str(name).split())
    if not 2 <= len(name) <= 80 or not all(ch.isalnum() or ch in " .'-_" for ch in name):
        raise HTTPException(422, "Use a name of 2-80 letters, digits, spaces, dots, hyphens or apostrophes")
    if len(passcode) < 12:
        raise HTTPException(422, "Use a passcode of at least 12 characters")
    secret, users = _config()
    if _key(name) in users:
        raise HTTPException(409, "That name is already registered")
    if len(users) >= MAX_ACCOUNTS:
        raise HTTPException(403, "Account limit reached; ask an admin")
    if len(secret) < 32:  # first use on this server: create the signing key
        os.environ["AUTH_SECRET"] = secrets.token_urlsafe(48)
        env_path = env_path or ROOT / ".env"
        lines = env_path.read_text(encoding="utf-8-sig").splitlines() if env_path.exists() else []
        _write_env(env_path, lines, {"AUTH_SECRET": os.environ["AUTH_SECRET"]})
    role = "viewer" if users else "admin"
    try:
        with contextlib.closing(_db()) as con, con:
            if role == "admin" and con.execute("SELECT COUNT(*) FROM users").fetchone()[0]:
                role = "viewer"  # someone else registered first
            con.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                        (_key(name), name, hash_passcode(passcode), role, dt.datetime.now().isoformat(timespec="seconds"), "self"))
    except sqlite3.IntegrityError:
        raise HTTPException(409, "That name is already registered")
    return {"investigator": name, "role": role,
            "message": "You are the first account, so you are the admin." if role == "admin"
            else "Account created as a read-only viewer. An admin must give you a role before you can approve changes."}


def list_users():
    env = _env_keys()
    with contextlib.closing(_db()) as con:
        rows = [{"investigator": n, "role": r, "created": c, "source": "database"}
                for k, n, r, c in con.execute("SELECT key, name, role, created FROM users ORDER BY created") if k not in env]
    _, users = _config()
    return [{"investigator": users[k][0], "role": "admin", "created": "", "source": ".env"} for k in sorted(env)] + rows


def set_role(actor, name, role):
    if role not in ROLES:
        raise HTTPException(422, f"Role must be one of {', '.join(ROLES)}")
    key, (_, users) = _key(name), _config()
    if key in _env_keys():
        raise HTTPException(403, "This account is defined in .env and cannot be changed here")
    if key not in users:
        raise HTTPException(404, "No such account")
    admins = [k for k, u in users.items() if u[2] == "admin"]
    if users[key][2] == "admin" and role != "admin" and admins == [key]:
        raise HTTPException(409, "This is the only admin; make someone else an admin first")
    with contextlib.closing(_db()) as con, con:
        con.execute("UPDATE users SET role = ?, created_by = ? WHERE key = ?", (role, actor, key))
    return {"investigator": users[key][0], "role": role, "changed_by": actor}


def enabled():
    secret, users = _config()
    return len(secret) >= 32 and bool(users)


# ------------------------------------------------------------------- sessions ---
def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _mac(body, secret):
    return _b64(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())


def login(name, passcode):
    secret, users = _config()
    if len(secret) < 32 or not users:
        raise HTTPException(503, DISABLED)
    key, now = _key(name), time.time()
    with _lock:
        n, since = _failures.get(key, (0, now))
        if n >= MAX_FAILURES and now - since < LOCKOUT_SECONDS:
            raise HTTPException(429, "Too many failed sign-ins for this name. Try again in a few minutes.")
    user = users.get(key)
    if not check_passcode(passcode, user[1] if user else _decoy()) or not user:
        with _lock:
            n, since = _failures.get(key, (0, now))
            _failures[key] = (1, now) if now - since >= LOCKOUT_SECONDS else (n + 1, since)
            if len(_failures) > 1000:  # attempts with made-up names must not grow memory without bound
                for k in [k for k, (_, t) in _failures.items() if now - t >= LOCKOUT_SECONDS]:
                    del _failures[k]
        raise HTTPException(401, "Unknown investigator or wrong passcode")
    with _lock:
        _failures.pop(key, None)
    payload = {"sub": user[0], "exp": int(now) + SESSION_SECONDS, "nonce": secrets.token_hex(8)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return {"token": f"{body}.{_mac(body, secret)}", "investigator": user[0], "role": user[2], "expires": payload["exp"]}


def verify(token):
    """The investigator a token was issued to, or None if it is forged, expired or for a removed investigator."""
    secret, users = _config()
    if len(secret) < 32 or token.count(".") != 1:
        return None
    body, mac = token.split(".")
    if not hmac.compare_digest(mac, _mac(body, secret)):
        return None
    try:
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except ValueError:
        return None
    if not isinstance(payload, dict) or payload.get("exp", 0) < time.time() or _key(payload.get("sub", "")) not in users:
        return None
    return users[_key(payload["sub"])][0]


def role_of(name):
    user = _config()[1].get(_key(name))
    return user[2] if user else None


def require_role(minimum):
    """FastAPI dependency: the signed-in person's name if their current role is at least `minimum`; else 401 or 403."""
    def check(authorization: str = Header("")):
        if not enabled():
            raise HTTPException(503, DISABLED)
        scheme, _, token = authorization.partition(" ")
        name = verify(token.strip()) if scheme.lower() == "bearer" else None
        if not name:
            raise HTTPException(401, "Sign in to approve changes", headers={"WWW-Authenticate": "Bearer"})
        role = role_of(name) or "viewer"
        if ROLES.index(role) < ROLES.index(minimum):
            from backend.security import security_events
            security_events.record("ROLE_DENIED", "MEDIUM", "Access control", f"{name} ({role}) attempted an action that needs {minimum}",
                                   "REFUSED", actor=name)
            raise HTTPException(403, f"Your role is {role}. This action needs the {minimum} role; ask an admin.")
        return name
    return check


require_investigator = require_role("investigator")   # verdicts, kept answers
require_lead = require_role("lead")                   # source documents, new patterns
require_admin = require_role("admin")                 # accounts
require_signed_in = require_role("viewer")


# ------------------------------------------------------------------------ CLI ---
def add_investigator(name, passcode, env_path=ROOT / ".env"):
    """Create or update an investigator in .env; adds AUTH_SECRET the first time."""
    if len(passcode) < 12:
        raise ValueError("Use a passcode of at least 12 characters")
    lines = env_path.read_text(encoding="utf-8-sig").splitlines() if env_path.exists() else []
    values = {l.split("=", 1)[0].strip(): l.split("=", 1)[1].strip() for l in lines if "=" in l and not l.strip().startswith("#")}
    entries = [e for e in values.get("INVESTIGATORS", "").split(";") if e.strip() and _key(e.rpartition(":")[0]) != _key(name)]
    entries.append(f"{' '.join(name.split())}:{hash_passcode(passcode)}")
    updates = {"INVESTIGATORS": ";".join(entries)}
    if len(values.get("AUTH_SECRET", "")) < 32:
        updates["AUTH_SECRET"] = secrets.token_urlsafe(48)
    _write_env(env_path, lines, updates)


def rotate_secret(env_path=ROOT / ".env"):
    """Replace AUTH_SECRET. Every session token signed with the old key stops working."""
    lines = env_path.read_text(encoding="utf-8-sig").splitlines() if env_path.exists() else []
    _write_env(env_path, lines, {"AUTH_SECRET": secrets.token_urlsafe(48)})


def _write_env(env_path, lines, updates):
    out = [l for l in lines if l.split("=", 1)[0].strip() not in updates]
    out += [f"{k}={v}" for k, v in updates.items()]
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if sys.argv[1:] == ["rotate-secret"]:
        rotate_secret()
        sys.exit("AUTH_SECRET rotated in .env: every current session is signed out. Restart the API to apply.")
    if len(sys.argv) != 3 or sys.argv[1] != "add":
        sys.exit('usage: python -m backend.app.auth add "Investigator Name"   (passcode is prompted, or read from stdin)\n'
                 '       python -m backend.app.auth rotate-secret')
    if sys.stdin.isatty():
        import getpass
        first, second = getpass.getpass("Passcode: "), getpass.getpass("Repeat passcode: ")
        if first != second:
            sys.exit("Passcodes do not match")
    else:
        first = sys.stdin.readline().rstrip("\n")
    add_investigator(sys.argv[2], first)
    print(f"Investigator {sys.argv[2]!r} saved to .env. Restart the API to apply.")
