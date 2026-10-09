// Adaptive investigation plan: rank verification steps by how much doubt they remove per unit of cost.
//
//   H(p)   uncertainty about "is this fraud?", in bits (0 = certain, 1 = coin flip)
//   ΔH(a)  expected bits removed by step a, from Bayes' rule over its two outcomes
//   C(a)   investigator time for a, priced at an hourly rate
//   U(a)   ΔH(a) / C(a), shown relative to the best step (best = 1.00)
//
// The sensitivities, false-positive rates and minutes below are planning assumptions,
// not measured values. Tune them here; every screen reads them from this file.

export const bits = (p) => (p <= 0 || p >= 1 ? 0 : -(p * Math.log2(p) + (1 - p) * Math.log2(1 - p)))

// Expected entropy reduction of a test with sensitivity s and false-positive rate f, at prior p.
export function infoGain(p, s, f) {
  const pos = p * s + (1 - p) * f
  if (pos <= 0 || pos >= 1) return 0
  const after = pos * bits((p * s) / pos) + (1 - pos) * bits((p * (1 - s)) / (1 - pos))
  return Math.max(0, bits(p) - after)
}

export const RATE = { us: 90, in: 1200 } // cost of one investigator hour, in the region's currency

// patterns: the case patterns a step applies to; omit for steps that apply to every case. region: limit to one region.
const STEPS = [
  { id: 'logs', title: 'Pull facility access and scheduling logs for both sites', why: 'Shows where the clinician actually was at each billed time.',
    minutes: 25, s: 0.92, f: 0.05, patterns: ['impossible_timing'] },
  { id: 'dupes', title: 'Match the repeated claims against remittance records', why: 'Confirms whether the same service was paid twice.',
    minutes: 20, s: 0.9, f: 0.08, patterns: ['duplicate_billing', 'duplicate_package', 'duplicate_document'] },
  { id: 'coder', title: 'Certified coder review of the flagged claims', why: 'Compares billed codes with the documented service level.',
    minutes: 120, s: 0.85, f: 0.12, patterns: ['upcoding', 'unbundling', 'package_upcoding', 'excessive_utilization', 'unnecessary_procedure', 'opd_to_ipd'] },
  { id: 'owners', title: 'Check ownership, referral and payment records across the network', why: 'Tests whether the linked providers share control or money.',
    minutes: 45, s: 0.78, f: 0.1, patterns: ['collusive_ring'] },
  { id: 'registry', title: 'Check the death registry and beneficiary identity records', why: 'A recorded death or a duplicate identity settles the claim outright.',
    minutes: 20, s: 0.95, f: 0.03, patterns: ['claim_after_death', 'ghost_beneficiary'], region: 'in' },
  { id: 'census', title: "Compare admissions with the hospital's bed census and discharge register", why: 'Shows whether the claimed stays could physically have happened.',
    minutes: 30, s: 0.88, f: 0.08, patterns: ['bed_overrun', 'overlapping_admission'], region: 'in' },
  { id: 'records', title: 'Request medical records for the flagged claims', why: 'Checks that each billed service is documented.',
    minutes: 60, s: 0.7, f: 0.15 },
  { id: 'members', title: 'Confirm services with a sample of patients', why: 'Patients can say whether the visit happened as billed.',
    minutes: 90, s: 0.6, f: 0.08 },
  { id: 'field', title: 'State Anti-Fraud Unit field visit', why: 'Direct inspection of the hospital, registers and patients.',
    minutes: 480, s: 0.95, f: 0.04, region: 'in' },
]

// Ranked steps for one case. p: the case confidence. pattern: the case pattern. region: 'us' or 'in'.
export function plan(p, pattern, region) {
  const rate = RATE[region] ?? RATE.us
  const rows = STEPS
    .filter((a) => (!a.region || a.region === region) && (!a.patterns || a.patterns.includes(pattern)))
    .map((a) => {
      const gain = infoGain(p, a.s, a.f)
      const cost = (a.minutes / 60) * rate
      return { ...a, gain, cost, raw: gain / cost }
    })
    .sort((x, y) => y.raw - x.raw)
  const best = rows[0]?.raw || 1
  return rows.map((a) => ({ ...a, u: a.raw / best }))
}
