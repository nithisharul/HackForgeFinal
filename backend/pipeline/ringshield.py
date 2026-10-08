"""RingShield robustness analysis for detected provider networks.

RingShield does not detect a new network and never changes a case score.  It stress-tests
the membership produced by :mod:`backend.pipeline.graph` and keeps corroborating evidence
separate from the shared-member topology that Leiden/Louvain actually used.
"""
from __future__ import annotations

import hashlib
import math
import random
from statistics import mean

import networkx as nx
import pandas as pd

from backend.region import PUBLIC_OWNERS

from .graph import communities


PERTURBATION_LEVELS = (0.10, 0.20, 0.30)
PERTURBATION_TRIALS = 10
STRUCTURAL_WEIGHT = 0.65
SUPPORTING_WEIGHT = 1.0 - STRUCTURAL_WEIGHT
MIN_SHARED = 15
MIN_LIFT = 3.0
MIN_REFERRALS = 15

FAMILY_LABELS = {
    "shared_beneficiaries": "Shared beneficiaries",
    "shared_agents": "Shared agents",
    "referrals": "Referral cycles",
    "common_ownership": "Common ownership",
    "administrative_hubs": "High-degree administrative hubs",
}


def _round(value, digits=3):
    return round(float(value), digits)


def _seed(network_id, level, trial):
    raw = f"ringshield|{network_id}|{level:.2f}|{trial}".encode("utf-8")
    return int.from_bytes(hashlib.sha256(raw).digest()[:8], "big")


def _qualifying_edges(edges, members):
    members = set(members)
    if edges.empty or not {"a", "b", "shared", "lift"}.issubset(edges.columns):
        return []
    selected = edges[
        edges.a.isin(members)
        & edges.b.isin(members)
        & (edges.shared >= MIN_SHARED)
        & (edges.lift >= MIN_LIFT)
    ]
    return sorted((str(r.a), str(r.b), float(r.shared)) for r in selected.itertuples())


def _best_membership(original, groups):
    original = set(original)
    if not original:
        return 0.0, 0
    best_score, best_size = 0.0, 0
    for group in groups:
        group = set(group)
        union = original | group
        score = len(original & group) / len(union) if union else 0.0
        if score > best_score or (score == best_score and len(group) > best_size):
            best_score, best_size = score, len(group)
    return best_score, best_size


def _partition(nodes, weighted_edges):
    graph = nx.Graph()
    graph.add_nodes_from(nodes)
    graph.add_weighted_edges_from(weighted_edges)
    if not weighted_edges:
        return [[node] for node in sorted(nodes)]
    groups, _ = communities(graph)
    return groups


def membership_stability(network_id, members, edges, levels=PERTURBATION_LEVELS, trials=PERTURBATION_TRIALS):
    """Deterministically remove qualifying topology edges and re-partition the network.

    The comparison is label-free: each perturbed partition is matched to the original
    network by maximum Jaccard overlap.  Supporting relationships are intentionally absent.
    """
    members = sorted(set(map(str, members)))
    topology = _qualifying_edges(edges, members)
    if len(members) < 3 or not topology:
        rows = [
            {
                "removal_fraction": level,
                "removed_edges": 0,
                "trials": trials,
                "mean_stability": 0.0,
                "min_stability": 0.0,
                "max_stability": 0.0,
                "mean_largest_members": 0.0,
            }
            for level in levels
        ]
        return {"original_membership_stability": 1.0, "qualifying_edges": len(topology), "perturbations": rows, "mean_stability": 0.0}

    rows = []
    for level in levels:
        remove_n = min(len(topology), max(1, int(round(len(topology) * level))))
        scores, sizes = [], []
        for trial in range(trials):
            rng = random.Random(_seed(network_id, level, trial))
            removed = set(rng.sample(range(len(topology)), remove_n))
            kept = [edge for index, edge in enumerate(topology) if index not in removed]
            score, size = _best_membership(members, _partition(members, kept))
            scores.append(score)
            sizes.append(size)
        rows.append(
            {
                "removal_fraction": level,
                "removed_edges": remove_n,
                "trials": trials,
                "mean_stability": _round(mean(scores)),
                "min_stability": _round(min(scores)),
                "max_stability": _round(max(scores)),
                "mean_largest_members": _round(mean(sizes), 2),
            }
        )
    return {
        "original_membership_stability": 1.0,
        "qualifying_edges": len(topology),
        "perturbations": rows,
        "mean_stability": _round(mean(row["mean_stability"] for row in rows)),
    }


def _agent_evidence(claims, members, excluded=frozenset()):
    if "referred_by_agent_id" not in claims.columns:
        return {"available": False, "score": 0.0, "detail": "Agent data is not available for this region."}
    sub = claims[claims.provider_id.isin(members)]
    agents = sub.referred_by_agent_id.dropna().astype(str)
    agents = agents[~agents.isin(excluded) & agents.ne("")]
    counts = agents.value_counts()
    score = float(counts.iloc[0] / len(sub)) if len(counts) and len(sub) else 0.0
    top = str(counts.index[0]) if len(counts) else ""
    return {
        "available": True,
        "score": _round(score),
        "relationship_count": int(counts.iloc[0]) if len(counts) else 0,
        "top_relationship": top,
        "detail": f"{score:.0%} of network admissions name the same agent ({top})." if top else "No shared agent supports this network.",
    }


def _referral_evidence(referrals, members, excluded=frozenset()):
    required = {"from_provider_id", "to_provider_id"}
    if referrals is None or not required.issubset(referrals.columns):
        return {"available": False, "score": 0.0, "detail": "Referral data is not available for this region."}
    original_members = set(members)
    members = original_members - set(excluded)
    sub = referrals[
        referrals.from_provider_id.isin(members) & referrals.to_provider_id.isin(members)
    ]
    counts = sub.groupby(["from_provider_id", "to_provider_id"]).size()
    graph = nx.DiGraph()
    graph.add_nodes_from(members)
    graph.add_edges_from(pair for pair, count in counts.items() if count >= MIN_REFERRALS and pair[0] != pair[1])
    cycles = [component for component in nx.strongly_connected_components(graph) if len(component) >= 3]
    largest = max((len(component) for component in cycles), default=0)
    denominator = max(1, len(original_members))
    score = largest / denominator
    return {
        "available": True,
        "score": _round(score),
        "relationship_count": int(counts.sum()) if len(counts) else 0,
        "top_relationship": "closed referral cycle" if largest else "no qualifying cycle",
        "detail": f"A thresholded referral cycle covers {largest} of {denominator} network hospitals." if largest else "No three-hospital referral cycle survives the detector threshold.",
    }


def _ownership_evidence(providers, members, excluded=frozenset()):
    if providers is None or not {"provider_id", "owner_id"}.issubset(providers.columns):
        return {"available": False, "score": 0.0, "detail": "Ownership data is not available for this region."}
    sub = providers[providers.provider_id.isin(members)]
    owners = sub.owner_id.dropna().astype(str)
    owners = owners[~owners.isin(PUBLIC_OWNERS) & ~owners.isin(excluded) & owners.ne("")]
    counts = owners.value_counts()
    score = float(counts.iloc[0] / len(set(members))) if len(counts) and members else 0.0
    top = str(counts.index[0]) if len(counts) else ""
    return {
        "available": True,
        "score": _round(score),
        "relationship_count": int(counts.iloc[0]) if len(counts) else 0,
        "top_relationship": top,
        "detail": f"{counts.iloc[0]} of {len(set(members))} hospitals share non-public owner {top}." if top else "No common non-public owner supports this network.",
    }


def _hub_cutoff(values):
    values = sorted(int(value) for value in values if int(value) >= 2)
    if not values:
        return math.inf
    return max(3, values[min(len(values) - 1, math.ceil(0.95 * len(values)) - 1)])


def _administrative_hubs(claims, providers, referrals):
    agent_degrees = {}
    if "referred_by_agent_id" in claims.columns:
        agent_rows = claims.dropna(subset=["referred_by_agent_id"])
        agent_degrees = agent_rows.groupby("referred_by_agent_id").provider_id.nunique().to_dict()
    owner_rows = providers[~providers.owner_id.isin(PUBLIC_OWNERS)].dropna(subset=["owner_id"])
    owner_degrees = owner_rows.groupby("owner_id").provider_id.nunique().to_dict()
    referral_degrees = {}
    if referrals is not None and {"from_provider_id", "to_provider_id"}.issubset(referrals.columns):
        counts = referrals.groupby(["from_provider_id", "to_provider_id"]).size()
        graph = nx.Graph()
        graph.add_edges_from(pair for pair, count in counts.items() if count >= MIN_REFERRALS and pair[0] != pair[1])
        referral_degrees = dict(graph.degree())

    def high(degrees):
        cutoff = _hub_cutoff(degrees.values())
        return {str(key) for key, value in degrees.items() if value >= cutoff}, cutoff

    agents, agent_cutoff = high(agent_degrees)
    owners, owner_cutoff = high(owner_degrees)
    referral_nodes, referral_cutoff = high(referral_degrees)
    return {
        "agents": agents,
        "owners": owners,
        "referral_providers": referral_nodes,
        "cutoffs": {
            "agent_provider_degree": None if math.isinf(agent_cutoff) else int(agent_cutoff),
            "owner_provider_degree": None if math.isinf(owner_cutoff) else int(owner_cutoff),
            "referral_provider_degree": None if math.isinf(referral_cutoff) else int(referral_cutoff),
        },
    }


def _supporting_score(families):
    available = [family["score"] for family in families.values() if family["available"]]
    return mean(available) if available else 0.0


def _recommendation(score):
    if score >= 0.75:
        return "Prioritize for investigator review: the network remains structurally stable and has corroborating signals, but this is an investigative lead—not proof of fraud."
    if score >= 0.50:
        return "Continue a targeted investigation and obtain independent records: some suspicion survives, but the network depends on evidence that is sensitive to exclusion."
    return "Treat the ring alert cautiously and seek independent corroboration before escalation; the current network is sensitive to plausible relationship removal."


def evaluate_network(network_id, members, edges, claims, providers, referrals, levels=PERTURBATION_LEVELS, trials=PERTURBATION_TRIALS):
    """Return a JSON-safe robustness assessment for one already-detected network."""
    members = sorted(set(map(str, members)))
    provider_names = {}
    if {"provider_id", "name"}.issubset(providers.columns):
        provider_names = providers.assign(provider_id=providers.provider_id.astype(str)).set_index("provider_id").name.to_dict()
    stability = membership_stability(network_id, members, edges, levels=levels, trials=trials)
    structural = stability["mean_stability"]
    supporting = {
        "shared_agents": _agent_evidence(claims, members),
        "referrals": _referral_evidence(referrals, members),
        "common_ownership": _ownership_evidence(providers, members),
    }
    available = [name for name, family in supporting.items() if family["available"]]
    supporting_score = _supporting_score(supporting)
    per_family_weight = SUPPORTING_WEIGHT / len(available) if available else 0.0
    overall = STRUCTURAL_WEIGHT * structural + SUPPORTING_WEIGHT * supporting_score

    contributions = [
        {
            "relationship_type": "shared_beneficiaries",
            "label": FAMILY_LABELS["shared_beneficiaries"],
            "available": True,
            "score": structural,
            "weight": STRUCTURAL_WEIGHT,
            "contribution": _round(STRUCTURAL_WEIGHT * structural),
            "detail": f"Mean maximum-Jaccard membership stability across {len(levels)} deterministic perturbation levels.",
        }
    ]
    for name, family in supporting.items():
        contributions.append(
            {
                "relationship_type": name,
                "label": FAMILY_LABELS[name],
                **family,
                "weight": _round(per_family_weight if family["available"] else 0.0),
                "contribution": _round(per_family_weight * family["score"] if family["available"] else 0.0),
            }
        )

    exclusions = []
    shared_only_removed = SUPPORTING_WEIGHT * supporting_score
    exclusions.append(
        {
            "relationship_type": "shared_beneficiaries",
            "label": FAMILY_LABELS["shared_beneficiaries"],
            "topology_affected": True,
            "membership_stability": 0.0,
            "resulting_robustness_score": round(shared_only_removed * 100),
            "sensitivity_points": round((overall - shared_only_removed) * 100),
            "explanation": "Shared-beneficiary edges construct the detector graph; removing them eliminates the basis for this Leiden/Louvain membership.",
        }
    )
    for name in ("shared_agents", "referrals", "common_ownership"):
        family = supporting[name]
        result = overall - (per_family_weight * family["score"] if family["available"] else 0.0)
        exclusions.append(
            {
                "relationship_type": name,
                "label": FAMILY_LABELS[name],
                "topology_affected": False,
                "membership_stability": structural,
                "resulting_robustness_score": round(max(0.0, result) * 100),
                "sensitivity_points": round(max(0.0, overall - result) * 100),
                "explanation": "This relationship corroborates the alert but was not used to construct the detector topology."
                if family["available"]
                else "This relationship is unavailable in the region's data and is not scored.",
            }
        )

    hubs = _administrative_hubs(claims, providers, referrals)
    hub_families = {
        "shared_agents": _agent_evidence(claims, members, hubs["agents"]),
        "referrals": _referral_evidence(referrals, members, hubs["referral_providers"]),
        "common_ownership": _ownership_evidence(providers, members, hubs["owners"]),
    }
    hub_supporting = _supporting_score(hub_families)
    hub_overall = STRUCTURAL_WEIGHT * structural + SUPPORTING_WEIGHT * hub_supporting
    network_agents = set(
        claims.loc[claims.provider_id.isin(members), "referred_by_agent_id"].dropna().astype(str)
    ) if "referred_by_agent_id" in claims.columns else set()
    network_owners = set(
        providers.loc[providers.provider_id.isin(members), "owner_id"].dropna().astype(str)
    ) if "owner_id" in providers.columns else set()
    exclusions.append(
        {
            "relationship_type": "administrative_hubs",
            "label": FAMILY_LABELS["administrative_hubs"],
            "topology_affected": False,
            "membership_stability": structural,
            "resulting_robustness_score": round(hub_overall * 100),
            "sensitivity_points": round(max(0.0, overall - hub_overall) * 100),
            "explanation": "Removes agents, owners, and referral providers at or above the global 95th-percentile provider degree; topology remains unchanged.",
            "excluded_hub_counts": {
                "agents": len(hubs["agents"] & network_agents),
                "owners": len(hubs["owners"] & network_owners),
                "referral_providers": len(hubs["referral_providers"] & set(members)),
            },
            "degree_cutoffs": hubs["cutoffs"],
        }
    )

    ranked = sorted(
        (family["score"], name, family) for name, family in supporting.items() if family["available"]
    )
    strongest = ranked[-1] if ranked else None
    weakest = ranked[0] if ranked else None
    limitations = [
        "RingShield tests robustness of an existing alert; it does not establish intent or prove fraud.",
        "Perturbations are deterministic simulations of missing shared-beneficiary edges, not a model of every data-quality failure.",
        "Agents, referrals, and ownership can be correlated, so their contributions are descriptive rather than causal.",
        "Interpretive recommendation bands are fixed in advance and have not been calibrated on real investigation outcomes.",
    ]
    if len(members) < 5:
        limitations.append("Small networks can split after a single edge removal, so stability estimates are coarse.")
    missing = [FAMILY_LABELS[name] for name, family in supporting.items() if not family["available"]]
    if missing:
        limitations.append(f"Missing evidence families are not scored: {', '.join(missing)}.")

    return {
        "network_id": str(network_id),
        "member_hospitals": members,
        "member_hospital_details": [
            {
                "provider_id": provider_id,
                "name": str(provider_names.get(provider_id, provider_id)),
            }
            for provider_id in members
        ],
        "member_count": len(members),
        "robustness_score": round(overall * 100),
        "score_formula": {
            "structural_weight": STRUCTURAL_WEIGHT,
            "supporting_evidence_weight": SUPPORTING_WEIGHT,
            "supporting_family_weight": _round(per_family_weight),
            "note": "Supporting-family weights are equal across evidence available in the selected region; exclusions keep the original denominator.",
        },
        "stability": stability,
        "evidence_family_contributions": contributions,
        "exclusion_sensitivity": exclusions,
        "strongest_supporting_relationship": None if not strongest else {
            "relationship_type": strongest[1], "label": FAMILY_LABELS[strongest[1]], "score": strongest[0], "detail": strongest[2]["detail"]
        },
        "weakest_supporting_relationship": None if not weakest else {
            "relationship_type": weakest[1], "label": FAMILY_LABELS[weakest[1]], "score": weakest[0], "detail": weakest[2]["detail"]
        },
        "recommendation": _recommendation(overall),
        "limitations": limitations,
    }


def detector_evaluation(scores, ground_truth, pattern="collusive_ring"):
    """Label-aware reporting only; labels never tune detection or RingShield thresholds."""
    planted = set(ground_truth.loc[ground_truth.pattern == pattern, "provider_id"].astype(str))
    detected = {
        str(cluster_id): set(group.index.astype(str))
        for cluster_id, group in scores[scores.cluster_id.fillna("").ne("")].groupby("cluster_id")
    }
    overlaps = []
    for cluster_id, members in detected.items():
        union = planted | members
        overlaps.append((len(planted & members) / len(union) if union else 0.0, cluster_id, members))
    best = max(overlaps, default=(0.0, "", set()))
    return {
        "planted_members": sorted(planted),
        "detected_networks": len(detected),
        "best_network_id": best[1],
        "best_network_members": sorted(best[2]),
        "recovered_members": len(planted & best[2]),
        "planted_member_count": len(planted),
        "precision": _round(len(planted & best[2]) / len(best[2]) if best[2] else 0.0),
        "recall": _round(len(planted & best[2]) / len(planted) if planted else 0.0),
        "exact_recovery": bool(planted and planted == best[2]),
        "false_ring_alerts": sum(not (members & planted) for members in detected.values()),
    }
