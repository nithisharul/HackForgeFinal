from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.brain import llm, wiki

from backend.security import log_integrity, prompt_scanner, security_events

from .. import auth, store

router = APIRouter(tags=["second brain"])
GROUPS = ("patterns", "networks", "sources", "notes", "providers", "cases", "rules", "data", "process", "system", "regulatory")


class Question(BaseModel):
    question: str = Field(min_length=5, max_length=500)


class Note(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    answer: str = Field(min_length=10)
    approved_by: str = Field("", description="Ignored: the signed-in investigator is recorded")


class Source(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    text: str = Field(min_length=40, max_length=40000)
    approved_by: str = Field("", description="Ignored when saving: the signed-in investigator is recorded")
    proposal: Optional[dict] = Field(None, description="The proposal returned by the preview, sent back unchanged or edited")


@router.get("/wiki")
def list_pages():
    """Every page in the Second Brain, grouped by type, plus whether an LLM is connected."""
    out = {g: [] for g in GROUPS} | {"other": []}
    for name, path in sorted(wiki.pages().items()):
        out[path.parent.name if path.parent.name in out else "other"].append(name)
    return out | {"llm": llm.status()}


@router.get("/wiki/lint")
def lint():
    """Health check: broken links, orphan pages, patterns that are mostly cleared."""
    return wiki.lint()


@router.get("/wiki/page/{name}")
def page(name: str):
    meta, body = wiki.read(name)
    if meta is None and body is None:
        raise HTTPException(404, f"No page named {name}")
    backlinks = sorted(n for n, p in wiki.pages().items()
                       if n != name and name in wiki.LINK.findall(p.read_text(encoding="utf-8")))
    return {"name": name, "meta": meta, "body": body, "backlinks": backlinks}


@router.post("/wiki/ask")
def ask(q: Question):
    """Query: read the index, choose pages, read them, answer with [[citations]]."""
    return wiki.ask(q.question.strip())


@router.post("/wiki/notes")
def file_note(n: Note, who: str = Depends(auth.require_investigator)):
    """Keep an answer as a page so later questions can build on it. Needs a signed-in investigator."""
    result = wiki.file_note(n.question.strip(), n.answer, who, store.PROV_INFO)
    log_integrity.record_change(who, "kept_answer", result["note_id"], result["changes"], detail=n.question.strip())
    return result


def _screen(title, text, actor, proposal=None):
    """Scan a document (and any proposal sent back with it) before the LLM or the wiki sees it. HIGH findings block."""
    extra = ""
    if proposal:
        np = proposal.get("new_pattern") or {}
        extra = " ".join([str(proposal.get("summary", ""))] + [str(k) for k in proposal.get("key_points", [])]
                         + [str(x.get("note", "")) for x in proposal.get("pattern_notes", []) if isinstance(x, dict)]
                         + [str(np.get(k, "")) for k in ("title", "definition", "signals", "innocent_explanations")])
    report = prompt_scanner.scan(title, f"{text}\n{extra}")
    if report["blocked"]:
        worst = next(f for f in report["findings"] if f["severity"] == "HIGH")
        event = security_events.record("PROMPT_INJECTION_DETECTED", "HIGH", "Document scanner",
                                       f"'{title}': {worst['message']}. Excerpt: {worst['excerpt']}", "BLOCKED", actor=actor)
        raise HTTPException(422, f"Blocked by the document scanner: this text {worst['message']} (\"{worst['excerpt']}\"). "
                                 f"Nothing was sent to the LLM or saved. Security event {event} recorded.")
    return report


@router.post("/wiki/sources/preview")
def preview_source(s: Source):
    """Ingest, step 1: read a document and show the pages it would create or change. Writes nothing."""
    report = _screen(s.title.strip(), s.text, actor="")
    return wiki.ingest_source(s.title.strip(), s.text, s.approved_by, store.PROV_INFO, dry_run=True) | {"security": report}


@router.post("/wiki/sources")
def add_source(s: Source, who: str = Depends(auth.require_lead)):
    """Ingest, step 2: a signed-in investigator approves; the raw file, summary page and linked pages are saved."""
    proposal = s.proposal
    if proposal is not None:
        ok = isinstance(proposal.get("summary"), str) and isinstance(proposal.get("key_points"), list) \
            and all(isinstance(n, dict) and n.get("pattern") in wiki.PATTERNS for n in proposal.get("pattern_notes", []))
        if not ok:
            raise HTTPException(422, "proposal is malformed")
        proposal.setdefault("pattern_notes", [])
        if proposal.get("new_pattern") is not None and not isinstance(proposal["new_pattern"], dict):
            raise HTTPException(422, "new_pattern must be an object or null")
    report = _screen(s.title.strip(), s.text, who, proposal)
    result = wiki.ingest_source(s.title.strip(), s.text, who, store.PROV_INFO, proposal=proposal)
    if report["findings"]:
        security_events.record("SUSPICIOUS_DOCUMENT_APPROVED", "MEDIUM", "Document scanner",
                               f"{result['source_id']} '{s.title.strip()}': " + "; ".join(f["message"] for f in report["findings"]),
                               "ALLOWED BY APPROVER", actor=who)
    log_integrity.record_change(who, "new_pattern" if result.get("new_pattern_id") else "source_document", result["source_id"],
                                result["changes"], extra=[f"sources/documents/{result['source_id']}.md"], detail=s.title.strip())
    return result | {"security": report}
