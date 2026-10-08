"""India rule checks on small hand-built fixtures (the package master is the real reference table).

    python -m unittest discover -s backend/tests -t .
"""
import unittest

import numpy as np
import pandas as pd

from backend.pipeline import rules_in

T0 = pd.Timestamp("2025-10-01 10:00")


def hospital(pid="P1", **kw):
    return {"provider_id": pid, "beds": 50, "nabh_status": "none", "city_tier": "Y", "teaching": 0,
            "empanelled_specialties": "General Medicine|General Surgery|Obstetrics & Gynaecology",
            "empanelment_date": pd.Timestamp("2020-01-01"), **kw}


def member(mid="M1", **kw):
    return {"member_id": mid, "age": 40, "gender": "F", "death_date": pd.NaT, "card_created_date": pd.Timestamp("2020-01-01"),
            "mobile_token": f"MOB-{mid}", "village_code": "VIL-A", **kw}


def claim(cid="C1", **kw):
    """A valid 3-day fever admission in a general ward, billed at the published rate (3 x 1,800)."""
    row = {"claim_id": cid, "member_id": "M1", "provider_id": "P1", "facility_id": "F1", "service_datetime": T0,
           "claim_type": "medical_per_day", "procedure_code": "MG001A", "los_days": 3, "ward_type": "general",
           "billed_amount": 5400.0, "paid_amount": 5400.0, "diagnosis_icd10": "R50.9", "specialty": "General Medicine",
           "referred_by_agent_id": np.nan, "document_hash": f"DOC-{cid}"}
    row.update(kw)
    row.setdefault("discharge_datetime", row["service_datetime"] + pd.Timedelta(days=max(row["los_days"], 0), hours=2))
    return row


def hysterectomy(cid="C1", **kw):
    """Surgical package SO010 (estimated rate 20,000) for a woman, billed at that rate."""
    return claim(cid, **{"claim_type": "surgical", "procedure_code": "SO010", "los_days": 5, "ward_type": "general",
                         "billed_amount": 20000.0, "paid_amount": 20000.0, "diagnosis_icd10": "D25.9",
                         "specialty": "Obstetrics & Gynaecology", **kw})


def run(claims, hospitals=None, members=None):
    flags = rules_in.run(pd.DataFrame(claims), pd.DataFrame(hospitals or [hospital()]), pd.DataFrame(members or [member()]))
    return {(r.claim_id, r.rule): r.detail for r in flags.itertuples()}


class PackageMismatch(unittest.TestCase):
    def test_valid_claim_is_not_flagged(self):
        self.assertEqual(run([claim()]), {})

    def test_more_specific_code_in_the_same_category_is_not_a_mismatch(self):
        self.assertNotIn(("C1", "package_mismatch"), run([claim(diagnosis_icd10="r50.8")]))

    def test_diagnosis_from_another_category_is_flagged(self):
        detail = run([claim(diagnosis_icd10="K35.8")])[("C1", "package_mismatch")]
        self.assertIn("K35.8", detail)
        self.assertIn("MG001A", detail)

    def test_missing_diagnosis_is_not_reported_as_a_mismatch(self):
        self.assertNotIn(("C1", "package_mismatch"), run([claim(diagnosis_icd10=np.nan)]))

    def test_unknown_package_code_is_flagged_not_crashed(self):
        self.assertIn("not in the package master", run([claim(procedure_code="ZZ999")])[("C1", "package_mismatch")])

    def test_female_only_package_for_a_man_is_flagged(self):
        flags = run([hysterectomy()], members=[member(gender="M")])
        self.assertIn("male beneficiary", flags[("C1", "package_mismatch")])

    def test_female_only_package_for_a_woman_is_not_a_mismatch(self):
        self.assertNotIn(("C1", "package_mismatch"), run([hysterectomy()]))

    def test_amount_above_the_entitled_rate_is_flagged_and_names_the_rate_basis(self):
        detail = run([claim(billed_amount=6000.0)])[("C1", "package_mismatch")]
        self.assertIn("published HBP rate", detail)
        detail = run([hysterectomy(billed_amount=25000.0)])[("C1", "package_mismatch")]
        self.assertIn("ESTIMATED package rate", detail)

    def test_incentives_the_hospital_is_entitled_to_are_not_flagged(self):
        # full NABH (+15%), metro (+10%) and teaching (+10%) on the procedure price
        rich = hospital(nabh_status="full", city_tier="X", teaching=1)
        self.assertEqual(run([claim(billed_amount=round(5400 * 1.15 * 1.10 * 1.10))], hospitals=[rich]), {})
        self.assertIn(("C1", "package_mismatch"), run([claim(billed_amount=round(5400 * 1.15 * 1.10 * 1.10) + 100)], hospitals=[rich]))


class Empanelment(unittest.TestCase):
    def test_specialty_outside_the_list_is_flagged(self):
        c = claim(procedure_code="MC001B", claim_type="surgical", los_days=1, billed_amount=5000.0,
                  diagnosis_icd10="I25.1", specialty="Cardiology")
        self.assertIn("not empanelled for Cardiology", run([c])[("C1", "not_empanelled")])

    def test_case_and_spacing_differences_are_not_violations(self):
        self.assertNotIn(("C1", "not_empanelled"), run([claim(specialty="general  MEDICINE")]))

    def test_hospital_without_a_specialty_list_is_skipped(self):
        for missing in (np.nan, "", " | "):
            self.assertNotIn(("C1", "not_empanelled"), run([claim(specialty="Cardiology")], hospitals=[hospital(empanelled_specialties=missing)]))

    def test_claim_without_a_specialty_is_skipped(self):
        self.assertNotIn(("C1", "not_empanelled"), run([claim(specialty=np.nan)]))

    def test_admission_before_empanelment_is_flagged_after_is_not(self):
        late = hospital(empanelment_date=pd.Timestamp("2025-12-01"))
        self.assertIn("before the hospital's empanelment", run([claim()], hospitals=[late])[("C1", "not_empanelled")])
        self.assertNotIn(("C1", "not_empanelled"), run([claim(service_datetime=pd.Timestamp("2025-12-02 09:00"))], hospitals=[late]))

    def test_missing_empanelment_date_is_skipped(self):
        self.assertNotIn(("C1", "not_empanelled"), run([claim()], hospitals=[hospital(empanelment_date=pd.NaT)]))


class WardDrift(unittest.TestCase):
    """Hospital-level ICU drift: admissions spread so that no month reaches 8, isolating the whole-period test."""

    def admissions(self, pid, n, n_icu):
        rows = []
        for i in range(n):
            rows.append(claim(f"{pid}-{i}", member_id=f"M-{pid}-{i}", provider_id=pid, facility_id=pid,
                              service_datetime=T0 + pd.Timedelta(days=11 * i), ward_type="icu" if i < n_icu else "general",
                              billed_amount=(3600.0 if i < n_icu else 1800.0) * 3))
        return rows

    def flags(self, target_n, target_icu):
        rows, hosps, mems = [], [], []
        for k in range(10):  # peers: 3 of 33 in ICU (9%)
            rows += self.admissions(f"P{k}", 33, 3)
        rows += self.admissions("PX", target_n, target_icu)
        for r in rows:
            mems.append(member(r["member_id"]))
        hosps = [hospital(f"P{k}") for k in range(10)] + [hospital("PX")]
        return run(rows, hosps, mems)

    def test_hospital_far_above_the_all_hospital_rate_is_flagged(self):
        f = self.flags(33, 15)
        hits = [k for k in f if k[1] == "ward_upcoding" and k[0].startswith("PX")]
        self.assertEqual(len(hits), 15)
        self.assertIn("binomial p", f[hits[0]])

    def test_hospital_at_the_peer_rate_is_not_flagged(self):
        f = self.flags(33, 3)
        self.assertFalse([k for k in f if k[1] == "ward_upcoding"])

    def test_small_hospital_is_not_judged_on_the_whole_period(self):
        f = self.flags(20, 10)  # 50% ICU but fewer than 30 admissions
        self.assertFalse([k for k in f if k[1] == "ward_upcoding" and k[0].startswith("PX")])


class AssumedNorms(unittest.TestCase):
    def test_long_stay_detail_says_the_norm_is_assumed(self):
        detail = run([claim(los_days=12, billed_amount=1800.0 * 12)])[("C1", "long_stay")]
        self.assertIn("assumed", detail)
        self.assertIn("publishes no length-of-stay norm", detail)


if __name__ == "__main__":
    unittest.main()
