import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from backend.integrations import notify
from backend.region import Code, use

from .. import auth, store

router = APIRouter(tags=["integrations"])


@router.get("/integrations")
def integrations(_: str = Depends(auth.require_admin)):
    """Admin: configured Slack, Teams and webhook channels (addresses masked) and the last 50 deliveries."""
    return notify.status()


@router.post("/integrations/test")
def test_notification(region: Code = "us", actor: str = Depends(auth.require_admin)):
    """Admin: send a test event to every configured channel and report each delivery."""
    if not notify.channels():
        raise HTTPException(409, "No channel is configured. Set SLACK_WEBHOOK_URL, TEAMS_WEBHOOK_URL or WEBHOOK_URLS in .env and restart.")
    event_id = notify.emit("integration.test", {"message": f"Test notification sent by {actor}", "actor": actor}, region)
    notify.flush(timeout=20)
    return {"event_id": event_id, "deliveries": [d for d in notify.status()["recent"] if d["event_id"] == event_id]}


COLUMNS = ("rank", "case_id", "provider_id", "provider_name", "specialty", "city", "pattern", "network", "tier", "route",
           "confidence", "risk_score", "priority", "potential_dollars", "member_impact", "in_capacity", "status")


@router.get("/queue/export")
def export_queue(horizon: int = Query(90, enum=[30, 60, 90]), investigators: int = Query(3, ge=0, le=50), region: Code = "us"):
    """The ranked queue as CSV, for a case-management system or a spreadsheet. Same order and capacity line as the app."""
    with use(region):
        rows = store.queue(horizon, investigators)["cases"]
    out = io.StringIO()
    w = csv.DictWriter(out, fieldnames=COLUMNS, extrasaction="ignore", lineterminator="\n")
    w.writeheader()
    # A text cell starting with = + - @ would run as a formula in a spreadsheet; a leading apostrophe keeps it text.
    safe = lambda v: "'" + v if isinstance(v, str) and v[:1] in ("=", "+", "-", "@") else v
    w.writerows({k: safe(v) for k, v in r.items()} for r in rows)
    return Response(out.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": f'attachment; filename="claimshield-queue-{region}-{horizon}d.csv"'})
