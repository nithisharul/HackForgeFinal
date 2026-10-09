from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from fastapi import HTTPException

from backend.security import log_integrity, security_events

from .. import auth

router = APIRouter(tags=["auth"])


class Login(BaseModel):
    investigator: str = Field(min_length=2, max_length=80)
    passcode: str = Field(min_length=1, max_length=200)


@router.post("/auth/login")
def login(body: Login):
    """Exchange an investigator name and passcode for a session token (8 hours). Needed for every write."""
    try:
        return auth.login(body.investigator, body.passcode)
    except HTTPException as e:
        if e.status_code == 429:
            security_events.record("ACCOUNT_LOCKOUT", "HIGH", "Sign-in", f"Repeated failed sign-ins for '{body.investigator[:80]}'",
                                   "LOCKED FOR 5 MINUTES", once=False)
        raise


class Register(BaseModel):
    investigator: str = Field(min_length=2, max_length=80)
    passcode: str = Field(min_length=12, max_length=200)


class RoleChange(BaseModel):
    investigator: str = Field(min_length=2, max_length=80)
    role: str


@router.post("/auth/register")
def register(body: Register):
    """Create an account. The first account becomes the admin; later ones are read-only until an admin gives a role."""
    out = auth.register(body.investigator, body.passcode)
    log_integrity.append(out["investigator"], "account_created", out["investigator"], f"role {out['role']}")
    return out


@router.get("/auth/session")
def session(investigator: str = Depends(auth.require_signed_in)):
    """Who the bearer token belongs to and their current role; 401 when it is missing, forged or expired."""
    return {"investigator": investigator, "role": auth.role_of(investigator)}


@router.get("/auth/users")
def users(_: str = Depends(auth.require_admin)):
    """Admin: every account and its role. Passcode hashes are never returned."""
    return {"users": auth.list_users(), "roles": list(auth.ROLES)}


@router.post("/auth/users/role")
def change_role(body: RoleChange, actor: str = Depends(auth.require_admin)):
    """Admin: change an account's role. Takes effect on that person's next request."""
    out = auth.set_role(actor, body.investigator, body.role)
    log_integrity.append(actor, "role_change", out["investigator"], f"role set to {out['role']}")
    return out


@router.get("/auth/status")
def status():
    """Whether this server accepts writes at all (an account exists)."""
    return {"writes_enabled": auth.enabled()}
