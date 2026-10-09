---
type: pattern
id: collusive_ring
title: Collusive hospital network
policy: POL-IN-001
---
# Collusive hospital network

## Definition
A group of hospitals, often under one owner and fed by one agent, repeatedly admits the same small pool of beneficiaries and refers them to each other.

## Detection signals
- Graph: Leiden community of hospitals with beneficiary overlap far above chance
- Graph: one agent brings most of the network's admissions
- Ownership: most hospitals share one private owner
- Graph: referrals form a closed loop
- BiRank: risk propagated through shared beneficiaries

## Policy basis
- POL-IN-001 Agents, camps and referrals among linked hospitals (`knowledge/india/sources/policies/POL-IN-001.md`)
- Public basis: NHA Anti-Fraud Framework Practitioners' Guidebook (2020); NHA Field Investigation and Medical Audit Manual (2020); the Khyati Hospital case (Ahmedabad, 2024) as background

## Known innocent explanations
- A referral chain where district hospitals send patients to one teaching hospital, with documented referral letters
- Beneficiaries from one area who use the nearest group of empanelled hospitals
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
0 closed cases: 0 confirmed, 0 cleared, 0 inconclusive.
<!-- /auto -->

## Cases
<!-- auto:cases -->
<!-- /auto -->
