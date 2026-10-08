from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from backend.brain import wiki

from backend.security import log_integrity

from .. import auth, store

router = APIRouter(tags=["cases"])


class Verdict(BaseModel):
    verdict: Literal["confirmed", "cleared", "inconclusive"]
    reasoning: str = Field(min_length=10, description="Why the investigator decided this; becomes precedent")
    investigator: str = Field(min_length=2)
    pattern: Optional[str] = Field(None, description="Set to correct the pattern the system proposed")
    lesson: Optional[str] = Field(None, description="The lesson shown in the preview; sent back so the approved text is what is saved")


def _case(case_id):
    if case_id not in store.CASES:
        raise HTTPException(404, f"Unknown case {case_id}")
    return store.CASES[case_id]


@router.get("/cases/{case_id}")
def get_case(case_id: str, horizon: int = Query(90, enum=[30, 60, 90])):
    _case(case_id)
    return store.detail(case_id, horizon)


def _write(case_id, v, dry_run):
    case = _case(case_id)
    if v.pattern and v.pattern not in wiki.PATTERNS:
        raise HTTPException(422, f"Unknown pattern {v.pattern}")
    return wiki.ingest(case, v.verdict, v.reasoning.strip(), v.investigator.strip(), store.PROV_INFO,
                       pattern=v.pattern, lesson=None if dry_run else (v.lesson or ""), dry_run=dry_run)


@router.post("/cases/{case_id}/verdict/preview")
def preview_verdict(case_id: str, v: Verdict):
    """Show which Second Brain pages would change. Nothing is written."""
    return {"case_id": case_id, "written": False, **_write(case_id, v, dry_run=True)}


@router.post("/cases/{case_id}/verdict")
def post_verdict(case_id: str, v: Verdict, who: str = Depends(auth.require_investigator)):
    """Human-approved writeback: the verdict becomes a case page and updates the linked pages.
    Needs a signed-in investigator, whose name is recorded whatever the body says."""
    v = v.model_copy(update={"investigator": who})
    result = _write(case_id, v, dry_run=False)
    log_integrity.record_change(who, "verdict", case_id, result["changes"], detail=f"{v.verdict}: {v.reasoning.strip()}")
    return {"case_id": case_id, "written": True, **result, "status": store.status_of(case_id)}

@router.get("/cases/{case_id}/audit-plan")
def audit_plan(case_id: str, horizon: int = Query(90, enum=[30, 60, 90])):
    """AuditNext: candidate checks ranked by expected information gain per hour. Read-only."""
    from backend.brain import auditnext
    case = _case(case_id)
    _, conf, _ = store.enrich(case, horizon)
    return auditnext.plan(case, conf)


@router.get("/cases/{case_id}/clinical-audit")
def clinical_audit(case_id: str):
    """Provider record review: the LLM compares a returned record with the flagged claims. Read-only."""
    from backend.brain.clinical_audit import audit_case_clinical_chart
    return audit_case_clinical_chart(_case(case_id))


@router.get("/cases/{case_id}/fhir")
def export_fhir(case_id: str):
    case = _case(case_id)
    from datetime import datetime
    return {
        "resourceType": "ExplanationOfBenefit",
        "id": f"eob-{case_id.lower()}",
        "status": "active",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "institutional"}]},
        "use": "claim",
        "patient": {"reference": "Patient/TOKENIZED-MEMBER-MASKED"},
        "created": datetime.utcnow().isoformat() + "Z",
        "insurer": {"display": "State Medicaid Agency (CMS-Aligned)"},
        "provider": {"reference": f"Practitioner/{case.get('provider_id', 'UNKNOWN')}"},
        "outcome": "complete",
        "extension": [
            {"url": "http://acentra.com/fhir/StructureDefinition/nist-governance", "valueString": "Aligned with NIST AI RMF: Probabilistic score for human review only."}
        ]
    }
