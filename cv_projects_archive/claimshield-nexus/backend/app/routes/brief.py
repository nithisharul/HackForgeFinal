from fastapi import APIRouter, HTTPException, Query

from .. import store

router = APIRouter(tags=["brief"])


@router.get("/cases/{case_id}/brief")
def get_brief(case_id: str, horizon: int = Query(90, enum=[30, 60, 90])):
    """Investigation brief: evidence, timeline, network context, confidence, limitations, recommended action."""
    if case_id not in store.CASES:
        raise HTTPException(404, f"Unknown case {case_id}")
    return store.detail(case_id, horizon)["brief"]
