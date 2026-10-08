from fastapi import APIRouter, HTTPException, Query

from backend.region import Code, use

from .. import store

router = APIRouter(tags=["brief"])


@router.get("/cases/{case_id}/brief")
def get_brief(case_id: str, horizon: int = Query(90, enum=[30, 60, 90]), region: Code = "us"):
    """Investigation brief: evidence, timeline, network context, confidence, limitations, recommended action."""
    with use(region):
        if case_id not in store.data().CASES:
            raise HTTPException(404, f"Unknown case {case_id}")
        return store.detail(case_id, horizon)["brief"]
