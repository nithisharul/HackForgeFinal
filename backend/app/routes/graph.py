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


@router.get("/graph/{provider_id}/ringshield")
def get_ringshield(provider_id: str, region: Code = "us"):
    """Read-only stress test of the detected network containing a provider."""
    with use(region):
        if provider_id not in store.data().PROV_INFO:
            raise HTTPException(404, f"Unknown provider {provider_id}")
        result = store.ring_shield(provider_id)
        if result is None:
            raise HTTPException(404, f"Provider {provider_id} is not in a detected network")
        return result
