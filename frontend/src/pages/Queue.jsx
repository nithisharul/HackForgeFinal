import { Fragment, useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { Doubt, Icon, Loading, Meter, Status, Tier, TIER_TEXT, money, pct, useCountUp, words } from '../components/bits.jsx'
import { getRegion, terms } from '../region.js'

// The queue remembers each case's route from the last visit, so a verdict that
// re-routes similar cases shows up as a visible change rather than a silent re-rank.
// Case IDs repeat across regions, so each region keeps its own memory.
const seenKey = () => (getRegion() === 'in' ? 'csn-routes-in' : 'csn-routes')
const routeOf = (r) => (r.status === 'open' ? r.tier : r.status)
const ROUTE_TEXT = { ...TIER_TEXT, confirmed: 'Confirmed', cleared: 'Cleared', inconclusive: 'Inconclusive' }

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
  // Tab, search and sort live in the URL, so a filtered view can be bookmarked or sent to a colleague.
  const [init] = useState(() => new URLSearchParams(window.location.hash.split('?')[1] || ''))
  const [tier, setTier] = useState(() => init.get('route') || 'all')
  const [retry, setRetry] = useState(0)
  const [metrics, setMetrics] = useState(null)
  const [q, setQ] = useState(() => init.get('q') || '')
  const [sort, setSort] = useState(() => (SORTS[init.get('sort')] ? { key: init.get('sort'), desc: init.get('dir') !== 'asc' } : { key: 'rank', desc: false }))
  const [updated, setUpdated] = useState(null)
  useEffect(() => {
    const p = new URLSearchParams()
    if (tier !== 'all') p.set('route', tier)
    if (q.trim()) p.set('q', q.trim())
    if (sort.key !== 'rank') { p.set('sort', sort.key); p.set('dir', sort.desc ? 'desc' : 'asc') }
    const next = `#/queue${p.size ? `?${p}` : ''}`
    if (window.location.hash.startsWith('#/queue') && window.location.hash !== next) history.replaceState(null, '', next)
  }, [tier, q, sort])
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

  useEffect(() => { api.metrics().then(setMetrics).catch(() => {}) }, [])

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
  const maxMoney = Math.max(...data.cases.map((r) => r.potential_dollars))
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
  const top = data.cases.find((r) => r.status === 'open')
  const movedIds = Object.keys(moved)
  const pl = metrics?.provider_level
  const tr = metrics?.triage
  const tabs = [['all', 'All cases', data.cases.length], ['high', 'Fast-track', s.fast_track], ['medium', 'Review', s.review], ['low', 'Not enough evidence', s.not_enough_evidence]]

  return (
    <>
      <header className="page-head">
        <div>
          <h1>Case queue</h1>
          <p>{t.Providers} ranked by priority for the {t.unit}. Select a row to open its case.</p>
        </div>
        <div className="page-actions">
          <a className="btn" href="#/brain/index">Second Brain</a>
          {top && <a className="btn primary" href={`#/case/${top.case_id}`}>Open top case</a>}
        </div>
      </header>

      <section className="kpis" aria-label="This week in numbers">
        <Kpi label="Claims analysed" n={s.claims} />
        <Kpi label="Alerts raised" n={s.raw_alerts} note="Rules, anomaly model and network analysis" />
        <Kpi label="Cases opened" n={s.actionable ?? s.open_cases} note={s.watch_list != null ? `Plus ${s.watch_list} on the watch list` : 'Each with supporting evidence'} />
        <Kpi label="Fit this week" n={s.capacity} accent
          note={`${investigators} ${investigators === 1 ? 'investigator' : 'investigators'}, ${money(s.dollars_in_capacity)} exposure`} />
      </section>

      {pl && (
        <p className="callout">
          <Icon name="check" />
          <span>
            Tested on planted fraud: <b>{tr ? tr.actionable.planted : pl.fwa_in_queue} of {pl.fwa_providers}</b> planted {t.providers} became cases,
            and {pct(tr ? tr.actionable.precision : pl.queue_precision)} of queued cases were planted ones. All data is synthetic.
          </span>
        </p>
      )}

      {movedIds.length > 0 && (
        <p className="callout warn" role="status">
          <Icon name="learn" />
          <span><b>{movedIds.length} {movedIds.length === 1 ? 'case' : 'cases'} changed route</b> since you last looked, because a recorded decision became precedent. They are highlighted below.</span>
        </p>
      )}

      <section className="panel" aria-label="Queue">
        <div className="toolbar">
          <div className="tabs" role="group" aria-label="Filter by route">
            {tabs.map(([k, label, n]) => (
              <button type="button" key={k} className={tier === k ? 'on' : ''} aria-pressed={tier === k} onClick={() => setTier(k)}>
                {k !== 'all' && <i className={`dot-${k}`} aria-hidden="true" />}{label}<span className="count-pill">{n}</span>
              </button>
            ))}
          </div>
          <div className="tools">
            <label className="search-box">
              <Icon name="search" />
              <input ref={search} type="search" value={q} onChange={(e) => setQ(e.target.value)}
                placeholder={`Search ${t.providers}`} aria-label={`Search ${t.providers}, IDs, cities or patterns`} aria-keyshortcuts="/" />
              <kbd aria-hidden="true">/</kbd>
            </label>
            <div className="control-inline">
              <span id="horizon-label">Horizon</span>
              <span className="seg" role="group" aria-labelledby="horizon-label">
                {[30, 60, 90].map((h) => (
                  <button type="button" key={h} className={h === horizon ? 'on' : ''} aria-pressed={h === horizon} onClick={() => setHorizon(h)}>{h}d</button>
                ))}
              </span>
            </div>
            <label className="control-inline">
              <span>Investigators</span>
              <span className="stepper">
                <button type="button" aria-label="Fewer investigators" onClick={() => setInvestigators(Math.max(0, investigators - 1))}>−</button>
                <input type="number" min="0" max="50" value={investigators}
                  onChange={(e) => setInvestigators(Math.max(0, Math.min(50, Number(e.target.value) || 0)))} />
                <button type="button" aria-label="More investigators" onClick={() => setInvestigators(Math.min(50, investigators + 1))}>+</button>
              </span>
            </label>
          </div>
        </div>

        <div className="table-wrap queue-wrap" id="queue-table">
          <table className="queue">
            <thead>
              <tr>
                {th('rank', '#', 'num')}<th>{t.Provider}</th><th>Pattern</th>{th('risk', 'Risk')}<th>Methods</th>{th('repeat', `Repeat ${horizon}d`)}
                {th('money', 'Exposure', 'num')}{th('members', t.Members, 'num opt')}{th('severity', 'Severity', 'opt')}
                {th('confidence', 'Confidence')}<th>Route</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <Fragment key={r.case_id}>
                  {i === watchAt && (
                    <tr className="divider watch-line">
                      <td colSpan="11"><b>Watch list</b> {s.watch_list} {t.providers} with weak evidence. Monitored and re-scored each month, not opened as cases.</td>
                    </tr>
                  )}
                  <tr className={[r.in_capacity ? '' : 'out', moved[r.case_id] ? 'moved' : ''].join(' ')}
                    onClick={() => (window.location.hash = `#/case/${r.case_id}`)}>
                    <td className="num rank">{r.rank}</td>
                    <td className="provider">
                      <a className="row-link" href={`#/case/${r.case_id}`} onClick={(e) => e.stopPropagation()}>{r.provider_name}</a>
                      <small>{r.network && <span className="net">Network {r.network}</span>}<span className="id">{r.provider_id}</span>, {r.specialty}, {r.city}</small>
                    </td>
                    <td className="cap">{words(r.pattern)}</td>
                    <td data-label="Risk"><Meter value={r.risk_score} /> {pct(r.risk_score)}</td>
                    <td data-label="Methods"><Methods on={r.methods || []} /></td>
                    <td data-label={`Repeat ${horizon}d`}>{pct(r.p_horizon)}</td>
                    <td className="num" data-label="Exposure">{money(r.potential_dollars)}<Scale value={r.potential_dollars} max={maxMoney} /></td>
                    <td className="num opt">{r.member_impact}</td>
                    <td className="opt"><Meter value={r.severity} tone="muted" /></td>
                    <td data-label="Confidence">{pct(r.confidence)}<Doubt p={r.confidence} short /></td>
                    <td className="route-cell">
                      {r.status === 'open' ? <Tier tier={r.tier} /> : <Status status={r.status} />}
                      {moved[r.case_id] && <small className="was">was {ROUTE_TEXT[moved[r.case_id]]}</small>}
                    </td>
                  </tr>
                  {i === lastIn && i < rows.length - 1 && (
                    <tr className="divider capacity-line">
                      <td colSpan="11"><b>Capacity line</b> {investigators} {investigators === 1 ? 'investigator' : 'investigators'} can take the cases above this week.</td>
                    </tr>
                  )}
                </Fragment>
              ))}
              {rows.length === 0 && (
                <tr className="empty-row"><td colSpan="11" className="empty">
                  {needle
                    ? <>No cases match “{q.trim()}”. <button type="button" className="linklike" onClick={() => setQ('')}>Clear search</button></>
                    : <>No cases are on this route right now. <button type="button" className="linklike" onClick={() => setTier('all')}>Show all cases</button></>}
                </td></tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
      <p className="foot">
        <span>
          Priority blends risk, potential {t.currency === '₹' ? 'rupees' : 'dollars'}, {t.member} impact, severity and confidence.
          Keyboard: <kbd>j</kbd> <kbd>k</kbd> to move, <kbd>Enter</kbd> to open.
          {!ranked && <> Sorted by a column, so the capacity line is hidden. <button type="button" className="linklike" onClick={() => setSort({ key: 'rank', desc: false })}>Back to priority order</button></>}
        </span>
        {updated && <span className="updated">Updated {updated.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>}
      </p>
    </>
  )
}

function Kpi({ label, n, note, accent }) {
  return (
    <div className={accent ? 'kpi accent' : 'kpi'}>
      <span className="kpi-label">{label}</span>
      <strong>{useCountUp(n).toLocaleString('en-US')}</strong>
      {note && <span className="kpi-note">{note}</span>}
    </div>
  )
}

// Which of the three detection methods agree on this provider. Agreement is what separates signal from noise.
const METHODS = [['rules', 'R', 'Rules'], ['ml', 'M', 'Anomaly model'], ['graph', 'N', 'Network analysis']]
function Methods({ on }) {
  const label = on.length ? METHODS.filter(([k]) => on.includes(k)).map((m) => m[2]).join(' and ') : 'None'
  return (
    <span className="methods" role="img" title={`Agreeing: ${label}`} aria-label={`${on.length} of 3 methods agree: ${label}`}>
      {METHODS.map(([k, ch]) => <i key={k} className={on.includes(k) ? 'on' : undefined} aria-hidden="true">{ch}</i>)}
    </span>
  )
}

// Money on a log scale against the largest exposure in the queue, the same scale the priority score uses.
function Scale({ value, max }) {
  const w = max > 0 ? Math.log1p(value) / Math.log1p(max) : 0
  return <span className="scale" title="Against the largest exposure in the queue (log scale)" aria-hidden="true"><i style={{ width: `${Math.max(2, w * 100)}%` }} /></span>
}
