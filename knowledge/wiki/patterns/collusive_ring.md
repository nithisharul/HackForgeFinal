---
type: pattern
id: collusive_ring
title: Collusive referral network
policy: POL-005
---
# Collusive referral network

## Definition
A group of providers, often commonly owned, repeatedly bill the same small set of members and refer them to each other in a loop.

## Detection signals
- Graph: Leiden community with member overlap far above chance
- Graph: circular referrals among the community
- Ownership: majority of the community shares one owner
- BiRank: risk propagated through shared members

## Policy basis
- POL-005 Referrals among commonly owned providers (`knowledge/sources/policies/POL-005.md`)
- Public basis: Physician self-referral (Stark) law and federal Anti-Kickback Statute, as general background

## Known innocent explanations
- A legitimate multi-specialty group whose referrals match documented care plans
<!-- auto:learned -->
<!-- /auto -->

## Detected by
- No claim rule. Found by the models; see [[system_models]].
- What to request from the provider: [[runbook_evidence]]

## Regulatory background
- [[REG-STARK]] | Physician self-referral law (Stark)
- [[REG-AKS]] | Anti-Kickback Statute

## Lessons from closed cases
<!-- auto:lessons -->
<!-- /auto -->

## Notes from sources
<!-- auto:notes -->
<!-- /auto -->

## Precedent summary
<!-- auto:summary -->
2 closed cases: 2 confirmed, 0 cleared, 0 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
- [[INV005]] | [[P263]] (DME Supplier) | **confirmed** | closed 2025-05-20
- [[INV004]] | [[P055]] (Cardiology) | **confirmed** | closed 2025-10-05
<!-- /auto -->
