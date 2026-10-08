// AuditNext (ported from feature/clinical-audit-rag): the next verification step, ranked by expected information
// per hour of audit time. children: the fixed checklist for the pattern, folded under the ranking.
import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { money } from './bits.jsx'

export default function AuditPlan({ caseId, children }) {
  const [plan, setPlan] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    let live = true
    setPlan(null); setError(null)
    api.auditPlan(caseId).then((p) => live && setPlan(p)).catch((e) => live && setError(e.message))
    return () => { live = false }
  }, [caseId])

  if (plan?.status === 'unavailable') return children || null
  return (
    <div className="audit-plan">
      <h4>Next verification step <small>AuditNext · ranking aid</small></h4>
      {!plan && !error && <p className="muted" role="status">Ranking verification steps…</p>}
      {error && <p className="notice error" role="alert">Verification plan could not load: {error}</p>}
      {plan && (
        <>
          <p className="ap-meta">
            Prior {Math.round(plan.prior_probability * 100)}% ({plan.prior_source}) · uncertainty {plan.prior_entropy_bits} bits.
            Ranked by expected information gained per hour.
          </p>
          <ol className="ap-list">
            {plan.actions.map((a) => (
              <li key={a.id} className={a.is_optimal ? 'best' : undefined}>
                <div className="ap-head">
                  <strong>{a.name}</strong>
                  {a.is_optimal && <span className="ap-best">Best next step</span>}
                </div>
                <p>{a.description}</p>
                <dl className="ap-nums">
                  <div><dt>Cost</dt><dd>{a.cost_mins} min · {money(a.cost_dollars)}</dd></div>
                  <div><dt>Info gain</dt><dd>{a.info_gain_bits} bits</dd></div>
                  <div><dt>Per hour</dt><dd>{a.utility_score}</dd></div>
                  <div><dt>Assumed accuracy</dt><dd>{a.discriminative_power_pct}%</dd></div>
                </dl>
              </li>
            ))}
          </ol>
          <small className="ap-note">{plan.assumptions}</small>
        </>
      )}
      {children && (
        <details className="ap-sop">
          <summary>Standard checklist for this pattern</summary>
          {children}
        </details>
      )}
    </div>
  )
}
