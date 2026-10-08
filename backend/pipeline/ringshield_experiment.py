"""Reproduce the RingShield comparison on a region's committed synthetic data.

    python -m backend.pipeline.ringshield_experiment --region in
"""
import argparse
import json

import pandas as pd

from backend import region
from backend.pipeline.ringshield import detector_evaluation, evaluate_network


def run(code="in"):
    selected = region.REGIONS[code]
    scores = pd.read_csv(selected.proc / "provider_scores.csv").set_index("provider_id")
    truth = pd.read_csv(selected.raw / "ground_truth.csv")
    baseline = detector_evaluation(scores, truth)
    if not baseline["best_network_id"]:
        return {"region": code, "baseline_detector": baseline, "ringshield": None}

    claims_header = pd.read_csv(selected.raw / "claims.csv", nrows=0).columns
    claim_columns = [c for c in ("provider_id", "member_id", "referred_by_agent_id") if c in claims_header]
    result = evaluate_network(
        baseline["best_network_id"],
        baseline["best_network_members"],
        pd.read_csv(selected.proc / "edges.csv"),
        pd.read_csv(selected.raw / "claims.csv", usecols=claim_columns),
        pd.read_csv(selected.raw / "providers.csv"),
        pd.read_csv(selected.raw / "referrals.csv"),
    )
    return {
        "region": code,
        "baseline_detector": baseline,
        "ringshield": {
            "network_id": result["network_id"],
            "robustness_score": result["robustness_score"],
            "stability": result["stability"],
            "exclusion_sensitivity": result["exclusion_sensitivity"],
            "strongest_supporting_relationship": result["strongest_supporting_relationship"],
            "weakest_supporting_relationship": result["weakest_supporting_relationship"],
            "limitations": result["limitations"],
        },
    }


def main():
    parser = argparse.ArgumentParser(description="Compare the committed graph detector with RingShield")
    parser.add_argument("--region", choices=sorted(region.REGIONS), default="in")
    args = parser.parse_args()
    print(json.dumps(run(args.region), indent=2))


if __name__ == "__main__":
    main()
