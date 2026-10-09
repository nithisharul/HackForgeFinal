import Explore from '../components/Explore.jsx'
import ArchMap from '../components/ArchMap.jsx'
import { Icon, Status, money, pct, useCountUp } from '../components/bits.jsx'
import { terms } from '../region.js'

// The explorable slides of the landing page. Each is one figure with numbered steps (see Explore.jsx):
// presenting, the arrow key walks the steps; on the page they advance while on screen and idle.
// Every figure is drawn from the live API for the selected region; the example case is the one the landing page picked.
// Plain language leads; how a number is computed sits one layer down (a title or a "How it is calculated" line).

const AGREE = { rules: 0.3, ml: 0.25, graph: 0.5 }  // same thresholds as families_agreeing in the pipeline
const cls = (i, at) => (i === at ? 'focus' : 'ctx')

export function Funnel({ s, build }) {
  const t = terms()
  const cases = s.actionable ?? s.open_cases
  const week = Math.min(s.capacity, cases)
  const stages = [
    [s.claims, 'claims analysed'],
    [s.raw_alerts, 'alerts raised by 3 detectors'],
    [cases, s.watch_list != null ? 'cases with evidence' : 'cases opened with evidence'],
    [week, 'cases that fit this week'],
  ]
  const steps = [
    { t: 'Every claim is checked', d: `All ${s.claims.toLocaleString('en-US')} claims in the extract are scored by claim rules, an anomaly model and network analysis.` },
    { t: 'Alerts, not yet cases', d: `${s.raw_alerts.toLocaleString('en-US')} claim alerts touch ${s.providers_with_any_alert} ${t.providers}. On their own, most are noise.` },
    { t: `Grouped by ${t.provider}`, d: s.watch_list != null
      ? `Alerts become ${cases} cases with enough evidence to open, plus ${s.watch_list} ${t.providers} on a watch list that is monitored, not opened.`
      : `Alerts become ${s.cases} cases: ${s.fast_track} fast-track, ${s.review} for review, ${s.not_enough_evidence} with not enough evidence yet.` },
    { t: 'What a team can work', d: `3 investigators at ${s.cases_per_investigator} cases each take the top ${week}, worth ${money(s.dollars_in_capacity)} in potential exposure. One claim in ${Math.round(s.claims / Math.max(1, week)).toLocaleString('en-US')} reaches a person.` },
  ]
  return (
    <section className="section" aria-labelledby="funnel-h">
      <header className="section-head">
        <h2 id="funnel-h">From {s.claims.toLocaleString('en-US')} claims to one week of work</h2>
        <p>Each stage keeps only what has evidence behind it. Bars use a log scale, so all four fit one ruler.</p>
      </header>
      <Explore label="Funnel" steps={steps} build={build} stage={(at) => (
        <ol className="fn">
          {stages.map(([n, label], i) => (
            <li key={label} className={cls(i, at)}>
              <Count n={n} />
              <span className="fn-bar" aria-hidden="true"><i style={{ width: `${Math.max(2, (Math.log10(Math.max(1, n)) / Math.log10(s.claims)) * 100)}%` }} /></span>
              <span className="fn-label">{label}</span>
            </li>
          ))}
        </ol>
      )} />
    </section>
  )
}

function Count({ n }) {
  return <strong className="fn-n">{useCountUp(n).toLocaleString('en-US')}</strong>
}

// One case through the five stages, with its real numbers at each step.
export function Journey({ c, row, total, plan, build }) {
  const t = terms()
  const conf = c.brief.confidence
  const g = c.brief.grounding
  const firstSentence = (c.brief.summary.match(/^.*?[.!?](\s|$)/) || [c.brief.summary])[0].trim()
  const checks = plan?.actions?.slice(0, 2) || []
  const doubt = plan?.prior_entropy_bits || 0
  const steps = [
    { t: 'Detect', d: `Three independent methods score ${c.provider_id}. A case needs agreement before it reaches the queue.` },
    { t: 'Prioritise', d: `Risk, money at stake, people affected, severity and confidence set its place. The team's capacity sets the line.` },
    { t: 'Explain', d: 'The brief is written for the investigator, and every ID, code and amount in it is checked against the claims data.' },
    { t: 'Decide', d: 'A person decides. The plan ranks the checks worth running first, by how much doubt each clears per hour of work.' },
    { t: 'Learn', d: 'Closed cases on the same pattern move this score. Contradicting verdicts cancel out, and old ones count for less.' },
  ]
  const panels = [
    <div className="jr-detect">
      {[['Claim rules', 'rules'], ['Anomaly model', 'ml'], ['Network analysis', 'graph']].map(([label, k]) => {
        const v = c.signals[k], ok = v >= AGREE[k]
        return (
          <div key={k} className="jr-signal">
            <span>{label}</span>
            <span className="jr-track" title={`Counts as agreeing at ${pct(AGREE[k])} or more`}><i className={ok ? 'ok' : undefined} style={{ width: `${Math.max(2, v * 100)}%` }} /><b style={{ left: `${AGREE[k] * 100}%` }} /></span>
            <strong>{pct(v)}</strong>
            <em className={ok ? 'agrees' : undefined}>{ok ? 'Agrees' : 'Below threshold'}</em>
          </div>
        )
      })}
      <p className="jr-sum"><b>{c.signals.families_agreeing} of 3</b> methods agree on {c.provider_id}.</p>
    </div>,
    <dl className="jr-tiles">
      <div><dt>Risk</dt><dd>{pct(row.risk_score)}</dd></div>
      <div><dt>Place in queue</dt><dd>#{row.rank} <small>of {total}</small></dd></div>
      <div><dt>This week</dt><dd>{row.in_capacity ? 'Inside the line' : 'Below the line'}</dd></div>
      <div><dt>Potential exposure</dt><dd>{money(c.potential_dollars)}</dd></div>
    </dl>,
    <div className="jr-explain">
      <blockquote>{firstSentence}</blockquote>
      <p className={g.passed ? 'jr-check ok' : 'jr-check'}><Icon name="check" />{g.verified} of {g.tokens_checked} IDs, codes and {t.amounts} match the claims data.</p>
    </div>,
    <ol className="jr-plan">
      {checks.length === 0 && <li>No plan is available for this case.</li>}
      {checks.map((a, i) => (
        <li key={a.id} className={i === 0 ? 'best' : undefined}>
          <b>{a.name}</b>
          <span>Clears {doubt ? Math.round((a.info_gain_bits / doubt) * 100) : 0}% of the remaining doubt</span>
          <span>{a.cost_mins >= 120 ? `${Math.round(a.cost_mins / 60)} hours` : `${a.cost_mins} min`}, {money(a.cost)}</span>
          {i === 0 && <small>Best value for the time</small>}
        </li>
      ))}
    </ol>,
    <div className="jr-learn">
      <p className="jr-sum">Confidence {pct(conf.score)} = evidence {pct(conf.evidence_strength)} {conf.precedent_adjustment >= 0 ? '+' : '−'} {Math.abs(Math.round(conf.precedent_adjustment * 100))} pts from precedent</p>
      <ul>
        {(conf.precedent_reasons || []).slice(0, 3).map((r) => <li key={r}>{plainReason(r)}</li>)}
        {!conf.precedent_reasons?.length && <li>No closed case has moved this score yet. The first verdict will.</li>}
        <li>When an investigator closes {c.provider_id}, its verdict becomes a precedent like these, and similar open cases are re-scored at once.</li>
      </ul>
    </div>,
  ]
  return (
    <section className="section" aria-labelledby="how-h">
      <header className="section-head">
        <h2 id="how-h">How it works, on one real case</h2>
        <p>Follow {c.provider_id} ({c.provider_name}) through all five stages. Every number below is live.</p>
      </header>
      <Explore label={`How it works on ${c.provider_id}`} steps={steps} build={build} stage={(at) => (
        <div className="jr">
          <ol className="jr-chain">{steps.map((s, i) => <li key={s.t} className={cls(i, at)}><span className="step-n">{i + 1}</span>{s.t}</li>)}</ol>
          <div key={at} className="jr-panel">{panels[at]}</div>
        </div>
      )} />
    </section>
  )
}

// "+0.04 INV039 confirmed (same pattern), weight 0.72 for age" -> "+4 pts: INV039, confirmed, same pattern (counts 72% for its age)"
function plainReason(r) {
  const m = r.match(/^([+-]?\d*\.\d+)\s+(\S+)\s+(\w+)\s*\(([^)]*)\)(?:,\s*weight\s+([\d.]+)\s+for age)?/)
  if (!m) return r
  const pts = Math.round(Number(m[1]) * 100)
  return (
    <>
      <b>{pts >= 0 ? '+' : '−'}{Math.abs(pts)} pts</b> <a className="wikilink" href={`#/brain/${m[2]}`}>{m[2]}</a> <Status status={m[3]} /> {m[4]}
      {m[5] && <small> · counts {Math.round(Number(m[5]) * 100)}% for its age</small>}
    </>
  )
}

// The two scoring formulas on the example case: block width = the weight, fill = how much of that weight the case earned.
export function Scoring({ c, row, rows, region, build }) {
  const t = terms()
  const maxD = Math.max(...rows.map((r) => r.potential_dollars), 1)
  const maxM = Math.max(...rows.map((r) => r.member_impact), 1)
  const sg = c.signals
  const risk = [['Claim rules', 0.35, sg.rules, 'rule'], ['Anomaly model', 0.2, Math.min(1, sg.ml * 2), 'ml'], ['Network', 0.2, sg.graph, 'graph'],
    ['BiRank', 0.05, sg.birank, 'graph'], ['Repeat risk', 0.2, row.p_horizon, 'pred']]
  const prio = [['Risk', 0.3, row.risk_score], ['Money at stake', 0.2, Math.log1p(row.potential_dollars) / Math.log1p(maxD)],
    [t.Members === 'Members' ? 'People affected' : 'Beneficiaries', 0.1, Math.log1p(row.member_impact) / Math.log1p(maxM)],
    ['Severity', 0.15, row.severity], ['Confidence', 0.25, row.confidence]]
  const capacity = rows.filter((r) => r.in_capacity).length
  const steps = [
    { t: 'Risk: how likely this is a problem', d: `Each block's width is how much that method counts; the fill is how strongly it flags ${c.provider_id}. Together: ${pct(row.risk_score)}.` },
    { t: 'Priority: what to open first', d: `Risk is one input. Money at stake and ${t.member === 'member' ? 'people' : 'beneficiaries'} affected are on a log scale, so one huge case cannot drown the rest.` },
    { t: 'The line for this week', d: `${c.provider_id} ranks #${row.rank} of ${rows.length}. With 3 investigators the first ${capacity} cases fit this week; change the team size in the app and the line moves.` },
  ]
  return (
    <section className="section" aria-labelledby="score-h">
      <header className="section-head">
        <h2 id="score-h">Why {c.provider_id} is at the top</h2>
        <p>The two scores behind every place in the queue, filled in for one real case.</p>
      </header>
      <Explore label="Scoring" steps={steps} build={build} stage={(at) => (
        <div className="sc">
          <Stack name="Risk" total={row.risk_score} terms={risk} state={cls(0, at)} />
          <Stack name="Priority" total={row.priority} terms={prio} state={cls(1, at)} />
          <div className={`sc-queue ${cls(2, at)}`} aria-label={`${c.provider_id} ranks ${row.rank} of ${rows.length}; ${capacity} fit this week`}>
            <p className="sc-name">Queue <span>first {capacity} fit this week</span></p>
            <ol>
              {rows.map((r) => <li key={r.case_id} className={`${r.in_capacity ? 'in' : ''}${r.case_id === c.case_id ? ' me' : ''}`} title={`#${r.rank} ${r.provider_id}`} />)}
            </ol>
          </div>
        </div>
      )} />
    </section>
  )
}

function Stack({ name, total, terms: parts, state }) {
  return (
    <figure className={`sc-row ${state}`} aria-label={`${name} ${pct(total)}: ${parts.map(([l, w, v]) => `${l} ${pct(w)} weight, scores ${pct(v)}`).join('; ')}`}>
      <figcaption className="sc-name">{name} <strong>{pct(total)}</strong></figcaption>
      <div className="sc-bar" aria-hidden="true">
        {parts.map(([label, w, v, fam]) => (
          <div key={label} className={fam ? `sc-seg f-${fam}` : 'sc-seg'} style={{ flexGrow: w * 100 }} title={`${label}: ${pct(w)} of the score; this case scores ${pct(v)}, adding ${Math.round(w * v * 100)} points`}>
            <span className="sc-fill"><i style={{ width: `${Math.max(1, v * 100)}%` }} /></span>
            <b>{label}</b>
            <small>{pct(w)} weight</small>
            <small>scores {pct(v)}</small>
          </div>
        ))}
      </div>
    </figure>
  )
}

export function Architecture({ region, build }) {
  return (
    <section className="section" aria-labelledby="arch-h">
      <header className="section-head">
        <h2 id="arch-h">Architecture</h2>
        <p>Detection runs offline and the app serves its saved results, so a detector outage never takes the investigators' app down.</p>
      </header>
      <ArchMap region={region} build={build} />
    </section>
  )
}

export function Safeguards({ c, health, region, build }) {
  const t = terms()
  const dets = health ? Object.values(health.pipeline.detectors) : []
  const llm = health?.llm
  const pillars = [
    ['check', 'Human in the loop', 'The system finds leads. Only a person closes a case.', [
      'Every verdict needs a written reason and a preview of each page it will change',
      'A signed-in investigator approves it; the server checks the role',
      'The LLM writes text only and never scores, ranks or decides',
      'A precedent can be withdrawn, and every score it moved is undone']],
    ['shield', 'Data privacy', "Case data stays on the payer's servers.", [
      `${t.Members} appear only as tokens${region === 'in' ? '; no name, Aadhaar or mobile number reaches the Second Brain' : ''}`,
      'The default LLM setup runs on the same machine, so no claim leaves it',
      'Slack, Teams and webhook messages carry IDs and a link, never claim lines',
      'API responses are not cached; logs record paths, never query strings']],
    ['info', 'When a method is down', 'Detection runs offline, so investigators keep working.', [
      'Each detector runs on its own; one failing never stops the others',
      'Scoring weights are spread over the detectors that ran',
      'Affected briefs carry a caution and the app shows a degraded-mode banner',
      'Without the LLM, briefs and answers fall back to templates']],
  ]
  const steps = [
    { d: c ? `${c.case_id} is ${c.status === 'open' ? 'open and waiting for an investigator. Nothing closes it automatically.' : `closed as ${c.status} by an investigator.`}` : 'Every case waits for a person.' },
    { d: llm ? (llm.configured ? `LLM: ${llm.model}, ${llm.reachable ? 'reachable on the payer side' : 'not reachable, so templates are in use'}.` : 'No LLM is connected: briefs use templates and nothing is sent anywhere.') : 'Checking the LLM connection.' },
    { d: dets.length ? `Last pipeline run: ${dets.map((d) => `${d.label} ${d.ok ? 'ran' : 'did not run'}`).join(', ')}.` : 'Detector status is recorded from the next pipeline run.' },
  ]
  return (
    <section className="section" aria-labelledby="safe-h">
      <header className="section-head">
        <h2 id="safe-h">People decide, data stays put, and no single failure stops the work</h2>
      </header>
      <Explore label="Safeguards" steps={steps.map((x, i) => ({ t: pillars[i][1], d: `Now: ${x.d}` }))} build={build} stage={(at) => (
        <div className="pillars">
          {pillars.map(([icon, title, lead, items], i) => (
            <div key={title} className={`pillar ${cls(i, at)}`}>
              <h3><span className="feature-icon"><Icon name={icon} /></span>{title}</h3>
              <p>{lead}</p>
              <ul className="plain">{items.map((x) => <li key={x}>{x}</li>)}</ul>
            </div>
          ))}
        </div>
      )} />
    </section>
  )
}

export function Security({ c, sec, build }) {
  const t = terms()
  const g = c?.brief.grounding
  const events = sec ? Object.values(sec.events || {}).reduce((x, y) => x + y, 0) : null
  const cards = [
    ['shield', 'Identity and access', 'Salted PBKDF2 passcodes, signed 8-hour sessions, a lockout after 5 failures. Four roles, checked on the server for every save.',
      'Viewer, investigator, lead and admin. The signed-in name is what gets recorded, whatever a form says.'],
    ['check', 'Tamper-evident audit log', 'Every approved change is chained and signed, with a fingerprint of each file it wrote.',
      sec ? `${sec.files_checked} knowledge files checked against ${sec.entries} signed ${sec.entries === 1 ? 'entry' : 'entries'}; chain ${sec.chain_valid ? 'intact' : 'broken'}${sec.ok ? '' : `, ${sec.problems.length} alert(s)`}.` : 'Checking the log.'],
    ['search', 'LLM guardrails', 'Pasted documents are scanned for prompt injection before the LLM reads them, and its facts are checked after.',
      g ? `${g.verified} of ${g.tokens_checked} IDs, codes and ${t.amounts} in the ${c.provider_id} brief are verified. Text that names anything else is discarded.` : 'Facts in every brief are checked against the data.'],
    ['network', 'Hardened API', 'Security headers, an origin allowlist, a request ID on every response and a JSON log line per request.',
      events != null ? `${events} security ${events === 1 ? 'event' : 'events'} recorded on this server. High and critical ones also go to Slack or Teams when configured.` : 'Events are recorded with severity and action.'],
  ]
  return (
    <section className="section" aria-labelledby="security-h">
      <header className="section-head">
        <h2 id="security-h">Security by design</h2>
        <p>Defence in layers, each one checkable. Live from this server.</p>
      </header>
      <Explore label="Security" steps={cards.map(([, title, , live]) => ({ t: title, d: live }))} build={build} stage={(at) => (
        <div className="features four">
          {cards.map(([icon, title, text], i) => (
            <div key={title} className={`feature ${cls(i, at)}`}><span className="feature-icon"><Icon name={icon} /></span><h3>{title}</h3><p>{text}</p></div>
          ))}
        </div>
      )} />
    </section>
  )
}

// Flags as line art in the app's own palette (red is kept for verified contradictions). On hover or focus the
// US stars come on one by one and the Ashoka chakra turns in. Transform and opacity only.
function Flag({ code }) {
  if (code === 'us') {
    const stars = []
    for (let r = 0; r < 4; r++) for (let c = 0; c < 5; c++) stars.push([7 + c * 6 + (r % 2) * 3, 6 + r * 5])
    return (
      <svg className="flag flag-us" viewBox="0 0 72 44" aria-hidden="true">
        <rect className="fl-frame" x="0.75" y="0.75" width="70.5" height="42.5" rx="3" />
        {[0, 1, 2, 3, 4, 5, 6].map((i) => <rect key={i} className="fl-stripe" x="1" y={1 + i * 6.1} width="70" height="3.05" />)}
        <rect className="fl-canton" x="1" y="1" width="36" height="24" />
        {stars.map(([x, y], i) => <circle key={i} className="fl-star" cx={x} cy={y} r="1.3" style={{ '--i': i }} />)}
      </svg>
    )
  }
  return (
    <svg className="flag flag-in" viewBox="0 0 72 44" aria-hidden="true">
      <rect className="fl-frame" x="0.75" y="0.75" width="70.5" height="42.5" rx="3" />
      <rect className="fl-band top" x="1" y="1" width="70" height="14" />
      <rect className="fl-band bottom" x="1" y="29" width="70" height="14" />
      <g className="fl-chakra">
        <circle cx="36" cy="22" r="6" />
        {Array.from({ length: 24 }, (_, i) => <line key={i} x1="36" y1="22" x2={36 + 6 * Math.cos((i * Math.PI) / 12)} y2={22 + 6 * Math.sin((i * Math.PI) / 12)} />)}
      </g>
    </svg>
  )
}

export function Regions({ region, onSwitch }) {
  const sides = [
    ['us', 'United States', 'CMS-style provider claims', 'Polices the procedure-code line.',
      ['Duplicate claims', 'Impossible travel between facilities', 'Bundling pairs from the CMS NCCI table', 'Units above CMS limits', 'Visit-level drift']],
    ['in', 'India', 'PM-JAY-style hospital admissions', 'Polices the hospital admission.',
      ['Overlapping admissions', 'Claims after recorded death', 'Package mismatch on diagnosis, sex or rate', 'Admissions above bed strength', 'Agent rings across hospitals']],
  ]
  return (
    <section className="section" aria-labelledby="regions-h">
      <header className="section-head">
        <h2 id="regions-h">One engine, two systems</h2>
        <p>The same anomaly model, network analysis, prediction models and Second Brain. Each region keeps its own data, models and knowledge.</p>
      </header>
      <div className="regions">
        {sides.map(([code, name, data, line, rules]) => {
          const here = code === region
          return (
            <button key={code} type="button" className={here ? 'region-card here' : 'region-card'} aria-pressed={here}
              onClick={() => !here && onSwitch?.(code)}>
              <span className="region-top"><Flag code={code} /><span><b>{name}</b><small>{data}</small></span></span>
              <span className="region-line">{line}</span>
              <span className="region-rules">{rules.map((r) => <span key={r}>{r}</span>)}</span>
              <span className="region-hint">{here ? 'Showing now' : `Select to switch the whole app to ${name}`}</span>
            </button>
          )
        })}
      </div>
    </section>
  )
}
