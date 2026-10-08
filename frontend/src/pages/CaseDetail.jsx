import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import SignIn, { useSession } from '../components/SignIn.jsx'
import { Loading, Status, Tier, money, pct, toast, words } from '../components/bits.jsx'
import AuditPlan from '../components/AuditPlan.jsx'
import ClinicalAuditCard from '../components/ClinicalAuditCard.jsx'
import { PrecedentEffects, PrecedentInfluence } from '../components/PrecedentGuard.jsx'
import Network, { RingShieldPanel } from './Network.jsx'
import { terms } from '../region.js'

const VERDICTS = [['confirmed', 'Confirm fraud'], ['cleared', 'Clear'], ['inconclusive', 'Inconclusive']]
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })

export default function CaseDetail({ caseId, horizon }) {
  const [c, setC] = useState(null)
  const [error, setError] = useState(null)
  const [pick, setPick] = useState(null)
  const [saved, setSaved] = useState(false)
  const load = () => api.getCase(caseId, horizon).then(setC).catch((e) => setError(e.message))
  useEffect(() => { setC(null); setSaved(false); load() }, [caseId, horizon])

  if (!c) return <Loading error={error} what={`case ${caseId}`} onRetry={() => { setError(null); load() }} />
  const b = c.brief
  const conf = b.confidence
  const t = terms()
  const h = c.hospital
  const open = c.status === 'open' && !saved
  const decide = (v) => { setPick({ v, at: Date.now() }); scrollTo('verdict') }

  return (
    <div className={open ? 'case has-bar' : 'case'}>
      <a className="back" href="#/">← Back to queue</a>
      <header className="case-head">
        <div>
          <h1><span className="id">{c.provider_id}</span> {c.provider_name}</h1>
          {h ? (
            <p>{c.specialty}, {c.city}, {h.state}. {h.beds} beds, tier {h.city_tier} city, NABH {h.nabh_status}, {h.sector}{h.teaching ? ', teaching' : ''}. Owned by {c.owner_id} {c.owner_name}. Case {c.case_id}.</p>
          ) : (
            <p>{c.specialty}, {c.city}. Owned by {c.owner_id} {c.owner_name}. Case {c.case_id}.</p>
          )}
        </div>
        <div className="case-actions">
          {c.status === 'open' ? <Tier tier={conf.tier} /> : <Status status={c.status} />}
          <a className="btn" href={api.fhirUrl(c.case_id)} target="_blank" rel="noreferrer">Export FHIR JSON</a>
          {open && <button type="button" className="btn primary" onClick={() => scrollTo('verdict')}>Record decision</button>}
        </div>
      </header>

      <section className="stats" aria-label="Case summary">
        <Stat label="Pattern" value={words(c.pattern)} />
        <Stat label="Potential exposure" value={money(c.potential_dollars)} />
        <Stat label={`${t.Members} affected`} value={c.member_impact} />
        <Stat label={`${horizon}-day repeat risk`} value={pct(b.prediction.probability)} />
        <Stat label="Confidence" value={pct(conf.score)} />
      </section>

      {/* One flow of cards in balanced columns: no empty gap under the shorter column on long cases */}
      <div className="flow">
        <Card title="Investigation brief" tag={`written by ${b.generated_by}`} tone="lead">
          <p className="lead">{b.summary}</p>
          <p className={`ground ${b.grounding.passed ? 'ok' : 'bad'}`}>
            <b>{b.grounding.passed ? 'Fact-checked' : 'Fact check failed'}</b>
            {b.grounding.verified} of {b.grounding.tokens_checked} IDs, codes and {t.amounts} match the claims data.
          </p>
          <div className="action-box">
            <h4>Recommended action <small className="source-tag">{b.recommended_action_source}</small></h4>
            <p>{b.recommended_action}</p>
            <AuditPlan caseId={c.case_id}>{b.investigation_playbook && <Playbook p={b.investigation_playbook} />}</AuditPlan>
          </div>
        </Card>

        <Card title="Evidence" tag={`${b.evidence.length} findings`}>
          <ul className="evidence">
            {b.evidence.map((e, i) => (
              <li key={i}>
                <span className={`kind kind-${e.type}`}>{e.type === 'ml' ? 'ML' : e.type}</span>
                <div>
                  {e.text}
                  <small>{e.rule}. Source: {e.source}{e.claim_ids.length ? `. For example ${e.claim_ids.join(', ')}` : ''}</small>
                </div>
              </li>
            ))}
          </ul>
        </Card>

        <Card title="Why this score" tag={`${c.signals.families_agreeing} of 3 methods agree`}>
          <p className="route"><strong>{conf.label}:</strong> {conf.route}. Owner: {conf.owner}.</p>
          <div className="why">
            <Bar label="Rules" value={c.signals.rules} />
            <Bar label="Anomaly model" value={c.signals.ml} />
            <Bar label="Network analysis" value={c.signals.graph} />
            <Bar label="Evidence strength" value={conf.evidence_strength} strong />
          </div>
          <table className="kv">
            <tbody>
              <tr><td>Precedent adjustment</td><td>{conf.precedent_adjustment >= 0 ? '+' : ''}{Math.round(conf.precedent_adjustment * 100)} pts</td></tr>
              <tr><td>30 / 60 / 90-day repeat risk</td><td>{pct(b.prediction.p30)} / {pct(b.prediction.p60)} / {pct(b.prediction.p90)}</td></tr>
            </tbody>
          </table>
        </Card>

        <Card title="Timeline" tag="claims per month">
          <Timeline monthly={b.timeline.monthly} />
          <ul className="events">
            {b.timeline.events.map((e, i) => <li key={i}><time>{e.date}</time> {e.event}</li>)}
          </ul>
        </Card>

        <Card title="Network context" tag={`select a ${t.provider} to trace its links`}>
          <p>{b.network_context}</p>
          <Network providerId={c.provider_id} />
        </Card>

        {c.network && <RingShieldPanel providerId={c.provider_id} />}

        <ClinicalAuditCard caseId={c.case_id} />

        <Verdict c={c} pick={pick} onSaved={() => setSaved(true)} />
        {c.status !== 'open' && <PrecedentInfluence caseId={c.case_id} />}

        <Card title="Precedents from the Second Brain" tag={`pages read: ${b.pages_read.length}`}>
          {b.precedents.length === 0 && <p className="muted">No similar closed cases yet. This verdict will be the first.</p>}
          <PrecedentEffects precedents={b.precedents} effects={conf.precedent_effects} revoked={b.revoked_precedents}
            capped={conf.adjustment_capped} />
          <p className="trail">
            Read: {b.pages_read.map((n, i) => (
              <span key={n}>{i > 0 && ' → '}<a className="wikilink" href={`#/brain/${n}`}>{n}</a></span>
            ))}
          </p>
          <h4>Policy cited</h4>
          <p><strong>{b.policy.id} {b.policy.title}.</strong> {b.policy.text}</p>
          <small>{b.policy.note}. Public basis: {b.policy.public_basis}.</small>
        </Card>
        {b.field_audit_checklist && (
          <Card title="Field audit checklist" tag="for the State Anti-Fraud Unit">
            <ol className="checklist">{b.field_audit_checklist.map((step, i) => <li key={i}>{step}</li>)}</ol>
          </Card>
        )}

        {c.sample_claims.length > 0 && (
          <Card title="Sample claims" tag={`${c.sample_claims.length} shown`} collapsed>
            <div className="table-wrap">
              <table className="claims">
                <thead><tr><th>Claim</th><th>Date</th><th>{t.Member}</th><th>{h ? 'Package' : 'Code'}</th><th className="num">Paid</th><th>Why flagged</th></tr></thead>
                <tbody>
                  {c.sample_claims.map((s) => (
                    <tr key={s.claim_id}>
                      <td>{s.claim_id}</td><td>{s.date}</td><td>{s.member_id}</td><td>{s.procedure_code}{s.package && <small>{s.package}</small>}</td>
                      <td className="num">{money(s.paid_amount)}</td><td>{s.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        )}

        <Card title="Limitations" tag={`${b.limitations.length} caveats`} collapsed>
          <ul className="plain">{b.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
        </Card>
      </div>

      {open && <DecisionBar c={c} onPick={decide} />}
    </div>
  )
}

// Sticky bar so the decision is one tap away from anywhere on a long case; it steps aside once the form is on screen.
function DecisionBar({ c, onPick }) {
  const [hidden, setHidden] = useState(false)
  useEffect(() => {
    const el = document.getElementById('verdict')
    if (!el || !('IntersectionObserver' in window)) return
    const io = new IntersectionObserver(([e]) => setHidden(e.isIntersecting), { rootMargin: '0px 0px -30% 0px' })
    io.observe(el)
    return () => io.disconnect()
  }, [])
  return (
    <div className={hidden ? 'decision-bar hide' : 'decision-bar'} role="region" aria-label="Record a decision" aria-hidden={hidden || undefined}>
      <p><strong>{c.provider_id}</strong> <span>Your decision becomes precedent for similar cases.</span></p>
      <div className="btns">
        {VERDICTS.map(([v, label]) => (
          <button type="button" key={v} tabIndex={hidden ? -1 : 0} className={`btn v-${v}`} onClick={() => onPick(v)}>{label}</button>
        ))}
      </div>
    </div>
  )
}

// Fixed per-pattern steps (US): labelled as a template so nobody reads them as advice generated for this case.
function Playbook({ p }) {
  return (
    <div className="playbook">
      <p className="directive">{p.directive}</p>
      <ol className="checklist">
        {p.steps.map((s) => <li key={s.title}><strong>{s.title}.</strong> {s.detail}</li>)}
      </ol>
      <small>{p.source}. References to verify: {p.references}.</small>
    </div>
  )
}

function Bar({ label, value, strong }) {
  return (
    <div className={strong ? 'why-row strong' : 'why-row'}>
      <span>{label}</span>
      <span className="why-track"><i style={{ width: `${Math.max(2, value * 100)}%` }} /></span>
      <b>{pct(value)}</b>
    </div>
  )
}

function Timeline({ monthly }) {
  const max = Math.max(1, ...monthly.map((m) => m.claims))
  const flagged = monthly.reduce((n, m) => n + m.flagged, 0)
  const total = monthly.reduce((n, m) => n + m.claims, 0)
  const peak = monthly.find((m) => m.claims === max)
  const label = (m) => `${MONTHS[+m.month.slice(5) - 1]} ${m.month.slice(2, 4)}`
  return (
    <figure className="timeline">
      <div className="bars-wrap" role="img"
        aria-label={`${total} claims over ${monthly.length} months, ${flagged} flagged. Busiest month ${peak ? label(peak) : ''} with ${max} claims.`}>
        <div className="axis" aria-hidden="true"><span>{max}</span><span>{Math.round(max / 2)}</span><span>0</span></div>
        <div className="bars">
          {monthly.map((m) => (
            <div key={m.month} className="bar" title={`${label(m)}: ${m.claims} claims, ${m.flagged} flagged`}>
              <div className="bar-stack" style={{ height: `${(m.claims / max) * 100}%` }}>
                <div className="bar-flag" style={{ height: `${m.claims ? (m.flagged / m.claims) * 100 : 0}%` }} />
              </div>
              <span>{MONTHS[+m.month.slice(5) - 1]}</span>
            </div>
          ))}
        </div>
      </div>
      <figcaption>
        <span><i className="key bar-key" /> claims</span>
        <span><i className="key seg-high" /> flagged ({flagged} of {total})</span>
      </figcaption>
    </figure>
  )
}

function Verdict({ c, pick, onSaved }) {
  const [verdict, setVerdict] = useState('confirmed')
  const [reasoning, setReasoning] = useState('')
  const [investigator, setInvestigator] = useState('')
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(null)
  const [busy, setBusy] = useState(false)
  const text = useRef(null)
  const session = useSession()
  // Approval is recorded under the signed-in investigator, so the name follows the session once there is one.
  const name = session ? session.investigator : investigator
  const body = { verdict, reasoning, investigator: name }
  const ready = reasoning.trim().length >= 10 && name.trim().length >= 2

  useEffect(() => {
    if (!pick) return
    setVerdict(pick.v); setPreview(null)
    setTimeout(() => text.current?.focus({ preventScroll: true }), 300)
  }, [pick])

  if (c.status !== 'open' && !saved) {
    return (
      <Card id="verdict" title="Investigator decision">
        <p>This case is closed as <Status status={c.status} />. It is now precedent:{' '}
          <a className="wikilink" href={`#/brain/${c.case_id}`}>{c.case_id}</a>.</p>
      </Card>
    )
  }
  if (saved) {
    return (
      <Card id="verdict" title="Saved to the Second Brain" tone="saved">
        <p>This verdict is now precedent. Pages updated: {saved.changes.map((x, i) => (
          <span key={x.page}>{i > 0 && ', '}<a className="wikilink" href={`#/brain/${x.page}`}>{x.page}</a></span>
        ))}.</p>
        <p>Similar open cases have been re-scored with it. Cases that changed route are marked in the queue.</p>
        <div className="btn-row"><a className="btn primary" href="#/">See the re-ranked queue</a></div>
      </Card>
    )
  }
  const run = (fn, then) => { setError(null); setBusy(true); fn(c.case_id, body).then(then).catch((e) => setError(e.message)).finally(() => setBusy(false)) }
  const done = (r) => { setSaved(r); onSaved(); toast(`Verdict saved · ${c.case_id} is now precedent`) }

  return (
    <Card id="verdict" title="Investigator decision" tag="human in the loop" tone="decide">
      <ol className="steps" aria-label="Steps">
        <li className={preview ? 'done' : 'on'}>Decide</li>
        <li className={preview ? (session ? 'done' : 'on') : ''}>Review changes</li>
        <li className={preview && session ? 'on' : ''}>Approve</li>
      </ol>
      <div className="seg wide" role="group" aria-label="Verdict">
        {VERDICTS.map(([v, label]) => (
          <button type="button" key={v} className={`${v === verdict ? 'on' : ''} v-${v}`} aria-pressed={v === verdict}
            onClick={() => { setVerdict(v); setPreview(null) }}>{label}</button>
        ))}
      </div>
      <label className="field">Reasoning (becomes precedent)
        <textarea ref={text} rows="3" value={reasoning} onChange={(e) => { setReasoning(e.target.value); setPreview(null) }}
          placeholder="What did the records show?" />
        <small className={reasoning.trim().length >= 10 ? 'count ok' : 'count'}>{reasoning.trim().length} / 10 characters minimum</small>
      </label>
      {!session && (
        <label className="field">Investigator name
          <input value={name} onChange={(e) => setInvestigator(e.target.value)} />
        </label>
      )}
      {session && <p className="signed-in">Recording as <strong>{session.investigator}</strong></p>}
      {error && <p className="notice error" role="alert">{error}</p>}
      {!preview && (
        <div className="btn-row">
          <button className="btn primary" disabled={!ready || busy} onClick={() => run(api.previewVerdict, setPreview)}>{busy ? 'Preparing preview…' : 'Preview Second Brain changes'}</button>
        </div>
      )}
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
          <SignIn name={investigator} />
          <div className="btn-row">
            <button className="btn primary" disabled={busy || !session} onClick={() => run((id, b) => api.submitVerdict(id, { ...b, lesson: preview.lesson || '' }), done)}>{busy ? 'Saving…' : 'Approve and save'}</button>
            <button className="btn" onClick={() => setPreview(null)}>Edit</button>
          </div>
        </div>
      )}
    </Card>
  )
}

function Stat({ label, value }) {
  return <div className="stat"><span>{label}</span><strong>{value}</strong></div>
}

// collapsed: secondary detail starts folded (native <details>), so the brief, evidence and decision lead.
function Card({ id, title, tag, tone, collapsed, children }) {
  const cls = tone ? `card card-${tone}` : 'card'
  if (collapsed) {
    return (
      <details className={`${cls} fold`} id={id}>
        <summary><h3>{title}{tag && <small>{tag}</small>}</h3></summary>
        {children}
      </details>
    )
  }
  return (
    <section className={cls} id={id}>
      <h3>{title}{tag && <small>{tag}</small>}</h3>
      {children}
    </section>
  )
}
