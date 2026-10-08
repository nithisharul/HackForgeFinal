from fastapi import APIRouter, HTTPException

from backend.region import Code, use

from .. import store

router = APIRouter(tags=["graph"])


@router.get("/graph/{provider_id}")
def get_graph(provider_id: str, region: Code = "us"):
    """Relationship graph around one provider: shared members, referrals, ownership, facilities (and agents in India)."""
    with use(region):
        if provider_id not in store.data().PROV_INFO:
            raise HTTPException(404, f"Unknown provider {provider_id}")
        return store.graph(provider_id)
