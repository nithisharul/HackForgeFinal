import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { Loading, Status, Tier, money, pct, words } from '../components/bits.jsx'
import Network from './Network.jsx'

export default function CaseDetail({ caseId, horizon }) {
  const [c, setC] = useState(null)
  const [error, setError] = useState(null)
  const load = () => api.getCase(caseId, horizon).then(setC).catch((e) => setError(e.message))
  useEffect(() => { setC(null); load() }, [caseId, horizon])

  if (!c) return <Loading error={error} />
  const b = c.brief
  const conf = b.confidence
  const maxClaims = Math.max(...b.timeline.monthly.map((m) => m.claims))

  return (
    <div className="case">
      <a className="back" href="#/">← Back to queue</a>
      <header className="case-head">
        <div>
          <h1>{c.provider_id} {c.provider_name} <a className="btn" href={`http://127.0.0.1:8000/api/cases/${c.case_id}/fhir`} target="_blank" rel="noreferrer" style={{float: "right", fontSize: "14px", background: "#005a9c", color: "white"}}>Export FHIR JSON</a></h1>
          <p>{c.specialty} · {c.city} · owner {c.owner_id} {c.owner_name} · {c.case_id}</p>
        </div>
        {c.status === 'open' ? <Tier tier={conf.tier} /> : <Status status={c.status} />}
      </header>

      <section className="stats">
        <Stat label="Pattern" value={words(c.pattern)} />
        <Stat label="Potential exposure" value={money(c.potential_dollars)} />
        <Stat label="Members affected" value={c.member_impact} />
        <Stat label={`${horizon}-day repeat risk`} value={pct(b.prediction.probability)} />
        <Stat label="Confidence" value={pct(conf.score)} />
      </section>

      <div className="grid">
        <div className="col">
          <Card title="Investigation brief" tag={`written by ${b.generated_by}`}>
            <p className="lead">{b.summary}</p>
            <p className={`ground ${b.grounding.passed ? 'ok' : 'bad'}`}>
              {b.grounding.passed ? '✓' : '✗'} Fact check: {b.grounding.verified} of {b.grounding.tokens_checked} IDs,
              codes and dollar figures match the claims data.
            </p>
            <h4>Recommended action</h4>
            <p>{b.recommended_action}</p>
          </Card>

          <Card title="Evidence">
            <ul className="evidence">
              {b.evidence.map((e, i) => (
                <li key={i}>
                  <span className={`kind kind-${e.type}`}>{e.type === 'ml' ? 'ML' : e.type}</span>
                  <div>
                    {e.text}
                    <small>{e.rule} · source: {e.source}{e.claim_ids.length ? ` · e.g. ${e.claim_ids.join(', ')}` : ''}</small>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          {c.sample_claims.length > 0 && (
            <Card title="Sample claims">
              <div className="table-wrap">
                <table className="claims">
                  <thead><tr><th>Claim</th><th>Date</th><th>Member</th><th>Code</th><th className="num">Paid</th><th>Why flagged</th></tr></thead>
                  <tbody>
                    {c.sample_claims.map((s) => (
                      <tr key={s.claim_id}>
                        <td>{s.claim_id}</td><td>{s.date}</td><td>{s.member_id}</td><td>{s.procedure_code}</td>
                        <td className="num">{money(s.paid_amount)}</td><td>{s.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          <Card title="Timeline" tag="claims per month, flagged in red">
            <div className="bars">
              {b.timeline.monthly.map((m) => (
                <div key={m.month} className="bar" title={`${m.month}: ${m.claims} claims, ${m.flagged} flagged`}>
                  <div className="bar-stack" style={{ height: `${(m.claims / maxClaims) * 100}%` }}>
                    <div className="bar-flag" style={{ height: `${(m.flagged / m.claims) * 100}%` }} />
                  </div>
                  <span>{m.month.slice(5)}</span>
                </div>
              ))}
            </div>
            <ul className="events">
              {b.timeline.events.map((e, i) => <li key={i}><time>{e.date}</time> {e.event}</li>)}
            </ul>
          </Card>
        </div>

        <div className="col">
          <Card title="Confidence and routing">
            <p className="route"><strong>{conf.label}:</strong> {conf.route}. Owner: {conf.owner}.</p>
            <table className="kv">
              <tbody>
                <tr><td>Evidence strength</td><td>{pct(conf.evidence_strength)}</td></tr>
                <tr><td>Precedent adjustment</td><td>{conf.precedent_adjustment >= 0 ? '+' : ''}{Math.round(conf.precedent_adjustment * 100)} pts</td></tr>
                <tr><td>Methods agreeing</td><td>{c.signals.families_agreeing} of 3</td></tr>
                <tr><td>Rules / anomaly / network</td><td>{pct(c.signals.rules)} / {pct(c.signals.ml)} / {pct(c.signals.graph)}</td></tr>
                <tr><td>30 / 60 / 90-day risk</td><td>{pct(b.prediction.p30)} / {pct(b.prediction.p60)} / {pct(b.prediction.p90)}</td></tr>
              </tbody>
            </table>
          </Card>

          <Card title="Precedents from the Second Brain" tag={`pages read: ${b.pages_read.length}`}>
            {b.precedents.length === 0 && <p>No similar closed cases yet.</p>}
            {b.precedents.map((p) => (
              <div key={p.case_id} className="prec">
                <a className="wikilink" href={`#/brain/${p.case_id}`}>{p.case_id}</a>{' '}
                <Status status={p.verdict} /> <small>{p.why.join(', ')} · closed {p.closed}</small>
                <p>{p.reasoning}</p>
              </div>
            ))}
            <p className="trail">
              Read: {b.pages_read.map((n, i) => (
                <span key={n}>{i > 0 && ' → '}<a className="wikilink" href={`#/brain/${n}`}>{n}</a></span>
              ))}
            </p>
            <h4>Policy cited</h4>
            <p><strong>{b.policy.id} {b.policy.title}.</strong> {b.policy.text}</p>
            <small>{b.policy.note}. Public basis: {b.policy.public_basis}.</small>
          </Card>

          <Card title="Network context">
            <p>{b.network_context}</p>
            <Network providerId={c.provider_id} />
          </Card>

          <Card title="Limitations">
            <ul className="plain">{b.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
          </Card>

          <Verdict c={c} onDone={load} />
        </div>
      </div>
    </div>
  )
}

function Verdict({ c, onDone }) {
  const [verdict, setVerdict] = useState('confirmed')
  const [reasoning, setReasoning] = useState('')
  const [investigator, setInvestigator] = useState('')
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(null)
  const body = { verdict, reasoning, investigator }
  const ready = reasoning.trim().length >= 10 && investigator.trim().length >= 2

  if (c.status !== 'open' && !saved) {
    return (
      <Card title="Investigator decision">
        <p>This case is closed as <Status status={c.status} />. It is now precedent:{' '}
          <a className="wikilink" href={`#/brain/${c.case_id}`}>{c.case_id}</a>.</p>
      </Card>
    )
  }
  if (saved) {
    return (
      <Card title="Saved to the Second Brain">
        <p>Pages updated: {saved.changes.map((x, i) => (
          <span key={x.page}>{i > 0 && ', '}<a className="wikilink" href={`#/brain/${x.page}`}>{x.page}</a></span>
        ))}. Similar open cases are re-scored with this precedent.</p>
        <a className="btn" href="#/">Back to queue</a>
      </Card>
    )
  }
  const run = (fn, then) => { setError(null); fn(c.case_id, body).then(then).catch((e) => setError(e.message)) }

  return (
    <Card title="Investigator decision" tag="human in the loop">
      <div className="seg wide">
        {['confirmed', 'cleared', 'inconclusive'].map((v) => (
          <button key={v} className={v === verdict ? 'on' : ''} onClick={() => { setVerdict(v); setPreview(null) }}>{v}</button>
        ))}
      </div>
      <label className="field">Reasoning (becomes precedent)
        <textarea rows="3" value={reasoning} onChange={(e) => { setReasoning(e.target.value); setPreview(null) }}
          placeholder="What did the records show?" />
      </label>
      <label className="field">Investigator name
        <input value={investigator} onChange={(e) => setInvestigator(e.target.value)} />
      </label>
      {error && <p className="notice error">{error}</p>}
      {!preview && <button className="btn" disabled={!ready} onClick={() => run(api.previewVerdict, setPreview)}>Preview Second Brain changes</button>}
      {preview && (
        <div className="diff">
          {preview.lesson && (
            <>
              <h4>Lesson written by the LLM</h4>
              <p>{preview.lesson}</p>
            </>
          )}
          <h4>Proposed changes</h4>
          {preview.changes.map((ch) => (
            <div key={ch.page}>
              <strong>{ch.action} {ch.path}</strong>
              <pre>{ch.added.slice(0, 5).map((l) => '+ ' + l).join('\n')}</pre>
            </div>
          ))}
          <button className="btn primary" onClick={() => { setError(null); api.submitVerdict(c.case_id, { ...body, lesson: preview.lesson || '' }).then(setSaved).catch((e) => setError(e.message)) }}>Approve and save</button>
          <button className="btn" onClick={() => setPreview(null)}>Edit</button>
        </div>
      )}
    </Card>
  )
}

function Stat({ label, value }) {
  return <div className="stat"><span>{label}</span><strong>{value}</strong></div>
}

function Card({ title, tag, children }) {
  return (
    <section className="card">
      <h3>{title}{tag && <small>{tag}</small>}</h3>
      {children}
    </section>
  )
}
