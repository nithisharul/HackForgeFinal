from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.brain import llm, wiki
from backend.region import Code, use

from .. import store

router = APIRouter(tags=["second brain"])
GROUPS = ("patterns", "networks", "sources", "notes", "providers", "cases")


class Question(BaseModel):
    question: str = Field(min_length=5, max_length=500)


class Note(BaseModel):
    question: str = Field(min_length=5, max_length=500)
    answer: str = Field(min_length=10)
    approved_by: str = Field(min_length=2)


class Source(BaseModel):
    title: str = Field(min_length=3, max_length=120)
    text: str = Field(min_length=40, max_length=40000)
    approved_by: str = Field("", description="Required when saving")
    proposal: Optional[dict] = Field(None, description="The proposal returned by the preview, sent back unchanged or edited")


@router.get("/wiki")
def list_pages(region: Code = "us"):
    """Every page in the Second Brain, grouped by type, plus whether an LLM is connected."""
    out = {g: [] for g in GROUPS} | {"other": []}
    with use(region):
        for name, path in sorted(wiki.pages().items()):
            out[path.parent.name if path.parent.name in out else "other"].append(name)
    return out | {"llm": llm.status()}


@router.get("/wiki/lint")
def lint(region: Code = "us"):
    """Health check: broken links, orphan pages, patterns that are mostly cleared."""
    with use(region):
        return wiki.lint()


@router.get("/wiki/page/{name}")
def page(name: str, region: Code = "us"):
    with use(region):
        meta, body = wiki.read(name)
        if meta is None and body is None:
            raise HTTPException(404, f"No page named {name}")
        backlinks = sorted(n for n, p in wiki.pages().items()
                           if n != name and name in wiki.LINK.findall(p.read_text(encoding="utf-8")))
    return {"name": name, "meta": meta, "body": body, "backlinks": backlinks}


@router.post("/wiki/ask")
def ask(q: Question, region: Code = "us"):
    """Query: read the index, choose pages, read them, answer with [[citations]]."""
    with use(region):
        return wiki.ask(q.question.strip())


@router.post("/wiki/notes")
def file_note(n: Note, region: Code = "us"):
    """Keep an answer as a page so later questions can build on it."""
    with use(region):
        return wiki.file_note(n.question.strip(), n.answer, n.approved_by.strip(), store.data().PROV_INFO)


@router.post("/wiki/sources/preview")
def preview_source(s: Source, region: Code = "us"):
    """Ingest, step 1: read a document and show the pages it would create or change. Writes nothing."""
    with use(region):
        return wiki.ingest_source(s.title.strip(), s.text, s.approved_by, store.data().PROV_INFO, dry_run=True)


@router.post("/wiki/sources")
def add_source(s: Source, region: Code = "us"):
    """Ingest, step 2: a named human approves; the raw file, summary page and linked pages are saved."""
    if len(s.approved_by.strip()) < 2:
        raise HTTPException(422, "approved_by is required to save")
    proposal = s.proposal
    with use(region):
        if proposal is not None:
            ok = isinstance(proposal.get("summary"), str) and isinstance(proposal.get("key_points"), list) \
                and all(isinstance(n, dict) and n.get("pattern") in wiki.patterns() for n in proposal.get("pattern_notes", []))
            if not ok:
                raise HTTPException(422, "proposal is malformed")
            proposal.setdefault("pattern_notes", [])
        return wiki.ingest_source(s.title.strip(), s.text, s.approved_by.strip(), store.data().PROV_INFO, proposal=proposal)
