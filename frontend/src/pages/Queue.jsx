import { Fragment, useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { RingHero } from './Network.jsx'
import { Loading, Meter, Status, Tier, TIER_TEXT, money, pct, words } from '../components/bits.jsx'
import { getRegion, terms } from '../region.js'

// The queue remembers each case's route from the last visit, so a verdict that
// re-routes similar cases shows up as a visible change rather than a silent re-rank.
// Case IDs repeat across regions, so each region keeps its own memory.
const seenKey = () => (getRegion() === 'in' ? 'csn-routes-in' : 'csn-routes')
const routeOf = (r) => (r.status === 'open' ? r.tier : r.status)
const ROUTE_TEXT = { ...TIER_TEXT, confirmed: 'Confirmed', cleared: 'Cleared', inconclusive: 'Inconclusive' }

// The demo walks through the referral ring first; fall back to any open network case once it closes.
const DEMO_CASE = { us: 'CASE-P081' }
// Full hero on the first queue view after a page load or a region switch; returning from a case shows the compact strip.
let heroSeen = false
export const showOverviewNext = () => { heroSeen = false }
// Someone who skips the overview keeps it skipped on later visits.
const HERO_KEY = 'csn-hero-hidden'
const heroHidden = () => { try { return localStorage.getItem(HERO_KEY) === '1' } catch { return false } }
const rememberHero = (hidden) => { try { hidden ? localStorage.setItem(HERO_KEY, '1') : localStorage.removeItem(HERO_KEY) } catch { /* ignore */ } }

// Sortable columns; the default is the queue's own priority rank.
const SORTS = { rank: (r) => r.rank, risk: (r) => r.risk_score, repeat: (r) => r.p_horizon, money: (r) => r.potential_dollars,
  members: (r) => r.member_impact, severity: (r) => r.severity, confidence: (r) => r.confidence }
const typing = (el) => el && (/^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName) || el.isContentEditable)

function diffRoutes(cases) {
  let seen = {}
  try { seen = JSON.parse(sessionStorage.getItem(seenKey())) || {} } catch { /* storage blocked: no history */ }
  const moved = {}
  for (const r of cases) if (seen[r.case_id] && seen[r.case_id] !== routeOf(r)) moved[r.case_id] = seen[r.case_id]
  try { sessionStorage.setItem(seenKey(), JSON.stringify(Object.fromEntries(cases.map((r) => [r.case_id, routeOf(r)])))) } catch { /* ignore */ }
  return moved
}

export default function Queue({ horizon, setHorizon, investigators, setInvestigators }) {
  const [data, setData] = useState(null)
  const [moved, setMoved] = useState({})
  const [error, setError] = useState(null)
  const [tier, setTier] = useState('all')
  const [retry, setRetry] = useState(0)
  const [metrics, setMetrics] = useState(null)
  const [fullHero, setFullHero] = useState(!heroSeen && !heroHidden())
  const [q, setQ] = useState('')
  const [sort, setSort] = useState({ key: 'rank', desc: false })
  const [updated, setUpdated] = useState(null)
  const search = useRef(null)
  const t = terms()

  // j / k step through cases, Enter opens one, / jumps to search.
  useEffect(() => {
    const on = (e) => {
      if (e.metaKey || e.ctrlKey || e.altKey || typing(e.target)) return
      if (e.key === '/') { e.preventDefault(); search.current?.focus(); return }
      if (e.key !== 'j' && e.key !== 'k') return
      const links = [...document.querySelectorAll('.queue .row-link')]
      if (!links.length) return
      const i = links.indexOf(document.activeElement)
      const next = links[Math.max(0, Math.min(links.length - 1, i < 0 ? 0 : i + (e.key === 'j' ? 1 : -1)))]
      next.focus()
      next.closest('tr').scrollIntoView({ block: 'nearest' })
    }
    document.addEventListener('keydown', on)
    return () => document.removeEventListener('keydown', on)
  }, [])

  useEffect(() => { heroSeen = true; api.metrics().then(setMetrics).catch(() => {}) }, [])

  useEffect(() => {
    setError(null)
    api.queue(horizon, investigators)
      .then((d) => { setMoved((m) => ({ ...m, ...diffRoutes(d.cases) })); setData(d); setUpdated(new Date()) })
      .catch((e) => setError(e.message))
  }, [horizon, investigators, retry])

  if (!data) return <Loading error={error} what="the queue" onRetry={() => setRetry((n) => n + 1)} />
  const s = data.summary
  const needle = q.trim().toLowerCase()
  const rows = data.cases
    .filter((r) => tier === 'all' || r.tier === tier)
    .filter((r) => !needle || [r.case_id, r.provider_id, r.provider_name, r.city, r.specialty, words(r.pattern), r.network].join(' ').toLowerCase().includes(needle))
  const ranked = sort.key === 'rank' && !sort.desc
  if (!ranked) rows.sort((a, b) => (SORTS[sort.key](a) - SORTS[sort.key](b)) * (sort.desc ? -1 : 1))
  // The capacity line and watch-list divider only mean something in priority order.
  const lastIn = ranked ? Math.max(...rows.map((r, i) => (r.in_capacity ? i : -1))) : -1
  // Regions that report a watch list (India) list it after the actionable cases, behind a divider.
  const watchAt = ranked && s.watch_list != null ? rows.findIndex((r) => r.status === 'open' && r.tier === 'low') : -1
  const sortBy = (key) => setSort((cur) => (cur.key === key ? { key, desc: !cur.desc } : { key, desc: key !== 'rank' }))
  const th = (k, label, className) => (
    <th className={className} aria-sort={sort.key === k ? (sort.desc ? 'descending' : 'ascending') : undefined}>
      <button type="button" className={`th-sort${sort.key === k ? ' on' : ''}`} onClick={() => sortBy(k)}>
        {label}<i aria-hidden="true">{sort.key === k ? (sort.desc ? '↓' : '↑') : '↕'}</i>
      </button>
    </th>
  )
  const open = data.cases.filter((r) => r.status === 'open')
  const demo = open.find((r) => r.case_id === DEMO_CASE[getRegion()]) || open.find((r) => r.network) || open[0]
  const pickTier = (t) => {
    setTier((cur) => (cur === t ? 'all' : t))
    document.getElementById('queue-table')?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
  }
  const movedIds = Object.keys(moved)
  const funnel = <Funnel s={s} tier={tier} onPick={pickTier} metrics={metrics} strip={!!demo?.network} />

  return (
    <>
      {fullHero ? (
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <h1 id="hero-title">
              {s.claims.toLocaleString('en-US')} claims, narrowed to the {s.actionable ?? s.open_cases} worth an investigator’s time.
            </h1>
            <p>
              ClaimShield ranks {t.providers} by fraud risk, writes a fact-checked brief for each case, and gets
              sharper with every verdict your team records. It finds leads for human review; it never decides fraud.
            </p>
            <ol className="loop" aria-label="How it works">
              <li><b>Detect</b>Rules, an anomaly model and network analysis flag {t.providers}.</li>
              <li><b>Decide</b>An investigator confirms or clears the case, with a reason.</li>
              <li><b>Learn</b>The verdict becomes precedent and re-routes similar cases.</li>
            </ol>
            <div className="hero-cta">
              {demo && (
                <a className="btn primary lg" href={`#/case/${demo.case_id}`}>
                  {demo.network ? `Walk through the ring case, ${demo.provider_id}` : `Open case ${demo.provider_id}`}
                </a>
              )}
              <a className="btn lg" href="#/brain/index">Browse the Second Brain</a>
            </div>
            <button type="button" className="linklike hero-skip" onClick={() => { rememberHero(true); setFullHero(false) }}>
              Skip this overview next time
            </button>
          </div>
          {demo?.network ? <RingHero c={demo} /> : funnel}
        </section>
      ) : null}
      {fullHero && demo?.network && funnel}
      {!fullHero && (
        <section className="hero-mini" aria-label="Queue overview">
          <p>
            <b>{s.claims.toLocaleString('en-US')}</b> claims, <b>{s.raw_alerts.toLocaleString('en-US')}</b> alerts,{' '}
            <b>{s.open_cases}</b> open cases
          </p>
          <div className="f-tiers" role="group" aria-label="Filter the queue by route">
            {[['high', s.fast_track], ['medium', s.review], ['low', s.not_enough_evidence]].map(([k, n]) => (
              <button type="button" key={k} className={tier === k ? 'on' : ''} aria-pressed={tier === k} onClick={() => pickTier(k)}>
                <i className={`key seg-${k}`} /><b>{n}</b> {TIER_TEXT[k].toLowerCase()}
              </button>
            ))}
          </div>
          <button type="button" className="linklike" onClick={() => { rememberHero(false); setFullHero(true) }}>Show overview</button>
        </section>
      )}

      {movedIds.length > 0 && (
        <p className="moved-note" role="status">
          <strong>{movedIds.length} {movedIds.length === 1 ? 'case' : 'cases'} changed route</strong> since you last looked,
          because a recorded verdict became precedent. They are marked below.
        </p>
      )}

      <section className="controls" aria-label="Queue settings">
        <div className="control">
          <span id="horizon-label">Risk horizon</span>
          <span className="seg" role="group" aria-labelledby="horizon-label">
            {[30, 60, 90].map((h) => (
              <button type="button" key={h} className={h === horizon ? 'on' : ''} aria-pressed={h === horizon}
                onClick={() => setHorizon(h)}>{h} days</button>
            ))}
          </span>
        </div>
        <label className="control">
          Investigators this week
          <span className="stepper">
            <button type="button" aria-label="Fewer investigators" onClick={() => setInvestigators(Math.max(0, investigators - 1))}>−</button>
            <input type="number" min="0" max="50" value={investigators}
              onChange={(e) => setInvestigators(Math.max(0, Math.min(50, Number(e.target.value) || 0)))} />
            <button type="button" aria-label="More investigators" onClick={() => setInvestigators(Math.min(50, investigators + 1))}>+</button>
          </span>
        </label>
        <label className="control search">
          Find a case
          <span className="search-box">
            <input ref={search} type="search" value={q} onChange={(e) => setQ(e.target.value)}
              placeholder={`${t.Provider}, ID, city or pattern`} aria-keyshortcuts="/" />
            <kbd aria-hidden="true">/</kbd>
          </span>
        </label>
        {tier !== 'all' && (
          <p className="chip">Route: {TIER_TEXT[tier]}
            <button type="button" aria-label="Clear route filter" onClick={() => setTier('all')}>×</button>
          </p>
        )}
        <p className="capacity">
          This week covers <strong>{s.capacity} cases</strong> and <strong>{money(s.dollars_in_capacity)}</strong> of potential exposure
          <small>{s.cases_per_investigator} cases per investigator</small>
        </p>
      </section>

      <div className="table-wrap queue-wrap" id="queue-table">
        <table className="queue">
          <thead>
            <tr>
              {th('rank', '#', 'num')}<th>{t.Provider}</th><th>Pattern</th>{th('risk', 'Risk')}{th('repeat', `${horizon}-day repeat`)}
              {th('money', `Potential ${t.currency}`, 'num')}{th('members', t.Members, 'num opt')}{th('severity', 'Severity', 'opt')}
              {th('confidence', 'Confidence')}<th>Route</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <Fragment key={r.case_id}>
                {i === watchAt && (
                  <tr className="cutoff watch-line">
                    <td colSpan="10">
                      <span>Watch list</span> {s.watch_list} {terms().providers} with weak evidence: monitored and re-scored each month, not opened as cases
                    </td>
                  </tr>
                )}
                <tr className={[r.in_capacity ? '' : 'out', moved[r.case_id] ? 'moved' : ''].join(' ')}
                  onClick={() => (window.location.hash = `#/case/${r.case_id}`)}>
                  <td className="num rank">{r.rank}</td>
                  <td className="provider">
                    <a className="row-link" href={`#/case/${r.case_id}`} onClick={(e) => e.stopPropagation()}>
                      <strong>{r.provider_id}</strong> {r.provider_name}
                    </a>
                    <small>{r.specialty}, {r.city}{r.network ? <span className="net">network {r.network}</span> : ''}</small>
                  </td>
                  <td className="cap">{words(r.pattern)}</td>
                  <td data-label="Risk"><Meter value={r.risk_score} /> {pct(r.risk_score)}</td>
                  <td data-label={`${horizon}-day repeat`}>{pct(r.p_horizon)}</td>
                  <td className="num" data-label="Potential">{money(r.potential_dollars)}</td>
                  <td className="num opt">{r.member_impact}</td>
                  <td className="opt"><Meter value={r.severity} tone="muted" /></td>
                  <td data-label="Confidence">{pct(r.confidence)}</td>
                  <td className="route-cell">
                    {r.status === 'open' ? <Tier tier={r.tier} /> : <Status status={r.status} />}
                    {moved[r.case_id] && <small className="was">was {ROUTE_TEXT[moved[r.case_id]]}</small>}
                  </td>
                </tr>
                {i === lastIn && i < rows.length - 1 && (
                  <tr className="cutoff">
                    <td colSpan="10">
                      <span>Capacity line</span> {investigators} {investigators === 1 ? 'investigator' : 'investigators'} can take the cases above this week
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {rows.length === 0 && (
              <tr className="empty-row"><td colSpan="10" className="empty">
                {needle
                  ? <>No cases match “{q.trim()}”. <button type="button" className="linklike" onClick={() => setQ('')}>Clear search</button></>
                  : <>No open cases are routed here right now. <button type="button" className="linklike" onClick={() => setTier('all')}>Show all routes</button></>}
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
      <p className="foot">
        Ranking blends risk, potential {t.currency === '₹' ? 'rupees' : 'dollars'}, {t.member} impact, severity and confidence.
        Select a row to open its brief, or use <kbd>j</kbd> <kbd>k</kbd> and <kbd>Enter</kbd>.
        {!ranked && <> Sorted by a column, so the capacity line is hidden. <button type="button" className="linklike" onClick={() => setSort({ key: 'rank', desc: false })}>Back to priority order</button></>}
        {updated && <span className="updated">Updated {updated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
      </p>
    </>
  )
}

// Bar widths use a log scale so 80,452 claims and 34 cases fit on one chart;
// the numbers carry the exact values.
function Funnel({ s, tier, onPick, metrics, strip }) {
  const max = Math.log10(s.claims)
  const w = (n) => `${Math.max(8, (Math.log10(Math.max(n, 1)) / max) * 100)}%`
  const tiers = [
    ['high', s.fast_track, 'fast-track'],
    ['medium', s.review, 'review'],
    ['low', s.not_enough_evidence, 'not enough evidence'],
  ]
  const open = Math.max(1, s.fast_track + s.review + s.not_enough_evidence)
  const pl = metrics?.provider_level
  const tr = metrics?.triage
  return (
    <figure className={strip ? 'funnel strip' : 'funnel'} aria-label="How claims narrow into cases">
      <div className="f-rows">
      <div className="f-row">
        <span className="f-bar" style={{ '--w': w(s.claims) }} />
        <strong>{s.claims.toLocaleString('en-US')}</strong><span>claims analysed</span>
      </div>
      <div className="f-row">
        <span className="f-bar" style={{ '--w': w(s.raw_alerts) }} />
        <strong>{s.raw_alerts.toLocaleString('en-US')}</strong><span>raw alerts from rules, anomaly model and network</span>
      </div>
      <div className="f-row f-cases">
        <span className="f-bar" style={{ '--w': w(s.actionable ?? s.open_cases) }} />
        <strong>{s.actionable ?? s.open_cases}</strong>
        <span>{s.watch_list != null ? `cases for investigators, plus ${s.watch_list} on the watch list` : 'open cases with evidence'}</span>
      </div>
      <div className="f-row f-split">
        <span className="f-bar" style={{ '--w': w(s.open_cases) }}>
          {tiers.map(([t, n]) => <i key={t} className={`seg-${t}`} style={{ flexGrow: n / open }} />)}
        </span>
        <div className="f-tiers" role="group" aria-label="Filter the queue by route">
          {tiers.map(([t, n, label]) => (
            <button type="button" key={t} className={tier === t ? 'on' : ''} aria-pressed={tier === t} onClick={() => onPick(t)}>
              <i className={`key seg-${t}`} /><b>{n}</b> {label}
            </button>
          ))}
        </div>
      </div>
      </div>
      {tr ? (
        <figcaption className="f-proof">
          On injected test scenarios, <b>{tr.actionable.planted} of {pl.fwa_providers}</b> planted fraud {terms().providers} are actionable
          cases and {tr.watch_list.planted} {tr.watch_list.planted === 1 ? 'is' : 'are'} on the watch list. {pct(tr.actionable.precision)} of actionable cases
          and {pct(tr.at_capacity_3_investigators.precision)} of the first {tr.at_capacity_3_investigators.cases} were planted ones. Synthetic data, not real claims.
        </figcaption>
      ) : pl && (
        <figcaption className="f-proof">
          On injected test scenarios, <b>{pl.fwa_in_queue} of {pl.fwa_providers}</b> planted fraud {terms().providers} made the queue,
          and {pct(pl.queue_precision)} of queued {terms().providers} were planted ones. Synthetic data, not real claims.
        </figcaption>
      )}
    </figure>
  )
}
