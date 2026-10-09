"""ClaimShield Nexus API.   uvicorn backend.app.main:app --reload   (run from the project root)"""
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from . import ops
from .routes import auth, brief, cases, graph, integrations, queue, security, wiki

VERSION = "0.2.0"
app = FastAPI(title="ClaimShield Nexus", version=VERSION)
origins = ops.cors_origins()
app.add_middleware(CORSMiddleware, allow_origins=origins, allow_credentials=False,  # bearer tokens, no cookies
                   allow_methods=["GET", "POST"], allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
                   expose_headers=["X-Request-ID"])
app.add_middleware(ops.RequestContext)
for r in (auth, queue, cases, brief, graph, wiki, security, integrations):
    app.include_router(r.router, prefix="/api")


@app.get("/")
def root():
    return {"service": "ClaimShield Nexus", "version": VERSION, "docs": "/docs"}


@app.get("/api/openapi.json", include_in_schema=False)
def openapi_spec():
    """The OpenAPI spec under /api, so it is reachable through the same proxy as the app (the Documentation page reads it)."""
    return app.openapi()


@app.get("/api/health/live", tags=["operations"])
def live():
    """Liveness probe: the process is up and answering."""
    return {"status": "ok", "version": VERSION}


@app.get("/api/health/ready", tags=["operations"])
def ready():
    """Readiness probe: both regions' pipeline outputs load and the account and audit database opens. 503 otherwise."""
    from backend import region
    from backend.security.store import open_db

    from . import store
    checks = {}
    for code in region.REGIONS:
        try:
            with region.use(code):
                checks[f"data_{code}"] = len(store.data().CASES) > 0
        except Exception:  # noqa: BLE001 - any failure means not ready
            checks[f"data_{code}"] = False
    try:
        with open_db() as con:
            con.execute("SELECT 1")
        checks["database"] = True
    except Exception:  # noqa: BLE001
        checks["database"] = False
    ok = all(checks.values())
    return JSONResponse({"status": "ready" if ok else "not ready", "checks": checks}, status_code=200 if ok else 503)


@app.on_event("startup")
def warm_briefs():
    """Prepare every case's LLM text in the background; the API answers immediately meanwhile."""
    from . import store
    threading.Thread(target=store.warm, name="warm-briefs", daemon=True).start()
