from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from backend.brain import wiki
from backend.region import Code, use

from .. import store

router = APIRouter(tags=["cases"])


class Verdict(BaseModel):
    verdict: Literal["confirmed", "cleared", "inconclusive"]
    reasoning: str = Field(min_length=10, description="Why the investigator decided this; becomes precedent")
    investigator: str = Field(min_length=2)
    pattern: Optional[str] = Field(None, description="Set to correct the pattern the system proposed")
    lesson: Optional[str] = Field(None, description="The lesson shown in the preview; sent back so the approved text is what is saved")


def _case(case_id):
    cases = store.data().CASES
    if case_id not in cases:
        raise HTTPException(404, f"Unknown case {case_id}")
    return cases[case_id]


@router.get("/cases/{case_id}")
def get_case(case_id: str, horizon: int = Query(90, enum=[30, 60, 90]), region: Code = "us"):
    with use(region):
        _case(case_id)
        return store.detail(case_id, horizon)


def _write(case_id, v, dry_run):
    case = _case(case_id)
    if v.pattern and v.pattern not in wiki.patterns():
        raise HTTPException(422, f"Unknown pattern {v.pattern}")
    return wiki.ingest(case, v.verdict, v.reasoning.strip(), v.investigator.strip(), store.data().PROV_INFO,
                       pattern=v.pattern, lesson=None if dry_run else (v.lesson or ""), dry_run=dry_run)


@router.post("/cases/{case_id}/verdict/preview")
def preview_verdict(case_id: str, v: Verdict, region: Code = "us"):
    """Show which Second Brain pages would change. Nothing is written."""
    with use(region):
        return {"case_id": case_id, "written": False, **_write(case_id, v, dry_run=True)}


@router.post("/cases/{case_id}/verdict")
def post_verdict(case_id: str, v: Verdict, region: Code = "us"):
    """Human-approved writeback: the verdict becomes a case page and updates the linked pages."""
    with use(region):
        return {"case_id": case_id, "written": True, **_write(case_id, v, dry_run=False), "status": store.status_of(case_id)}

@router.get("/cases/{case_id}/fhir")
def export_fhir(case_id: str, region: Code = "us"):
    with use(region):
        case = _case(case_id)
    india = region == "in"
    from datetime import datetime
    return {
        "resourceType": "ExplanationOfBenefit",
        "id": f"eob-{case_id.lower()}",
        "status": "active",
        "type": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/claim-type", "code": "institutional"}]},
        "use": "claim",
        "patient": {"reference": "Patient/TOKENIZED-MEMBER-MASKED"},
        "created": datetime.utcnow().isoformat() + "Z",
        "insurer": {"display": "National Health Authority / State Health Agency (PM-JAY)" if india else "State Medicaid Agency (CMS-Aligned)"},
        "provider": {"reference": f"{'Organization' if india else 'Practitioner'}/{case.get('provider_id', 'UNKNOWN')}"},
        "outcome": "complete",
        "extension": [
            {"url": "http://acentra.com/fhir/StructureDefinition/nist-governance", "valueString": "Aligned with NIST AI RMF: Probabilistic score for human review only."}
        ]
    }
