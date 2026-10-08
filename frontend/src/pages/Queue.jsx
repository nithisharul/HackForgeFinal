import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { Loading, Meter, Status, Tier, money, pct, words } from '../components/bits.jsx'

export default function Queue({ horizon, setHorizon, investigators, setInvestigators }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [tier, setTier] = useState('all')

  useEffect(() => {
    api.queue(horizon, investigators).then(setData).catch((e) => setError(e.message))
  }, [horizon, investigators])

  if (!data) return <Loading error={error} />
  const s = data.summary
  const rows = data.cases.filter((r) => tier === 'all' || r.tier === tier)
  const lastIn = Math.max(...rows.map((r, i) => (r.in_capacity ? i : -1)))

  return (
    <>
      <section className="funnel">
        <Step n={s.claims} label="claims analysed" />
        <Step n={s.raw_alerts} label="raw alerts" />
        <Step n={s.cases} label="evidence-backed cases" />
        <Step n={s.fast_track} label="fast-track" tone="high" />
        <Step n={s.review} label="investigator review" tone="medium" />
        <Step n={s.not_enough_evidence} label="not enough evidence" tone="low" last />
      </section>

      <section className="controls">
        <label>
          Risk horizon
          <span className="seg">
            {[30, 60, 90].map((h) => (
              <button key={h} className={h === horizon ? 'on' : ''} onClick={() => setHorizon(h)}>{h} days</button>
            ))}
          </span>
        </label>
        <label>
          Investigators this week
          <input type="number" min="0" max="50" value={investigators}
            onChange={(e) => setInvestigators(Math.max(0, Math.min(50, Number(e.target.value) || 0)))} />
        </label>
        <label>
          Show
          <select value={tier} onChange={(e) => setTier(e.target.value)}>
            <option value="all">All tiers</option>
            <option value="high">Fast-track</option>
            <option value="medium">Review</option>
            <option value="low">Not enough evidence</option>
          </select>
        </label>
        <p className="capacity">
          Capacity {s.capacity} cases ({s.cases_per_investigator} per investigator) covers{' '}
          <strong>{money(s.dollars_in_capacity)}</strong> of potential exposure.
        </p>
      </section>

      <div className="table-wrap">
        <table className="queue">
          <thead>
            <tr>
              <th>#</th><th>Provider</th><th>Pattern</th><th>Risk</th><th>{horizon}-day repeat</th>
              <th className="num">Potential $</th><th className="num">Members</th><th>Severity</th>
              <th>Confidence</th><th>Route</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.case_id}
                className={`${r.in_capacity ? '' : 'out'} ${i === lastIn ? 'cutoff' : ''}`}
                onClick={() => (window.location.hash = `#/case/${r.case_id}`)}>
                <td>{r.rank}</td>
                <td>
                  <strong>{r.provider_id}</strong> {r.provider_name}
                  <small>{r.specialty} · {r.city}{r.network ? ` · network ${r.network}` : ''}</small>
                </td>
                <td>{words(r.pattern)}</td>
                <td><Meter value={r.risk_score} /> {pct(r.risk_score)}</td>
                <td>{pct(r.p_horizon)}</td>
                <td className="num">{money(r.potential_dollars)}</td>
                <td className="num">{r.member_impact}</td>
                <td><Meter value={r.severity} tone="muted" /></td>
                <td>{pct(r.confidence)}</td>
                <td>{r.status === 'open' ? <Tier tier={r.tier} /> : <Status status={r.status} />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="foot">
        Rows below the line are outside this week's capacity. Ranking blends risk, potential dollars, member impact,
        severity and confidence. Every case is a lead for human review; the system never decides fraud.
      </p>
    </>
  )
}

function Step({ n, label, tone, last }) {
  return (
    <div className={`step ${tone ? 'step-' + tone : ''}`}>
      <strong>{n.toLocaleString('en-US')}</strong>
      <span>{label}</span>
      {!last && <i aria-hidden="true">→</i>}
    </div>
  )
}
