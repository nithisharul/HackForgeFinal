from fastapi import APIRouter, HTTPException

from .. import store

router = APIRouter(tags=["graph"])


@router.get("/graph/{provider_id}")
def get_graph(provider_id: str):
    """Relationship graph around one provider: shared members, referrals, ownership, facilities."""
    if provider_id not in store.PROV_INFO:
        raise HTTPException(404, f"Unknown provider {provider_id}")
    return store.graph(provider_id)
