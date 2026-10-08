"""ClaimShield Nexus API.   uvicorn backend.app.main:app --reload   (run from the project root)"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routes import auth, brief, cases, graph, queue, wiki

app = FastAPI(title="ClaimShield Nexus", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
for r in (auth, queue, cases, brief, graph, wiki):
    app.include_router(r.router, prefix="/api")


@app.get("/")
def root():
    return {"service": "ClaimShield Nexus", "docs": "/docs"}
