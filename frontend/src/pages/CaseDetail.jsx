import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import SignIn, { useSession } from '../components/SignIn.jsx'
import { Doubt, Icon, Loading, Meter, Status, Tier, bits, money, pct, toast, words } from '../components/bits.jsx'
import AuditNext, { Playbook } from '../components/AuditNext.jsx'
import ClinicalAuditCard from '../components/ClinicalAuditCard.jsx'
import Network from './Network.jsx'
import { getRegion, terms } from '../region.js'

const VERDICTS = [['confirmed', 'Confirm fraud'], ['cleared', 'Clear'], ['inconclusive', 'Inconclusive']]
// Same thresholds as families_agreeing in backend/pipeline/run_all.py.
const AGREE = { rules: 0.3, ml: 0.25, graph: 0.5 }
// Rule hits that are logically impossible, not just unusual. Only these get the red conflict treatment.
// Each parser turns the claim's detail text into two sides (what was billed, what the record says) and the gap between them.
const IMPOSSIBLE = [
  [/Billed at (\S+) and (\S+), (\d+) km apart, within (\d+) min/, (m, s) => ({
    title: 'Physically impossible travel', speed: m[3] / m[4],
    a: ['Billed at', m[1], s.date], b: ['Also billed at', m[2], `within ${m[4]} min`],
    gaps: [['Distance', `${m[3]} km`], ['Elapsed time', `${m[4]} min`], ['Speed required', `${Math.round(m[3] / (m[4] / 60)).toLocaleString('en-US')} km/h`]],
  })],
  [/Admitted (.+?) while an inpatient at (\S+) under (\S+) \(admitted (.+?), discharged (.+?)\); stays overlap by (\d+) h/, (m, s) => ({
    title: 'Two inpatient stays at once',
    a: ['This admission', s.claim_id, m[1]], b: [`Inpatient at ${m[2]}`, m[3], `${m[4]} to ${m[5]}`],
    gaps: [['Overlap', `${m[6]} hours`]],
  })],
  [/Admitted (.+?), (\d+) days after the beneficiary's recorded death on (.+)/, (m, s) => ({
    title: 'Admission after recorded death',
    a: ['Admitted', s.claim_id, m[1]], b: ['Death recorded', s.member_id, m[3]],
    gaps: [['Days after death', m[2]]],
  })],
  [/Package (\S+) \((.+?)\) billed for a male beneficiary/, (m, s) => ({
    title: 'Female-only package billed for a man',
    a: ['Package billed', m[1], m[2]], b: ['Beneficiary', s.member_id, 'Recorded as male'],
    gaps: [['Eligible', 'Female beneficiaries only']],
  })],
  [/Admitted (.+?), before the hospital's empanelment on (.+)/, (m, s) => ({
    title: 'Admission before empanelment',
    a: ['Admitted', s.claim_id, m[1]], b: ['Empanelled from', 'Scheme registry', m[2]],
    gaps: [['Status on admission', 'Not empanelled']],
  })],
]
const impossible = (s) => {
  for (const [re, make] of IMPOSSIBLE) {
    const m = s.detail.match(re)
    if (m) return { speed: 0, ...make(m, s) }
  }
  return null
}
// Whether any sample claim on a case is logically impossible (the landing page picks its example with this).
export const hasConflict = (c) => c.sample_claims.some((s) => impossible(s))
const claimCount = (e) => Number(((e.text.match(/^([\d,]+) claims/) || [])[1] || '').replace(/,/g, ''))
// How much one finding weighs: rules by their share of flagged claims, the model and network by their own scores.
const weight = (e, c) => {
  if (e.type === 'ml') return c.signals.ml
  if (e.type === 'graph') return Math.max(c.signals.graph, Number((e.text.match(/Network risk ([\d.]+)/) || [])[1] || 0))
  if (e.type !== 'rule') return 0.2
  const n = claimCount(e)
  return n && c.n_flagged ? Math.min(1, n / c.n_flagged) * c.signals.rules : c.signals.rules
}
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const scrollTo = (id) => document.getElementById(id)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'nearest' })

// Layout: the case file reads top to bottom on the left; the decision panel on the right
// stays in view while you read, so the route, the score and the verdict are always one glance away.
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

  const region = getRegion()
  const flaggedCodes = new Set(c.sample_claims.map((s) => s.procedure_code))
  const rules = Object.entries(c.rule_counts || {}).sort((x, y) => y[1] - x[1])

  // Four pods in Gutenberg order. Left column, the reading path: identity (top-left), then the forensic discrepancy.
  // Right column: confidence (top-right), then the action plan ending in the decision (bottom-right, the terminal area).
  return (
    <article className={open ? 'case has-bar' : 'case'}>
      <nav className="crumbs" aria-label="Breadcrumb"><a href="#/queue">Case queue</a><span aria-hidden="true">/</span><span aria-current="page">{c.case_id}</span></nav>

      <div className="case-body">
        <div className="doc">
          <section className="pod pod-identity" aria-labelledby="pod-identity">
            <p className="pod-label" id="pod-identity">Subject identity</p>
            <header className="case-head">
              <div>
                <p className="case-id">{c.provider_id}<span>{c.case_id}</span></p>
                <h1>{c.provider_name}</h1>
                {h ? (
                  <p>{c.specialty} in {c.city}, {h.state}. {h.beds} beds, tier {h.city_tier} city, NABH {h.nabh_status}, {h.sector}{h.teaching ? ', teaching' : ''}. Owned by {c.owner_name} (<span className="id">{c.owner_id}</span>).</p>
                ) : (
                  <p>{c.specialty} in {c.city}. Owned by {c.owner_name} (<span className="id">{c.owner_id}</span>).</p>
                )}
              </div>
              <div className="page-actions">
                <a className="btn" href={api.fhirUrl(c.case_id)} target="_blank" rel="noreferrer"><Icon name="export" />Export FHIR</a>
                <button type="button" className="btn" onClick={() => window.print()}><Icon name="print" />Print</button>
                {open && <button type="button" className="btn primary" onClick={() => scrollTo('verdict')}>Record decision</button>}
              </div>
            </header>
            <dl className="facts">
              <div><dt>Primary pattern</dt><dd className="cap">{words(c.pattern)}</dd></div>
              <div><dt>Potential exposure</dt><dd>{money(c.potential_dollars)}</dd><dd><LogRuler value={c.potential_dollars} region={region} /></dd></div>
              <div><dt>{t.Members} affected</dt><dd>{c.member_impact}</dd></div>
              <div><dt>Claims flagged</dt><dd>{c.n_flagged.toLocaleString('en-US')} <small>of {c.n_claims.toLocaleString('en-US')}</small></dd>
                {c.total_paid > 0 && <dd className="sub">{money(c.total_paid)} paid in total</dd>}</div>
            </dl>
          </section>

          <p className="pod-label" id="pod-forensic">Forensic discrepancy</p>
          <Discrepancy c={c} />
          <ClinicalAuditCard caseId={c.case_id} />
          <Section title="Brief">
            <p className="lead">{b.summary}</p>
            <p className={`ground ${b.grounding.passed ? 'ok' : 'bad'}`}>
              <b>{b.grounding.passed ? 'Fact-checked' : 'Fact check failed'}</b>
              Written by {b.generated_by === 'template' ? 'a template' : 'the language model'}. {b.grounding.verified} of {b.grounding.tokens_checked} IDs, codes and {t.amounts} match the claims data.
            </p>
          </Section>

          <Section title="Evidence" note={`${b.evidence.length} ${b.evidence.length === 1 ? 'finding' : 'findings'}, strongest first. Faded findings carry little weight on their own.`}>
            <ol className="evidence">
              {b.evidence.map((e) => ({ e, w: weight(e, c) })).sort((x, y) => y.w - x.w).map(({ e, w }, i) => (
                <li key={i} className={w < 0.3 ? 'weak' : undefined}>
                  <span className="ev-side">
                    <span className={`kind kind-${e.type}`}>{e.type === 'ml' ? 'Model' : e.type === 'graph' ? 'Network' : e.type === 'history' ? 'History' : 'Rule'}</span>
                    <span className="ev-weight" title={`Weight ${pct(w)}`}><Meter value={w} tone={w < 0.3 ? 'muted' : 'accent'} /></span>
                  </span>
                  <div>
                    <p>{e.text}</p>
                    <small>{e.rule}. Source: {e.source}{e.claim_ids.length ? <>. For example <span className="id">{e.claim_ids.join(', ')}</span></> : ''}.</small>
                  </div>
                </li>
              ))}
            </ol>
            {rules.length > 0 && (
              <table className="rule-hits">
                <caption>Rule hits</caption>
                <thead><tr><th>Rule</th><th className="num">Claims</th><th>Share of flagged</th></tr></thead>
                <tbody>
                  {rules.map(([r, n]) => (
                    <tr key={r}><td>{r}</td><td className="num">{n.toLocaleString('en-US')}</td>
                      <td><Meter value={c.n_flagged ? n / c.n_flagged : 0} tone="muted" /> {pct(c.n_flagged ? n / c.n_flagged : 0)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}
            {c.anomaly_drivers && <p className="drivers"><b>Model drivers:</b> {c.anomaly_drivers}.</p>}
          </Section>

          <div className="pair">
            <Section title="Claims over time" note="Claims per month; the dark part was flagged.">
              <Timeline monthly={b.timeline.monthly} />
              <ol className="events" aria-label="Case chronology">
                {b.timeline.events.map((e, i) => <li key={i}><time>{e.date}</time> {e.event}</li>)}
              </ol>
            </Section>
            <Section title="Network" note={`Select a ${t.provider} to see how it connects.`}>
              <p>{b.network_context}</p>
              <Network providerId={c.provider_id} />
            </Section>
          </div>

          {c.sample_claims.length > 0 && (
            <Section title={`Claims and ${h ? 'packages' : 'codes'}`} note={`${c.sample_claims.length} sample claims. Rows in red are logically impossible.`}>
              <div className="table-wrap" tabIndex="0" role="region" aria-label="Sample claims">
                <table className="claims">
                  <thead><tr><th>Claim</th><th>Date</th><th>{t.Member}</th><th>{h ? 'Package' : 'Code'}</th><th className="num">Paid</th><th>Why flagged</th></tr></thead>
                  <tbody>
                    {c.sample_claims.map((s) => (
                      <tr key={s.claim_id} className={impossible(s) ? 'impossible' : undefined}>
                        <td className="id">{s.claim_id}</td><td>{s.date}</td><td className="id">{s.member_id}</td><td><span className="id">{s.procedure_code}</span>{s.package && <small>{s.package}</small>}</td>
                        <td className="num">{money(s.paid_amount)}</td><td>{s.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {c.codes?.length > 0 && (
                <div className="codes">
                  <p>{c.codes.length} {h ? 'packages' : 'codes'} billed by this {t.provider}. Outlined ones appear in the flagged claims above.</p>
                  <ul>{c.codes.map((k) => <li key={k} className={flaggedCodes.has(k) ? 'hit' : undefined}>{k}</li>)}</ul>
                </div>
              )}
            </Section>
          )}

          <Section title="Authority and precedent" note={`Policy cited, and closed cases the Second Brain matched from ${b.pages_read.length} pages read.`}>
            <div className="policy">
              <p className="policy-id">{b.policy.id}</p>
              <p><strong>{b.policy.title}.</strong> {b.policy.text}</p>
              <small>{b.policy.note}. Public basis: {b.policy.public_basis}.</small>
            </div>
            {b.precedents.length === 0 && <p className="muted">No similar closed cases yet. This decision will be the first.</p>}
            {b.precedents.map((p) => (
              <div key={p.case_id} className="prec">
                <p><a className="wikilink" href={`#/brain/${p.case_id}`}>{p.case_id}</a> <Status status={p.verdict} /> <small>{p.why.join(', ')}, closed {p.closed}</small></p>
                <p className="muted">{p.reasoning}</p>
              </div>
            ))}
            <p className="trail">
              Pages read: {b.pages_read.map((n, i) => (
                <span key={n}>{i > 0 && ', '}<a className="wikilink" href={`#/brain/${n}`}>{n}</a></span>
              ))}
            </p>
          </Section>
          <Section title={`Limitations (${b.limitations.length})`} collapsed>
            <ul className="plain">{b.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
          </Section>
        </div>

        <aside className="rail" aria-label="Confidence and action plan">
          <section className="pod pod-confidence" aria-labelledby="pod-confidence">
            <p className="pod-label" id="pod-confidence">Algorithmic confidence</p>
            <div className="conf-main">
              <strong>{pct(conf.score)}</strong>
              {c.status === 'open' && !saved ? <Tier tier={conf.tier} /> : <Status status={c.status === 'open' ? 'open' : c.status} />}
            </div>
            <Chance label="Needs attention" p={conf.score} />
            <Chance label={`Repeats within ${horizon} days`} p={b.prediction.probability} />
            <p className="conf-ctx">From {c.n_claims.toLocaleString('en-US')} claims. <b>{c.signals.families_agreeing} of 3</b> detection methods agree.</p>
            <Bar label="Rules" value={c.signals.rules} th={AGREE.rules} />
            <Bar label="Anomaly model" value={c.signals.ml} th={AGREE.ml} />
            <Bar label="Network analysis" value={c.signals.graph} th={AGREE.graph} />
            <p className="why-note">Each bar is that method's score. The mark is where it starts to count as agreeing; filled blue means it does.</p>
            <Bar label="Evidence strength" value={conf.evidence_strength} strong />
            <details className="how">
              <summary>How the score is built</summary>
              <dl className="kv">
                <div><dt>Evidence strength</dt><dd>{pct(conf.evidence_strength)}</dd></div>
                <div><dt>Precedent adjustment</dt><dd>{conf.precedent_adjustment >= 0 ? '+' : ''}{Math.round(conf.precedent_adjustment * 100)} pts</dd></div>
                <div><dt>Repeat risk in 30, 60, 90 days</dt><dd>{pct(b.prediction.p30)}, {pct(b.prediction.p60)}, {pct(b.prediction.p90)}</dd></div>
              </dl>
              {conf.precedent_reasons?.length > 0 && <ul className="reasons" aria-label="Precedent adjustment">{conf.precedent_reasons.map((r) => <li key={r}>{r}</li>)}</ul>}
              {conf.formula && <p className="formula">Score = {conf.formula}.</p>}
            </details>
            {conf.contradictions?.length > 0 && (
              <p className="contra"><b>Precedents disagree.</b> {conf.contradictions.join(' and ')} reached opposite verdicts on the same pattern, so neither moved this score.</p>
            )}
          </section>
          <p className="pod-label" id="pod-action">Adaptive action plan</p>
          <div className="route-box">
            <h2>Route and playbook</h2>
            <p className="route-stamp">{c.status === 'open' ? <Tier tier={conf.tier} /> : <Status status={c.status} />}</p>
            <p><strong>{conf.label}.</strong> {conf.route}. Owner: {conf.owner}.</p>
            <Playbook text={b.recommended_action} />
          </div>
          {c.status === 'open' && !saved && <AuditNext caseId={c.case_id} horizon={horizon} />}
          {b.field_audit_checklist && (
            <details className="checklist-box">
              <summary>Field audit checklist ({b.field_audit_checklist.length} steps)</summary>
              <ol className="checklist">{b.field_audit_checklist.map((step, i) => <li key={i}>{step}</li>)}</ol>
            </details>
          )}
          <Verdict c={c} pick={pick} onSaved={() => setSaved(true)} />
        </aside>
      </div>

      {open && <DecisionBar c={c} onPick={decide} />}
    </article>
  )
}

// Narrow screens only (the desktop panel is always visible): keeps the decision one tap away.
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
      <p>Decision for <strong>{c.provider_id}</strong></p>
      <div className="btns">
        {VERDICTS.map(([v, label]) => (
          <button type="button" key={v} tabIndex={hidden ? -1 : 0} className={`btn v-${v}`} onClick={() => onPick(v)}>{label}</button>
        ))}
      </div>
    </div>
  )
}

// th: the score at which this method counts as agreeing, drawn as a tick on the track.
function Bar({ label, value, strong, th }) {
  const agrees = th != null && value >= th
  return (
    <div className={strong ? 'why-row strong' : agrees ? 'why-row agrees' : 'why-row'}>
      <span>{label}</span>
      <span className="why-track" title={th != null ? `Counts as agreeing at ${pct(th)} or more` : undefined}>
        <i style={{ width: `${Math.max(2, value * 100)}%` }} />
        {th != null && <b className="th" style={{ left: `${th * 100}%` }} />}
      </span>
      <b>{pct(value)}</b>
    </div>
  )
}

function Timeline({ monthly }) {
  const max = Math.max(1, ...monthly.map((m) => m.claims))
  const flagged = monthly.reduce((n, m) => n + m.flagged, 0)
  const total = monthly.reduce((n, m) => n + m.claims, 0)
  const peak = monthly.find((m) => m.claims === max)
  const label = (m) => `${MONTHS[+m.month.slice(5) - 1]} ${m.month.slice(0, 4)}`
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
              <span>{MONTHS[+m.month.slice(5) - 1]}{m.month.slice(5) === '01' && <em>{m.month.slice(0, 4)}</em>}</span>
            </div>
          ))}
        </div>
      </div>
      <figcaption>{flagged} of {total} claims flagged. Busiest month: {peak ? label(peak) : 'none'}, {max} claims.</figcaption>
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
      <section id="verdict" className="verdict">
        <h2>Decision</h2>
        <p>Closed as <Status status={c.status} />. This case is now precedent in the Second Brain:{' '}
          <a className="wikilink" href={`#/brain/${c.case_id}`}>{c.case_id}</a>.</p>
      </section>
    )
  }
  if (saved) {
    return (
      <section id="verdict" className="verdict saved">
        <h2>Decision saved</h2>
        <p>It is now precedent. Pages updated: {saved.changes.map((x, i) => (
          <span key={x.page}>{i > 0 && ', '}<a className="wikilink" href={`#/brain/${x.page}`}>{x.page}</a></span>
        ))}.</p>
        <p>Similar open cases were re-scored. Cases that changed route are marked in the queue.</p>
        <div className="btn-row"><a className="btn primary" href="#/queue">See the updated queue</a></div>
      </section>
    )
  }
  const run = (fn, then) => { setError(null); setBusy(true); fn(c.case_id, body).then(then).catch((e) => setError(e.message)).finally(() => setBusy(false)) }
  const done = (r) => { setSaved(r); onSaved(); toast(`Decision saved. ${c.case_id} is now precedent.`) }
  const step = !preview ? 1 : session ? 3 : 2

  return (
    <section id="verdict" className="verdict">
      <h2>Your decision</h2>
      <ol className="steps" aria-label={`Step ${step} of 3`}>
        {['Decide', 'Review changes', 'Approve'].map((s, i) => (
          <li key={s} className={i + 1 < step ? 'done' : i + 1 === step ? 'on' : ''} aria-current={i + 1 === step ? 'step' : undefined}>{s}</li>
        ))}
      </ol>
      <div className="seg wide" role="group" aria-label="Verdict">
        {VERDICTS.map(([v, label]) => (
          <button type="button" key={v} className={`${v === verdict ? 'on' : ''} v-${v}`} aria-pressed={v === verdict}
            onClick={() => { setVerdict(v); setPreview(null) }}>{label}</button>
        ))}
      </div>
      <label className="field">Why? This becomes precedent for similar cases.
        <textarea ref={text} rows="3" value={reasoning} onChange={(e) => { setReasoning(e.target.value); setPreview(null) }}
          placeholder="What did the records show?" />
        <small className={reasoning.trim().length >= 10 ? 'count ok' : 'count'}>{reasoning.trim().length < 10 ? `${10 - reasoning.trim().length} more characters needed` : 'Ready'}</small>
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
          <button className="btn primary" disabled={!ready || busy} onClick={() => run(api.previewVerdict, setPreview)}>{busy ? 'Preparing preview…' : 'Preview changes'}</button>
        </div>
      )}
      {preview && (
        <div className="diff">
          {preview.lesson && (
            <>
              <h3>Lesson the LLM wrote</h3>
              <p>{preview.lesson}</p>
            </>
          )}
          <h3>Second Brain pages that will change</h3>
          {preview.changes.map((ch) => (
            <div key={ch.page}>
              <p><strong>{ch.action}</strong> {ch.path}</p>
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
    </section>
  )
}

// One section of the case file. collapsed: secondary detail starts folded (native <details>).
function Section({ title, note, collapsed, children }) {
  if (collapsed) {
    return (
      <details className="sec fold">
        <summary><h2>{title}</h2></summary>
        {children}
      </details>
    )
  }
  return (
    <section className="sec">
      <h2>{title}</h2>
      {note && <p className="sec-note">{note}</p>}
      {children}
    </section>
  )
}

// The single most damning claim, as a two-sided record with the gap between the sides measured.
// Red only when the claim is logically impossible; otherwise a neutral card with the strongest flagged claim.
export function Discrepancy({ c }) {
  const t = terms()
  const hits = c.sample_claims.map((s) => ({ s, x: impossible(s) })).filter((h) => h.x).sort((a, b) => b.x.speed - a.x.speed)
  const top = hits[0] || (c.sample_claims[0] && { s: c.sample_claims[0] })
  if (!top) return null
  const { s, x } = top
  const ev = c.brief.evidence.find((e) => e.rule === s.rule)
  const n = ev && claimCount(ev)
  const side = ([label, id, when]) => <div className="side"><dt>{label}</dt><dd className="id">{id}</dd><dd>{when}</dd></div>
  return (
    <section className={x ? 'sec conflict' : 'sec'} aria-label={x ? 'Contradiction in the claims' : 'Strongest flagged claim'}>
      <div className="conflict-head">
        <h2>{x ? x.title : 'Strongest flagged claim'}</h2>
        {x && <span className="verdict-tag">Verified conflict</span>}
      </div>
      {x ? (
        <>
          <dl className="sides">{side(x.a)}<div className="side-link" aria-hidden="true" />{side(x.b)}</dl>
          <dl className="gaps">{x.gaps.map(([k, v]) => <div key={k}><dt>{k}</dt><dd>{v}</dd></div>)}</dl>
        </>
      ) : <p className="conflict-why">{s.detail}</p>}
      <dl className="conflict-claim">
        <div><dt>Claim</dt><dd className="id">{s.claim_id}</dd></div>
        <div><dt>Date</dt><dd>{s.date}</dd></div>
        <div><dt>{t.Member}</dt><dd className="id">{s.member_id}</dd></div>
        <div><dt>{c.hospital ? 'Package' : 'Code'}</dt><dd className="id">{s.procedure_code}</dd></div>
        <div><dt>Paid</dt><dd>{money(s.paid_amount)}</dd></div>
      </dl>
      <p className="conflict-src">{s.rule}{n > 1 ? `: ${n.toLocaleString('en-US')} claims like this` : ''}. Source text: “{s.detail}”</p>
    </section>
  )
}

// Probability as distance from a coin flip: the bar grows from the 50% midline, with the uncertainty in bits beside it.
// plain: for an audience, not an investigator. The bits move one layer down, into the tooltip.
export function Chance({ label, p, plain }) {
  const d = p - 0.5
  return (
    <div className="chance" title={plain ? `${bits(p).toFixed(2)} bits of uncertainty (0 is certain, 1 is a coin flip)` : undefined}>
      <span className="chance-label">{label}</span>
      <span className="chance-track" role="img" aria-label={`${pct(p)}, ${Math.abs(Math.round(d * 100))} points ${d >= 0 ? 'above' : 'below'} chance, ${bits(p).toFixed(2)} bits of uncertainty`}>
        <i style={{ left: `${Math.min(50, p * 100)}%`, width: `${Math.abs(d) * 100}%` }} />
      </span>
      <span className="chance-scale" aria-hidden="true"><span>0%</span><span>coin flip</span><span>100%</span></span>
      <b>{pct(p)}</b>
      {!plain && <Doubt p={p} />}
    </div>
  )
}

// Where an amount sits on a log scale, from a clerical error to a large ring.
const RULER = { us: [2, 6, (e) => ['$100', '$1k', '$10k', '$100k', '$1M'][e - 2]], in: [4, 8, (e) => ['₹10k', '₹1L', '₹10L', '₹1Cr', '₹10Cr'][e - 4]] }
function LogRuler({ value, region }) {
  const [lo, hi, label] = RULER[region] || RULER.us
  const x = Math.min(1, Math.max(0, (Math.log10(Math.max(1, value)) - lo) / (hi - lo)))
  const ticks = [lo, (lo + hi) / 2, hi]
  return (
    <span className="ruler" aria-hidden="true" title="Log scale">
      <span className="ruler-track"><b style={{ left: `${x * 100}%` }} /></span>
      <span className="ruler-ticks">{ticks.map((e) => <span key={e}>{label(e)}</span>)}</span>
    </span>
  )
}
