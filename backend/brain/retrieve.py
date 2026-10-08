"""Query the Second Brain: index -> pattern page -> linked cases -> provider page.

No vector search. Retrieval follows the wiki's own links, so every item returned
is a page a human can open and read.
"""
from . import wiki


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


def precedents(case, k=3):
    out = []
    for p in wiki.case_metas():
        if p["id"] == case["case_id"]:
            continue
        s, why = similarity(case, p)
        if p["pattern"] != case["pattern"] and p["provider"] != case["provider_id"]:
            continue
        out.append({"case_id": p["id"], "provider_id": p["provider"], "specialty": p.get("specialty", ""),
                    "pattern": p["pattern"], "verdict": p["verdict"], "closed": p.get("closed", ""),
                    "source": p.get("source", ""), "network": p.get("network", ""),
                    "similarity": round(s, 2), "why": why, "reasoning": wiki.reasoning_of(p)})
    out.sort(key=lambda p: (p["similarity"], p["source"] == "live", p["closed"]), reverse=True)
    return out[:k]


def query(case):
    trail = ["index"]
    meta, body = wiki.read(case["pattern"])
    trail.append(case["pattern"])
    pat = wiki.patterns()[case["pattern"]]
    precs = precedents(case)
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
        "provider_has_history": bool(pmeta),
        "pages_read": trail,
    }


def _innocent(body, pat):
    if not body or "## Known innocent explanations" not in body:
        return pat["innocent"]
    block = body.split("## Known innocent explanations", 1)[1].split("\n## ", 1)[0]
    return [l[2:].strip() for l in block.splitlines() if l.startswith("- ")]
