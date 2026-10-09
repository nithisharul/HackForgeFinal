// Region switch: 'us' (CMS-style claims) or 'in' (PM-JAY-style admissions). Remembered per browser.
const KEY = 'csn-region'
let current = 'us'
try { if (localStorage.getItem(KEY) === 'in') current = 'in' } catch { /* storage blocked: default to US */ }

export const getRegion = () => current
export function setRegion(r) {
  current = r
  try { localStorage.setItem(KEY, r) } catch { /* storage blocked: the switch still works for this visit */ }
}

const TERMS = {
  us: { provider: 'provider', Provider: 'Provider', providers: 'providers', Providers: 'Providers', member: 'member', Member: 'Member',
        Members: 'Members', unit: "SIU", amounts: 'dollar figures', currency: '$', ask: 'What have we learned about referral rings?' },
  in: { provider: 'hospital', Provider: 'Hospital', providers: 'hospitals', Providers: 'Hospitals', member: 'beneficiary', Member: 'Beneficiary',
        Members: 'Beneficiaries', unit: 'SAFU', amounts: 'rupee amounts', currency: '₹', ask: 'What have we learned about ghost beneficiaries?' },
}
export const terms = () => TERMS[current]
