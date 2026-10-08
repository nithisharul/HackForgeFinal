"""Sign-in for writes to the Second Brain: verdicts, kept answers and source documents.

Reads and previews stay open. Every write needs a session token from POST /api/auth/login, checked on
this server, so a request sent straight to the tunnel URL is refused too. Investigators exist only in
the host's .env file (git-ignored), never in the frontend bundle or the Cloudflare configuration:

    AUTH_SECRET    random key that signs session tokens
    INVESTIGATORS  "name:pbkdf2_sha256$iterations$salt$hash" entries separated by ";"

Add an investigator or change a passcode (prompts for it; restart the API afterwards):

    python -m backend.app.auth add "Investigator Name"

Without both variables every write is refused (fail closed).
"""
import base64
import functools
import hashlib
import hmac
import json
import os
import secrets
import sys
import threading
import time

from fastapi import Header, HTTPException

from backend.brain import llm
from backend.pipeline.common import ROOT

ITERATIONS = 310_000            # PBKDF2-HMAC-SHA256 work factor (OWASP recommendation)
SESSION_SECONDS = 8 * 3600
MAX_FAILURES, LOCKOUT_SECONDS = 5, 300
DISABLED = "Writes are disabled: no investigators are configured on this server"
_failures, _lock = {}, threading.Lock()


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
    users = {}
    for item in os.getenv("INVESTIGATORS", "").split(";"):
        name, _, stored = item.strip().rpartition(":")
        if name.strip() and stored:
            users[_key(name)] = (" ".join(name.split()), stored)
    return os.getenv("AUTH_SECRET", ""), users


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
    return {"token": f"{body}.{_mac(body, secret)}", "investigator": user[0], "expires": payload["exp"]}


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


def require_investigator(authorization: str = Header("")):
    """FastAPI dependency for every write: the signed-in investigator's name, or 401."""
    if not enabled():
        raise HTTPException(503, DISABLED)
    scheme, _, token = authorization.partition(" ")
    name = verify(token.strip()) if scheme.lower() == "bearer" else None
    if not name:
        raise HTTPException(401, "Sign in as an investigator to approve changes", headers={"WWW-Authenticate": "Bearer"})
    return name


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
    out = [l for l in lines if l.split("=", 1)[0].strip() not in updates]
    out += [f"{k}={v}" for k, v in updates.items()]
    env_path.write_text("\n".join(out) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "add":
        sys.exit('usage: python -m backend.app.auth add "Investigator Name"   (passcode is prompted, or read from stdin)')
    if sys.stdin.isatty():
        import getpass
        first, second = getpass.getpass("Passcode: "), getpass.getpass("Repeat passcode: ")
        if first != second:
            sys.exit("Passcodes do not match")
    else:
        first = sys.stdin.readline().rstrip("\n")
    add_investigator(sys.argv[2], first)
    print(f"Investigator {sys.argv[2]!r} saved to .env. Restart the API to apply.")
