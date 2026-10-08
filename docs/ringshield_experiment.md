# RingShield methodology and synthetic-data evaluation

RingShield is a read-only stress test for networks already detected by ClaimShield Nexus. It does not re-label hospitals, alter case scores, retrain a model, write a verdict, or claim that a network is fraudulent.

## Method

The original graph detector projects hospital–beneficiary activity into hospital pairs and keeps edges with at least 15 shared beneficiaries and lift of at least 3. Leiden clustering (deterministic seed 0; Louvain seed 0 only when Leiden is unavailable) supplies the baseline membership. RingShield preserves that membership as the comparison target.

For each detected network, RingShield removes 10%, 20%, and 30% of qualifying shared-beneficiary edges in ten deterministic trials per level. Seeds are SHA-256-derived from the network ID, removal level, and trial number. It re-runs the same community routine and reports the maximum Jaccard overlap between the original membership and any perturbed community. This separates membership instability from a mere cluster-label change.

Corroboration is measured independently:

- shared agents: share of the network's admissions naming its most common agent;
- referrals: share of member hospitals covered by a referral strongly connected component, using the detector's 15-referral threshold;
- common ownership: share of hospitals under the most common non-public owner;
- administrative-hub exclusion: recalculates corroboration after excluding agents, owners, and referral providers at or above the global 95th-percentile provider degree (minimum degree 3).

The transparent robustness score is `65% × mean membership stability + 35% × mean available corroborating-family score`. Available corroborating families split the 35% equally. Exclusion tests keep that original denominator: removing a family can only reduce, never silently reweight, the result. Removing agents, referrals, ownership, or administrative hubs cannot change reported topology because none constructs the Leiden graph. Removing shared-beneficiary edges does affect topology.

No planted label was used to select a detector threshold, perturbation level, score weight, or recommendation band. Labels are read only after scoring to report recovery.

## Reproduction

From the repository root, with the pinned backend dependencies installed:

```text
python -m backend.pipeline.ringshield_experiment --region in
python -m unittest backend.tests.test_ringshield backend.tests.test_ringshield_api -v
```

## Results on the committed India synthetic data

The original detector produced one network, N01. It exactly recovered the five planted hospitals (`P022`, `P059`, `P148`, `P152`, `P203`): 5/5 recovered, precision 1.00, recall 1.00. There were zero detected networks with no planted-ring member. Because the dataset contains only one detected network, this zero count cannot establish a false-positive rate.

RingShield scored N01 at **82/100**. Original membership is the 100% reference. Mean perturbed membership stability was:

| Shared-beneficiary edges removed | Trials | Mean Jaccard stability | Range | Mean largest matched group |
|---:|---:|---:|---:|---:|
| 10% | 10 | 1.00 | 1.00–1.00 | 5.0 hospitals |
| 20% | 10 | 0.64 | 0.60–1.00 | 3.2 hospitals |
| 30% | 10 | 0.66 | 0.60–1.00 | 3.3 hospitals |

The non-monotonic 20%/30% means are possible because each level uses independent deterministic edge-removal trials and the network has only nine qualifying edges. They should not be interpreted as improved resilience at 30%.

| Relationship excluded | Topology changes? | Resulting score | Sensitivity |
|---|---|---:|---:|
| Shared beneficiaries | Yes | 32 | −50 points |
| Shared agents | No | 73 | −9 points |
| Referrals | No | 70 | −12 points |
| Common ownership | No | 70 | −12 points |
| High-degree administrative hubs | No | 70 | −12 points |

Referral cycles and common ownership both scored 1.00; the deterministic tie-break reports referral cycles as the strongest support. Shared agents were weakest at 0.755, still representing 76% of network admissions naming the same agent.

## Controlled checks and limitations

Unit fixtures cover a dense four-hospital network, a small disconnected network with missing evidence, deterministic repeatability, topology/evidence separation, and false-ring alert accounting. These fixtures validate behavior only and do not replace the original dataset or support an accuracy claim.

- The evaluation has one detected India network, so it cannot estimate false-positive performance or calibrate the 82/100 score.
- Edge deletion is a controlled sensitivity analysis, not a complete model of coding errors, missing claims, beneficiary identity problems, or adversarial behavior.
- Supporting families can be correlated. Their contributions are descriptive, not causal or statistically independent.
- Small networks have coarse changes: one removed edge can materially alter a partition.
- Results are synthetic and are an investigation aid, never proof of fraud.
