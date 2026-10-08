"""Query the Second Brain: index -> pattern page -> linked cases -> provider page.

No vector search. Retrieval follows the wiki's own links, so every item returned
is a page a human can open and read.
"""
import contextvars
from contextlib import contextmanager

from . import wiki

# Precedents left out of retrieval for a what-if ("rank the queue as if this verdict were revoked").
_EXCLUDED = contextvars.ContextVar("excluded_precedents", default=frozenset())


@contextmanager
def excluding(ids):
    token = _EXCLUDED.set(frozenset(ids) | _EXCLUDED.get())
    try:
        yield
    finally:
        _EXCLUDED.reset(token)


def similarity(case, prec):
    """How closely a closed case matches the open one. Returns (score, reasons)."""
    score, why = 0.0, []
    if prec["pattern"] == case["pattern"]:
        score += 0.6
        why.append("same pattern")
    if prec.get("specialty") == case["specialty"]:
        score += 0.25
        why.append("same specialty")
    if prec["provider"] == case["provider_id"]:
        score += 0.15
        why.append("same provider")
    net = (case.get("network") or {}).get("cluster_id")
    if net and prec.get("network") == net:
        score += 0.3
        why.append(f"same network {net}")
    return min(score, 1.0), why


def _matching(case, metas):
    """Closed cases that can serve as precedent for this one: same pattern or same provider."""
    for p in metas:
        if p["id"] != case["case_id"] and (p["pattern"] == case["pattern"] or p["provider"] == case["provider_id"]):
            yield p


def precedents(case, k=3, exclude=(), metas=None):
    out = []
    skip = set(exclude) | _EXCLUDED.get()
    for p in _matching(case, wiki.case_metas() if metas is None else metas):
        if p.get("revoked") or p["id"] in skip:
            continue
        s, why = similarity(case, p)
        out.append({"case_id": p["id"], "provider_id": p["provider"], "specialty": p.get("specialty", ""),
                    "pattern": p["pattern"], "verdict": p["verdict"], "closed": p.get("closed", ""),
                    "source": p.get("source", ""), "network": p.get("network", ""),
                    "evidence": [e for e in p["evidence"].split("|") if e] if "evidence" in p else None,
                    "similarity": round(s, 2), "why": why, "reasoning": wiki.reasoning_of(p)})
    out.sort(key=lambda p: (p["similarity"], p["source"] == "live", p["closed"]), reverse=True)
    return out[:k]


def revoked(case, metas=None):
    """Matching verdicts an investigator withdrew as precedent. Listed for the audit trail; they carry no weight."""
    return [{"case_id": p["id"], "verdict": p["verdict"], "closed": p.get("closed", ""), "revoked": p["revoked"],
             "revoked_by": p.get("revoked_by", ""), "reason": p.get("revoke_reason", "")}
            for p in _matching(case, wiki.case_metas() if metas is None else metas) if p.get("revoked")]


def query(case):
    trail = ["index"]
    meta, body = wiki.read(case["pattern"])
    trail.append(case["pattern"])
    pat = wiki.patterns()[case["pattern"]]
    metas = wiki.case_metas()
    precs = precedents(case, metas=metas)
    trail += [p["case_id"] for p in precs]
    net = (case.get("network") or {}).get("cluster_id")
    if net and wiki.read(net)[0]:
        trail.append(net)
    pmeta, _ = wiki.read(case["provider_id"])
    if pmeta:
        trail.append(case["provider_id"])
    return {
        "pattern": {"id": case["pattern"], "title": pat["title"], "definition": pat["definition"],
                    "innocent_explanations": _innocent(body, pat)},
        "policy": {"id": pat["policy"], "title": pat["policy_title"], "text": pat["policy_text"],
                   "path": wiki.policy_path(pat["policy"]), "public_basis": pat["public_basis"],
                   "note": "Synthetic policy written for this prototype"},
        "precedents": precs,
        "revoked_precedents": revoked(case, metas),
        "provider_has_history": bool(pmeta),
        "pages_read": trail,
    }


def _innocent(body, pat):
    if not body or "## Known innocent explanations" not in body:
        return pat["innocent"]
    block = body.split("## Known innocent explanations", 1)[1].split("\n## ", 1)[0]
    return [l[2:].strip() for l in block.splitlines() if l.startswith("- ")]
