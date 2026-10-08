# Synthetic clinical records

Records read by the clinical audit (`backend/brain/clinical_audit.py`, `GET /api/cases/{case_id}/clinical-audit`).
All of them are synthetic and were written for the demo on `feature/clinical-audit-rag`; they are copied here unchanged.

A record is used only for the case whose id is its file name, in its own region folder (`us/`, later `in/`).
It is never borrowed for another case, even one with the same pattern.

| File | Matches a case? | Notes |
|---|---|---|
| `us/CASE-P209.txt` | Yes: US CASE-P209, Dr. Hannah Hayes, impossible timing | Badge and EHR log. The claims data has no P209 claims on the log's date (2026-03-14), so the audit reports it as not corroborated. |
| `us/CASE-P104.txt` | No US case CASE-P104 exists | Progress note (99215, 7 minutes). Used only as a test fixture for the visit-level check. |
| `us/CASE-P164.txt` | No US case CASE-P164 exists | Lab accession audit (80053 with 80048). Used only as a test fixture for the bundling check. |

There are no Indian records yet; India cases show the audit as unavailable rather than reuse US records.
