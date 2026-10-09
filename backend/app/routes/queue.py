from fastapi import APIRouter, Query

from backend.region import Code, use

from .. import store

router = APIRouter(tags=["queue"])


@router.get("/queue")
def get_queue(horizon: int = Query(90, enum=[30, 60, 90]), investigators: int = Query(3, ge=0, le=50), region: Code = "us"):
    """Ranked SIU queue. Priority blends risk, dollars, member impact, severity and confidence;
    investigators x 5 cases sets how many open cases fit this week's capacity."""
    with use(region):
        return store.queue(horizon, investigators)


@router.get("/health")
def get_health(region: Code = "us"):
    """Which detectors ran, how old the results are, whether the LLM is reachable and whether the knowledge is intact.
    The app keeps working when any of them is down; this says what it is working without."""
    with use(region):
        return store.health()


@router.get("/metrics")
def get_metrics(region: Code = "us"):
    """Evaluation against the injected synthetic scenarios, plus model cross-validation scores."""
    with use(region):
        return store.data().METRICS
