"""Running the API behind a load balancer: request IDs, structured access logs, security headers and CORS.

    CORS_ORIGINS   comma-separated browser origins allowed to call the API from another site. Default: the local
                   dev servers only. The React app is served from the same origin (Vite proxy, Cloudflare Worker),
                   so it needs no entry. "*" allows any origin.
    LOG_FORMAT     "json" (default) writes one JSON line per request to stdout for a log collector, in place of
                   uvicorn's access log (which records query strings); "off" restores uvicorn's log.

Every response carries X-Request-ID (taken from the caller when it sends one, so a trace crosses systems).
API responses are marked no-store: case data must not sit in shared or browser caches.
"""
import json
import logging
import os
import re
import time
import uuid

from backend.brain import llm

log = logging.getLogger("claimshield.access")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


def cors_origins():
    llm._env()
    raw = os.getenv("CORS_ORIGINS", "")
    if not raw.strip():
        return ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173"]
    return [o.strip().rstrip("/") for o in raw.split(",") if o.strip()]


class RequestContext:
    """Pure ASGI middleware (no extra dependencies), so it also wraps streaming and error responses."""

    def __init__(self, app):
        self.app = app
        if not log.handlers:
            h = logging.StreamHandler()
            h.setFormatter(logging.Formatter("%(message)s"))
            log.addHandler(h)
            log.setLevel(logging.INFO)
            log.propagate = False
        if os.getenv("LOG_FORMAT", "json") != "off":
            logging.getLogger("uvicorn.access").disabled = True  # its lines include query strings; this log replaces it

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        incoming = dict(scope.get("headers") or []).get(b"x-request-id", b"").decode("latin-1")
        rid = incoming if _SAFE_ID.match(incoming) else uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = rid
        t0, status = time.perf_counter(), [500]
        https = scope.get("scheme") == "https" or dict(scope.get("headers") or []).get(b"x-forwarded-proto") == b"https"

        async def wrapped(message):
            if message["type"] == "http.response.start":
                status[0] = message["status"]
                headers = list(message.get("headers") or [])
                present = {k.lower() for k, _ in headers}
                extra = dict(HEADERS, **{"X-Request-ID": rid})
                if scope["path"].startswith("/api/"):
                    extra["Cache-Control"] = "no-store"
                if https:
                    extra["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
                headers += [(k.lower().encode(), v.encode()) for k, v in extra.items() if k.lower().encode() not in present]
                message = dict(message, headers=headers)
            await send(message)

        try:
            await self.app(scope, receive, wrapped)
        finally:
            if os.getenv("LOG_FORMAT", "json") != "off":
                # The path only, never the query string or body: they can carry identifiers.
                log.info(json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"), "request_id": rid, "method": scope["method"],
                                     "path": scope["path"], "status": status[0], "ms": round((time.perf_counter() - t0) * 1000, 1)}))
