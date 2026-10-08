from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from .. import auth

router = APIRouter(tags=["auth"])


class Login(BaseModel):
    investigator: str = Field(min_length=2, max_length=80)
    passcode: str = Field(min_length=1, max_length=200)


@router.post("/auth/login")
def login(body: Login):
    """Exchange an investigator name and passcode for a session token (8 hours). Needed for every write."""
    return auth.login(body.investigator, body.passcode)


@router.get("/auth/session")
def session(investigator: str = Depends(auth.require_investigator)):
    """Who the bearer token belongs to; 401 when it is missing, forged or expired."""
    return {"investigator": investigator}


@router.get("/auth/status")
def status():
    """Whether this server accepts writes at all (an investigator is configured)."""
    return {"writes_enabled": auth.enabled()}
