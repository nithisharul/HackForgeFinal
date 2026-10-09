"""Provider record review: the LLM compares a returned record with the flagged claims.

A record is tied to one case: backend/data/clinical_notes/<CASE-ID>.txt. The sample files are
synthetic and written for this prototype.

Fail-safe behaviour
  no record on file   -> status "no_record", nothing is shown as a finding
  LLM off or unusable -> status "unread", the record is shown for the investigator to read
  LLM answers         -> status "read", shown as a possible discrepancy for human review, never as confirmed
"""
import re
from pathlib import Path

from backend import region

from . import llm, refpages
from .brief import saved_llm

NOTES_DIR = Path(__file__).resolve().parent.parent / "data" / "clinical_notes"  # India's records go in clinical_notes/india/
SAFE_ID = re.compile(r"^[A-Za-z0-9-]{3,40}$")


def _meta(text):
    author = re.search(r"(?:ATTENDING PHYSICIAN|PROVIDER|AUTHOR):\s*([^\n\r]+)", text, re.I)
    dos = re.search(r"(?:AUDIT DATE OF SERVICE|DATE OF SERVICE|ACCESSION DATE):\s*([^\n\r]+)", text, re.I)
    return (author.group(1).strip() if author else "Not stated"), (dos.group(1).strip() if dos else "Not stated")


def audit_case_clinical_chart(case):
    case_id, pattern = case["case_id"], case["pattern"]
    out = {"case_id": case_id, "provider_id": case["provider_id"], "pattern": pattern, "source_file": None, "artifact": None}
    path = (NOTES_DIR / "india" if region.current().code == "in" else NOTES_DIR) / f"{case_id}.txt"
    if not SAFE_ID.match(case_id) or not path.exists():
        return out | {"status": "no_record", "message": "No provider record has been received for this case."}

    text = path.read_text(encoding="utf-8-sig")
    author, dos = _meta(text)
    regs = refpages.PATTERN_REGS.get(pattern, [])
    art = {"author": author, "date_of_service": dos, "text_content": text, "discrepancy_found": None,
           "discrepancy_type": "", "finding": "", "model_auditor": None,
           "statute": " / ".join(refpages.REGS[g]["title"] for g in regs) or "See the regulatory pages in the Second Brain"}
    out |= {"source_file": path.name, "artifact": art}

    claims = "\n".join(f"- {s['claim_id']} on {s['date']} at {s['facility_id']}, code {s['procedure_code']}: {s['detail']}"
                       for s in case["sample_claims"][:6])
    def read():  # only a usable reading is saved
        r = llm.chat_json(
            "You help a claims investigator read a provider record. Compare the record with the flagged claims and say "
            "whether the record is inconsistent with what was billed. Use only what the record and claims say. "
            'Return JSON only: {"discrepancy_found": true or false, "discrepancy_type": "a few words", '
            '"finding": "one or two sentences quoting the times, places or codes that matter"}. '
            "Never say fraud occurred; describe the inconsistency.",
            f"Pattern flagged: {pattern.replace('_', ' ')}\n\nFlagged claims:\n{claims}\n\nRecord:\n{text[:6000]}", max_tokens=300)
        usable = isinstance(r, dict) and isinstance(r.get("discrepancy_found"), bool) \
            and isinstance(r.get("finding"), str) and len(r["finding"].strip()) >= 15
        return r if usable else None

    # Saved per record and claims, like the briefs, so the record is read once rather than on every page load.
    res = saved_llm("record", {"case": case_id, "record": text, "claims": claims}, read)
    finding = (res or {}).get("finding")
    if not isinstance(res, dict) or not isinstance(res.get("discrepancy_found"), bool) or not isinstance(finding, str) \
            or len(finding.strip()) < 15:
        return out | {"status": "unread", "message": "The LLM could not read this record. Review it manually."}
    art |= {"discrepancy_found": res["discrepancy_found"], "finding": finding.strip(),
            "discrepancy_type": str(res.get("discrepancy_type") or "").strip()[:80], "model_auditor": llm.config()["model"]}
    return out | {"status": "read", "message": "LLM reading of the record. A lead for review, not a finding."}
