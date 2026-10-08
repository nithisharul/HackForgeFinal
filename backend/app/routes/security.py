from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from backend.security import log_integrity, security_events

from .. import auth

router = APIRouter(tags=["security"])


class Reseal(BaseModel):
    reason: str = Field(min_length=10, max_length=300)


@router.get("/security/status")
def status():
    """Integrity of the audit log and of every knowledge file, plus a count of security events. Open, read-only."""
    return log_integrity.verify() | {"events": security_events.counts()}


@router.get("/security/audit")
def audit(limit: int = 100, _: str = Depends(auth.require_lead)):
    """The signed audit trail, newest first: who approved what and when. Lead or admin."""
    return {"entries": log_integrity.entries(min(max(limit, 1), 500))}


@router.get("/security/events")
def events(limit: int = 50, _: str = Depends(auth.require_lead)):
    """What the defences caught: blocked documents, tampering, lockouts, refused actions. Lead or admin."""
    return {"events": security_events.recent(min(max(limit, 1), 200))}


@router.post("/security/reseal")
def reseal(body: Reseal, actor: str = Depends(auth.require_admin)):
    """Admin: after investigating a tampering alert and restoring the files, accept the current files as trusted.
    The decision and the reason are themselves written to the signed log."""
    seq = log_integrity.seal(actor, body.reason)
    security_events.record("KNOWLEDGE_RESEALED", "HIGH", "Integrity check", f"{actor}: {body.reason}", "ACCEPTED CURRENT FILES", actor=actor)
    return {"sealed": True, "entry": seq} | log_integrity.verify(raise_events=False)
