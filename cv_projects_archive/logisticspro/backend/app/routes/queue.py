from fastapi import APIRouter, Query

from .. import store

router = APIRouter(tags=["queue"])


@router.get("/queue")
def get_queue(horizon: int = Query(90, enum=[30, 60, 90]), investigators: int = Query(3, ge=0, le=50)):
    """Ranked SIU queue. Priority blends risk, dollars, member impact, severity and confidence;
    investigators x 5 cases sets how many open cases fit this week's capacity."""
    return store.queue(horizon, investigators)


@router.get("/metrics")
def get_metrics():
    """Evaluation against the injected synthetic scenarios, plus model cross-validation scores."""
    return store.METRICS
