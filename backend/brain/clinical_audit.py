"""
ClaimShield Nexus - Clinical Chart & EHR Audit Engine (Multimodal Evidence Module)
Simulates CMS Additional Documentation Request (ADR) review by cross-referencing
billed claims against clinical progress notes, EHR audit logs, and lab requisitions.
"""

CLINICAL_ARTIFACTS = {
    "impossible_timing": {
        "doc_type": "EHR Audit Log & Badge Access Record",
        "author": "Security & EHR IT Compliance, Methodist Hospital San Antonio",
        "date_of_service": "2026-03-14",
        "text_content": (
            "[08:45 AM CST] Badge Access: Physician entry at West Tower Physician Lounge (San Antonio, TX).\n"
            "[09:12 AM - 11:30 AM CST] Active EHR Session: IP 10.240.12.88 (Hospital Workstation Room 402, San Antonio).\n"
            "[12:15 PM CST] Inpatient Rounding Note signed for Patient MRN-99412.\n"
            "[01:30 PM CST] Flagged Outpatient Claim: In-person office encounter (CPT 99214, POS 11) billed at Austin Clinic (approx. 80 miles away).\n"
            "[02:10 PM CST] Badge Access: Physician badge swipe at Methodist San Antonio Cafeteria.\n"
            "Conclusion: Provider was physically present in San Antonio continuously between 08:45 and 15:30."
        ),
        "discrepancy_found": True,
        "discrepancy_type": "Physical Presence Discrepancy",
        "finding": "EHR badge logs confirm physician was physically in San Antonio during time outpatient office visit was billed in Austin.",
        "statute": "CMS Pub 100-08 Ch. 3 §3.3 / Texas Medicaid Travel Adjudication Rules",
        "recommended_action": "Disallow in-person Place of Service (POS 11) claims; refer to MFCU for impossible physical travel."
    },
    "upcoding": {
        "doc_type": "Signed Outpatient Clinical Encounter Progress Note",
        "author": "Dr. Hannah Hayes, MD",
        "date_of_service": "2026-02-18",
        "text_content": (
            "CHIEF COMPLAINT: Routine 3-month blood pressure follow-up.\n"
            "HISTORY OF PRESENT ILLNESS: Patient reports feeling well. No headaches, dizziness, or chest pain.\n"
            "MEDICATIONS: Lisinopril 20mg daily. Compliance good.\n"
            "PHYSICAL EXAM: BP 124/82, HR 72 regular, lungs clear to auscultation, no pedal edema.\n"
            "ASSESSMENT & PLAN: Essential hypertension, benign, well-controlled. Refilled Lisinopril x 90 days. Follow up in 6 months.\n"
            "TOTAL TIME DOCUMENTED: 7 minutes face-to-face.\n"
            "BILLED CODE: CPT 99215 (Office Visit, Level 5 - requires 40-54 minutes or High-Complexity MDM)."
        ),
        "discrepancy_found": True,
        "discrepancy_type": "Coding Level Inflation (Upcoding)",
        "finding": "Clinical note documents 7 minutes of routine care with straightforward MDM, failing to meet CPT 99215 high-complexity criteria.",
        "statute": "CMS Evaluation and Management (E/M) Guidelines / CPT Coding Manual §99215",
        "recommended_action": "Downcode claim to CPT 99212/99213; issue overpayment recoupment demand for reimbursement differential."
    },
    "unbundling": {
        "doc_type": "Diagnostic Laboratory Accession Order & Requisition Slip",
        "author": "Quest Diagnostic Reference Lab - Specimen Processing",
        "date_of_service": "2026-01-22",
        "text_content": (
            "SPECIMEN ID: LAB-2026-88190\n"
            "COLLECTION: Single red-top venipuncture tube collected at 08:30 AM CST.\n"
            "ORDERED TESTS: Comprehensive Metabolic Panel (CMP - CPT 80053).\n"
            "BILLED CODES: CPT 80053 (Comprehensive Panel) AND CPT 80048 (Basic Metabolic Panel).\n"
            "AUDIT FINDINGS: Only one venipuncture draw performed. No distinct clinical indication or separate requisition for CPT 80048.\n"
            "All analytes of 80048 (BMP) are constituent sub-components of 80053."
        ),
        "discrepancy_found": True,
        "discrepancy_type": "NCCI PTP Unbundling Violation",
        "finding": "Single specimen collected for CMP; separate billing of component code 80048 without Modifier 59 violates CMS NCCI bundling edits.",
        "statute": "CMS NCCI Policy Manual Ch. 1 / Social Security Act §1862(a)(1)(A)",
        "recommended_action": "Deny component code 80048; adjust claim to comprehensive package rate only."
    },
    "cleared_benign": {
        "doc_type": "Operative Report & Surgical Narrative",
        "author": "Surgical Pathology & Orthopedics",
        "date_of_service": "2026-03-02",
        "text_content": (
            "PROCEDURE: Arthroscopy knee with partial meniscectomy (CPT 29881) AND distinct excision separate compartment with Modifier 59.\n"
            "OPERATIVE DETAILS: Separate distinct incision performed on contralateral compartment due to acute traumatic loose body.\n"
            "DOCUMENTATION: Extensive anatomical photographs and separate operative times documented.\n"
            "FINDINGS: Appropriate use of Modifier 59 established by operative note."
        ),
        "discrepancy_found": False,
        "discrepancy_type": "None (Documentation Corroborated)",
        "finding": "Medical records substantiate separate anatomical sites and independent surgical necessity. Modifier 59 appropriately supported.",
        "statute": "CMS NCCI Policy Manual Modifier Guidelines (Modifier 59 / X-EPSU)",
        "recommended_action": "Exonerate provider; close SIU lead as substantiated compliant care."
    }
}

def audit_case_clinical_chart(pattern: str, provider_id: str = "") -> dict:
    """
    Returns the clinical audit findings for a case based on detected pattern.
    Falls back to upcoding archetype if pattern is unrecognized.
    """
    key = pattern if pattern in CLINICAL_ARTIFACTS else "upcoding"
    artifact = CLINICAL_ARTIFACTS[key]
    return {
        "status": "completed",
        "provider_id": provider_id,
        "pattern": pattern,
        "artifact": artifact
    }
