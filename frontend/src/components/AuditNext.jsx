import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { money } from './bits.jsx'

// AuditNext: the next checks for this case, ranked by U(a) = expected uncertainty removed (ΔH) / cost.
// Numbers come from /api/cases/{id}/audit-plan; accuracy is learned from closed cases in the Second Brain.
// The doubt removed, the cost and the utility sit side by side so the ranking can be checked at a glance.
export default function AuditNext({ caseId, horizon }) {
  const [plan, setPlan] = useState(undefined)
  useEffect(() => {
    let live = true
    setPlan(undefined)
    api.auditPlan(caseId, horizon).then((d) => live && setPlan(d.actions?.length ? d : null)).catch(() => live && setPlan(null))
    return () => { live = false }
  }, [caseId, horizon])

  if (plan === null) return null
  if (plan === undefined) return <section className="plan" aria-busy="true"><h2>Next verification steps</h2><span className="sk sk-line" /></section>
  const best = Math.max(...plan.actions.map((a) => a.utility_score)) || 1
  return (
    <section className="plan" aria-labelledby="plan-h">
      <h2 id="plan-h">Next verification steps</h2>
      <p className="sec-note">
        Ranked by doubt removed per hour. Doubt now: {plan.prior_entropy_bits.toFixed(2)} bits
        {plan.closed_cases_used > 0 && `, learned from ${plan.closed_cases_used} closed ${plan.closed_cases_used === 1 ? 'case' : 'cases'}`}.
      </p>
      <ol className="plan-list">
        {plan.actions.map((a) => (
          <li key={a.id} className={a.is_optimal ? 'best' : undefined}>
            <p className="plan-title">{a.name}</p>
            <p className="plan-why">{a.description}</p>
            <div className="plan-figs">
              <span className="gain" title="Expected uncertainty removed (ΔH)">−{a.info_gain_bits.toFixed(2)} bits</span>
              <span className="cost" title="Investigator time and its cost, C(a)">{a.cost_mins} min, {money(a.cost)}</span>
              <span className="u" title="Utility U(a) = ΔH per hour">U {a.utility_score.toFixed(2)}</span>
            </div>
            <span className="u-bar" aria-hidden="true"><i style={{ width: `${Math.max(2, (a.utility_score / best) * 100)}%` }} /></span>
            <p className="plan-basis">{a.basis} Accuracy: {a.accuracy_pct}%.</p>
          </li>
        ))}
      </ol>
      <p className="formula">U(a) = ΔH ÷ hours. Prior is this case's confidence ({Math.round(plan.prior_probability * 100)}%). {plan.assumptions}</p>
    </section>
  )
}

// The recommended action. US cases get a structured playbook from the Second Brain
// ("Primary Directive: ... Targeted Investigation Steps: 1. Title: text ... Statutory Basis: ..."); other text shows as written.
export function Playbook({ text }) {
  const directive = text.match(/Primary Directive:\s*([\s\S]*?)(?=Targeted Investigation Steps:|$)/i)?.[1].trim()
  const steps = [...text.matchAll(/(\d+)\.\s*([^:\n]+):\s*([\s\S]*?)(?=\n\d+\.|\n\nStatutory Basis:|$)/g)].map((m) => [m[2].trim(), m[3].trim()])
  const basis = text.match(/Statutory Basis:\s*([\s\S]*)$/i)?.[1].trim()
  if (!directive && !steps.length) return <p className="route-rec">{text}</p>
  return (
    <div className="playbook">
      {directive && <p className="pb-directive">{directive}</p>}
      {steps.length > 0 && (
        <ol className="pb-steps">{steps.map(([t, d]) => <li key={t}><b>{t}.</b> {d}</li>)}</ol>
      )}
      {basis && <p className="pb-basis"><b>Statutory basis:</b> {basis}</p>}
    </div>
  )
}
