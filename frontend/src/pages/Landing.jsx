import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client.js'
import { RingHero } from './Network.jsx'
import { Chance, Discrepancy, hasConflict } from './CaseDetail.jsx'
import { Architecture, Funnel, Journey, Regions, Safeguards, Scoring, Security } from './Slides.jsx'
import AuditNext from '../components/AuditNext.jsx'
import ClinicalAuditCard from '../components/ClinicalAuditCard.jsx'
import { SCENE_COUNT } from '../components/ArchMap.jsx'
import { startTour } from '../components/Tour.jsx'
import { Icon, Logo, Meter, RegionSwitch, Tier, money, pct, words } from '../components/bits.jsx'
import { terms } from '../region.js'

const motion = () => (matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth')
const field = (e) => e.target.closest('input, textarea, select, [contenteditable="true"]')
const control = (e) => e.target.closest('button, a, [role="button"]')
const store = { get: (k) => { try { return sessionStorage.getItem(k) } catch { return null } },
  set: (k, v) => { try { v == null ? sessionStorage.removeItem(k) : sessionStorage.setItem(k, v) } catch { /* storage blocked */ } } }
// Presenter notes (N): what to say on each slide and when it should end, for a 6-minute slot. Numbers are on the slides.
const NOTES = {
  top: [20, 'SIUs get thousands of alerts and one week. We rank providers by fraud risk, explain each case with checked facts, and learn from every decision.'],
  funnel: [45, 'Four presses. Land on the last number: what a team of three can actually work this week.'],
  how: [90, 'One real case through all five stages. Every number is live. Pause on Decide: it says what to check first and what it costs.'],
  scoring: [110, 'Why this case is first: block width is how much a factor counts, the fill is how strongly this case scores on it.'],
  architecture: [140, 'Data in, scored offline, served with memory, decided by a person, out to your systems. Linger on the failure and the data boundary.'],
  live: [145, 'Press Enter. About two minutes: queue, capacity line, identity, confidence, the conflict, record review, next checks, the decision, the tamper check.'],
  case: [265, 'Backup for the walkthrough. Skip with the rail if the live demo ran.'],
  record: [265, 'Backup. The record puts the provider in San Antonio while the claim bills Dallas.'],
  next: [265, 'Backup. The top check clears the most doubt for the time it takes.'],
  ring: [285, 'No single provider looks extreme. Together they refer the same people in a loop under one owner.'],
  safeguards: [305, "People decide. Data stays on the payer's servers. Losing one method degrades gracefully, and the app says so."],
  security: [325, 'Signed sessions, a tamper-evident log, prompt-injection screening, a hardened API. All live from this server.'],
  results: [340, 'Measured on fraud we planted ourselves. Say that plainly: it is recovery of injected scenarios, not real-world accuracy.'],
  regions: [352, 'Same engine, two payment systems: the US polices the procedure line, India the hospital admission.'],
  cta: [360, "Close: every lead is explained, every decision is a person's, and every decision makes the next case better. Questions."],
}
const clock = (ms) => { const s = Math.floor(ms / 1000); return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}` }

// The public front page, and the 6-minute presentation (Present). Every number on it comes from the live API for the selected region.
export default function Landing({ region, onSwitch }) {
  const [q, setQ] = useState(null)
  const [m, setM] = useState(null)
  const [c, setC] = useState(null)          // the example case: the top open case with a verified conflict (US) or the top case (India)
  const [record, setRecord] = useState(false) // whether that case has a provider record on file
  const [plan, setPlan] = useState(null)
  const [sec, setSec] = useState(null)
  const [health, setHealth] = useState(null)

  useEffect(() => {
    let live = true
    api.queue(90, 3).then(async (d) => {
      if (!live) return
      setQ(d)
      const open = d.cases.filter((x) => x.status === 'open').slice(0, region === 'in' ? 1 : 5)
      let pick = null
      for (const row of open) {
        const full = await api.getCase(row.case_id, 90).catch(() => null)
        if (!live) return
        if (!full) continue
        pick = pick || full
        if (hasConflict(full)) { pick = full; break }
      }
      if (!pick) return
      // Record and plan arrive before the case is shown, so the slide list changes once, not three times.
      const [r, p] = await Promise.all([api.clinicalAudit(pick.case_id).catch(() => null), api.auditPlan(pick.case_id, 90).catch(() => null)])
      if (!live) return
      setRecord(Boolean(r?.artifact)); setPlan(p); setC(pick)
    }).catch(() => live && setQ(false))
    api.metrics().then((x) => live && setM(x)).catch(() => {})
    api.securityStatus().then((x) => live && setSec(x)).catch(() => {})
    api.health().then((x) => live && setHealth(x)).catch(() => {})
    return () => { live = false }
  }, [])

  // Centre the page the same whether or not a scrollbar shows; undone when leaving the landing page.
  useEffect(() => {
    const h = document.documentElement
    h.classList.add('landing')
    return () => h.classList.remove('landing', 'presenting')
  }, [])

  const t = terms()
  const s = q?.summary
  const rows = q ? q.cases : []
  const open = rows.filter((x) => x.status === 'open')
  const ring = open.find((x) => x.network)
  const row = c && rows.find((x) => x.case_id === c.case_id)
  const pl = m?.provider_level
  const tr = m?.triage
  const dataset = region === 'in' ? 'PM-JAY-style hospital admissions' : 'CMS-style provider claims'
  const members = t.member === 'member' ? 'members' : 'beneficiaries'

  const slides = [
    { id: 'top', title: 'ClaimShield Nexus', body: (
      <section className="hero">
        <div className="hero-copy">
          <h1>Find the {t.providers} worth investigating. Show exactly why.</h1>
          <p className="lede">
            ClaimShield Nexus ranks {t.providers} by fraud risk, writes a fact-checked brief for every case, and learns
            from each decision your investigators record.
          </p>
          <div className="btn-row">
            <a className="btn primary lg" href="#/queue">Open the case queue</a>
            {ring && <a className="btn lg" href={`#/case/${ring.case_id}`}>See a fraud ring case</a>}
          </div>
          <p className="fine"><Icon name="info" />Demo on synthetic {dataset}. It finds leads for human review and never decides fraud on its own.</p>
        </div>
        <Preview q={q} />
      </section>
    ) },
    s && { id: 'funnel', title: 'The funnel', builds: 4, body: (b) => <Funnel s={s} build={b} /> },
    row && { id: 'how', title: 'How it works', builds: 5, body: (b) => <Journey c={c} row={row} total={rows.length} plan={plan} build={b} /> },
    row && { id: 'scoring', title: 'Scoring', builds: 3, body: (b) => <Scoring c={c} row={row} rows={rows} region={region} build={b} /> },
    { id: 'architecture', title: 'Architecture', builds: SCENE_COUNT, body: (b) => <Architecture region={region} build={b} /> },
    c && { id: 'live', title: 'Live walkthrough', body: (
      <section className="section live-slide" aria-labelledby="live-h">
        <header className="section-head">
          <h2 id="live-h">Now the real app</h2>
          <p>A guided walk through the live queue and case <span className="id">{c.case_id}</span>, one part at a time. Everything else dims; the app keeps working.</p>
        </header>
        <div className="btn-row">
          <button type="button" className="btn primary lg" onClick={() => liveDemo(c.case_id)} aria-keyshortcuts="Enter">Start the walkthrough</button>
          <a className="btn lg" href={`#/case/${c.case_id}`}>Open the case without a guide</a>
        </div>
        <p className="fine"><Icon name="info" />Press Enter on this slide to start; the arrow keys then move through it and Esc ends it. It returns here when it ends. The next slides show the same screens as a backup.</p>
      </section>
    ) },
    c && { id: 'case', title: 'What an investigator sees', body: (
      <section className="section">
        <header className="section-head">
          <h2>What an investigator sees</h2>
          <p>The strongest claim on case <span className="id">{c.case_id}</span>, with the gap between the records measured. Red appears only when a claim is logically impossible.</p>
        </header>
        <div className="showcase">
          <Discrepancy c={c} />
          <section className="pod pod-confidence" aria-labelledby="show-conf">
            <p className="pod-label" id="show-conf">Algorithmic confidence</p>
            <div className="conf-main"><strong>{pct(c.brief.confidence.score)}</strong><Tier tier={c.brief.confidence.tier} /></div>
            <Chance label="Needs attention" p={c.brief.confidence.score} plain />
            <Chance label="Repeats within 90 days" p={c.brief.prediction.probability} plain />
            <p className="conf-ctx">From {c.n_claims.toLocaleString('en-US')} claims. <b>{c.signals.families_agreeing} of 3</b> detection methods agree.</p>
            <a className="btn" href={`#/case/${c.case_id}`}>Open the {c.provider_id} case file</a>
          </section>
        </div>
      </section>
    ) },
    c && record && { id: 'record', title: 'Evidence the system reads', body: (
      <section className="section">
        <header className="section-head">
          <h2>Evidence the system reads for you</h2>
          <p>A record returned by the {t.provider} is laid out as one timeline and compared with the flagged claims. It is a lead for review, not a finding.</p>
        </header>
        <div className="narrow"><ClinicalAuditCard caseId={c.case_id} /></div>
      </section>
    ) },
    c && { id: 'next', title: 'What to check next', body: (
      <section className="section duo">
        <div>
          <h2>What to check next</h2>
          <p>Each check an investigator could run is ranked by how much doubt it clears for the time it takes. Accuracy is learned from closed cases in the Second Brain.</p>
          <p className="fine"><Icon name="info" />Costs assume {region === 'in' ? '₹1,200' : '$90'} per investigator hour. Accuracies start from stated assumptions.</p>
        </div>
        <div className="rail"><AuditNext caseId={c.case_id} horizon={90} plain /></div>
      </section>
    ) },
    ring && { id: 'ring', title: 'Rings', body: (
      <section className="section split">
        <div>
          <h2>Rings show up as loops</h2>
          <p>
            Network {ring.network} is {open.filter((x) => x.network === ring.network).length} {t.providers} under one owner,
            referring the same {members} to each other in a closed loop. No single
            {' '}{t.provider} looks extreme on its own, which is why claim-by-claim rules miss it.
          </p>
          <a className="btn" href={`#/case/${ring.case_id}`}>Open the {ring.provider_id} case file</a>
        </div>
        <div className="split-figure"><RingHero c={ring} /></div>
      </section>
    ) },
    { id: 'safeguards', title: 'Safeguards', builds: 3, body: (b) => <Safeguards c={c} health={health} region={region} build={b} /> },
    { id: 'security', title: 'Security', builds: 4, body: (b) => <Security c={c} sec={sec} build={b} /> },
    pl && { id: 'results', title: 'Results', body: (
      <section className="section">
        <header className="section-head">
          <h2>Tested on planted fraud</h2>
          <p>The synthetic data contains {t.providers} with fraud deliberately planted in them. This is how many the system finds.</p>
        </header>
        <div className="results">
          <div><strong>{tr ? tr.actionable.planted : pl.fwa_in_queue} of {pl.fwa_providers}</strong><span>planted fraud {t.providers} reached the queue as cases</span></div>
          <div><strong>{pct(tr ? tr.actionable.precision : pl.queue_precision)}</strong><span>of queued cases were planted fraud</span></div>
          {tr && <div><strong>{pct(tr.at_capacity_3_investigators.precision)}</strong><span>of the first {tr.at_capacity_3_investigators.cases} cases, the ones that fit a week, were planted fraud</span></div>}
          <div><strong>{pl.legit_outliers_in_queue}</strong><span>honest but unusual {pl.legit_outliers_in_queue === 1 ? t.provider : t.providers} in the queue, kept there for a human to clear</span></div>
        </div>
      </section>
    ) },
    { id: 'regions', title: 'One engine, two systems', body: <Regions region={region} onSwitch={onSwitch} /> },
    { id: 'cta', title: 'See the queue', body: (
      <section className="cta-band">
        <h2>See this week's queue</h2>
        <p>Start with the highest-priority case, or open the fraud ring.</p>
        <div className="btn-row">
          <a className="btn primary lg" href="#/queue">Open the case queue</a>
          <a className="btn lg" href="#/brain/index">Browse the Second Brain</a>
        </div>
      </section>
    ) },
  ].filter(Boolean)

  const deck = useDeck(slides, c ? () => liveDemo(c.case_id) : null)

  return (
    <div className="site">
      <header className="site-nav">
        <a className="brand" href="#/" aria-label="ClaimShield Nexus home"><Logo /><strong>ClaimShield Nexus</strong></a>
        <nav aria-label="Sections">
          <a href="#how" onClick={jump('how')}>How it works</a>
          <a href="#architecture" onClick={jump('architecture')}>Architecture</a>
          <a href="#safeguards" onClick={jump('safeguards')}>Safeguards</a>
          <a href="#security" onClick={jump('security')}>Security</a>
          <a href="#results" onClick={jump('results')}>Results</a>
          <a href="#/docs">Docs</a>
        </nav>
        <RegionSwitch region={region} onSwitch={onSwitch} />
        <button type="button" className="btn present-btn" onClick={() => deck.start()} aria-keyshortcuts="P">Present</button>
        <a className="btn primary" href="#/queue">Open the app</a>
      </header>

      {slides.map((x, i) => (
        <div key={x.id} id={x.id} className="slide" data-title={x.title}>{typeof x.body === 'function' ? x.body(deck.buildOf(i)) : x.body}</div>
      ))}

      <footer className="site-foot">
        <span className="brand"><Logo /><strong>ClaimShield Nexus</strong></span>
        <p>All claims, {t.providers} and people shown are synthetic. Not for real claims decisions.</p>
      </footer>

      {deck.on && <DeckChrome slides={slides} deck={deck} />}
    </div>
  )
}

// Present mode: full-height slides with scroll snap, keyboard control, a progress rail, a counter and an elapsed timer.
// Slides with steps (builds) take the arrow first, then move on. The current slide is tracked by one IntersectionObserver;
// the key handler is bound once and reads the latest state from a ref.
function useDeck(slides, onLive) {
  const [on, setOn] = useState(false)
  const [at, setAt] = useState(0)
  const [sub, setSub] = useState(0)  // build step within the current slide
  const [t0, setT0] = useState(0)
  const [notes, setNotes] = useState(false)
  const ids = slides.map((x) => x.id).join(' ')
  const builds = slides.map((x) => x.builds || 1)
  const ref = useRef(null)

  // i: a slide index, or a slide id (stable while slides are still loading); s: the build step to show there.
  const go = (i, s = 0) => {
    const list = ref.current.ids
    const k = Math.max(0, Math.min(list.length - 1, typeof i === 'string' ? list.indexOf(i) : i))
    // A hard cut: the page jumps at once and the new slide's entrance animation (opacity and transform only) is the motion.
    document.getElementById(list[k])?.scrollIntoView({ behavior: 'auto', block: 'start' })
    ref.current.at = k
    setAt(k); setSub(s)
  }
  // Forward runs through a slide's builds first; back from the next slide arrives with that slide complete.
  const next = () => { const d = ref.current; if (d.sub < d.builds[d.at] - 1) setSub(d.sub + 1); else go(d.at + 1) }
  const prev = () => { const d = ref.current; if (d.sub > 0) setSub(d.sub - 1); else if (d.at > 0) go(d.at - 1, d.builds[d.at - 1] - 1) }
  const fullscreen = () => {
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {})
    else document.documentElement.requestFullscreen?.().catch(() => {})
  }
  const stop = () => {
    document.documentElement.classList.remove('presenting')
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {})
    store.set('csn-deck-t0', null)
    setOn(false)
  }
  const start = (i = ref.current.at, since = Date.now()) => {
    document.documentElement.classList.add('presenting')
    document.activeElement?.blur?.()  // the Present button is hidden now; keys go to the deck
    store.set('csn-deck-t0', String(since))
    setOn(true); setT0(since)
    requestAnimationFrame(() => go(i))
  }
  const toggleNotes = () => setNotes((v) => !v)
  ref.current = { at, sub, builds, on, ids: ids.split(' '), go, next, prev, start, stop, fullscreen, onLive, toggleNotes }

  // The slide crossing the middle of the viewport is current; it also gets .on, which runs its entrance animation.
  useEffect(() => {
    if (!('IntersectionObserver' in window)) return
    const list = ids.split(' ')
    const io = new IntersectionObserver((entries) => {
      for (const e of entries) {
        e.target.classList.toggle('on', e.isIntersecting)
        if (e.isIntersecting) {
          const k = list.indexOf(e.target.id)
          if (k !== ref.current.at) { ref.current.at = k; setAt(k); setSub(0) }  // reached by scrolling: its steps start over
        }
      }
    }, { rootMargin: '-50% 0px -50% 0px' })
    list.forEach((id) => { const el = document.getElementById(id); if (el) io.observe(el) })
    return () => io.disconnect()
  }, [ids])

  // Back from the walkthrough: present again from the slide after it, with the clock still running.
  // Waits for the example case's slides (they sit above it), so the target does not move after the jump.
  useEffect(() => {
    const resume = store.get('csn-deck-resume')
    const list = ids.split(' ')
    if (!resume || !list.includes(resume) || !list.includes('how')) return
    store.set('csn-deck-resume', null)
    start(resume, Number(store.get('csn-deck-t0')) || Date.now())
  }, [ids])

  useEffect(() => {
    const NEXT = new Set(['ArrowDown', 'ArrowRight', 'PageDown', ' '])
    const PREV = new Set(['ArrowUp', 'ArrowLeft', 'PageUp'])
    const keys = (e) => {
      if (e.ctrlKey || e.metaKey || e.altKey || document.querySelector('dialog[open], .tour')) return
      const d = ref.current, k = e.key
      if (field(e)) return
      // Enter on the live slide starts the walkthrough, presenting or not (unless a button or link has focus: then Enter is its own).
      if (k === 'Enter' && d.onLive && d.ids[d.at] === 'live' && !control(e)) { e.preventDefault(); return d.onLive() }
      let act = null
      if (!d.on) { if (k === 'p' || k === 'P') act = () => d.start() }
      else if (NEXT.has(k)) act = d.next
      else if (PREV.has(k)) act = d.prev
      else if (k === 'Home') act = () => d.go(0)
      else if (k === 'End') act = () => d.go(d.ids.length - 1)
      else if (k === 'f' || k === 'F') act = d.fullscreen
      else if (k === 'n' || k === 'N') act = d.toggleNotes
      else if (k === 'Escape') act = d.stop
      if (act) { e.preventDefault(); act() }
    }
    document.addEventListener('keydown', keys)
    return () => document.removeEventListener('keydown', keys)
  }, [])

  // Outside Present mode every slide is explorable on its own (null). Presenting: earlier slides complete, the current one at its step.
  const buildOf = (i) => (!on ? null : i < at ? builds[i] - 1 : i === at ? sub : 0)
  return { on, at, sub, builds, t0, notes, go, start, stop, fullscreen, buildOf, toggleNotes }
}

function DeckChrome({ slides, deck }) {
  const id = slides[deck.at]?.id
  const [by, note] = NOTES[id] || []
  return (
    <>
      {deck.notes && note && (
        <aside className="deck-notes" aria-label="Presenter notes">
          <p className="pod-label">Notes <span>end by {clock(by * 1000)}</span></p>
          <p>{note}</p>
        </aside>
      )}
      <nav className="deck-nav" aria-label="Slides">
        {slides.map((x, i) => (
          <button type="button" key={x.id} aria-current={i === deck.at ? 'step' : undefined} aria-label={`Slide ${i + 1}: ${x.title}`} onClick={(e) => { deck.go(i); e.currentTarget.blur() }}>
            <i aria-hidden="true" /><span aria-hidden="true">{x.title}</span>
          </button>
        ))}
      </nav>
      <div className="deck-meta">
        <span aria-live="polite"><b>{deck.at + 1}</b> / {slides.length}{deck.builds[deck.at] > 1 && <small className="deck-build"> · step {deck.sub + 1} of {deck.builds[deck.at]}</small>}</span>
        <Clock since={deck.t0} by={by} />
        <button type="button" className="top-btn" onClick={deck.toggleNotes} aria-pressed={deck.notes} aria-keyshortcuts="N">Notes</button>
        <button type="button" className="top-btn" onClick={deck.fullscreen} aria-keyshortcuts="F">Full screen</button>
        <button type="button" className="top-btn" onClick={deck.stop} aria-keyshortcuts="Escape">Exit</button>
      </div>
    </>
  )
}

// Ticks on its own, so only these few characters re-render each second. Amber once this slide is 10 s past its target.
function Clock({ since, by }) {
  const [, tick] = useState(0)
  useEffect(() => { const id = setInterval(() => tick((n) => n + 1), 1000); return () => clearInterval(id) }, [])
  const ms = Date.now() - since
  const late = by != null && ms > (by + 10) * 1000
  return (
    <span className={late ? 'deck-time late' : 'deck-time'} title={by != null ? 'Elapsed, and when this slide should end (6:00 total)' : 'Elapsed time'}>
      {clock(ms)}{by != null && <> / {clock(by * 1000)}</>}
    </span>
  )
}

// Leave the deck for the guided walkthrough (full screen stays on); the deck's clock keeps running and resumes after it.
function liveDemo(caseId) {
  document.documentElement.classList.remove('presenting')
  if (!store.get('csn-deck-t0')) store.set('csn-deck-t0', String(Date.now()))
  startTour(caseId)
}

const jump = (id) => (e) => {
  e.preventDefault()
  document.getElementById(id)?.scrollIntoView({ behavior: motion() })
}

// The product itself, live: the top of this week's queue.
function Preview({ q }) {
  const t = terms()
  if (q === false) return <div className="preview preview-empty"><p>The live preview needs the API. Open the app once it is running.</p></div>
  if (!q) return <div className="preview"><div className="sk" style={{ height: 320 }} /></div>
  const rows = q.cases.filter((c) => c.status === 'open').slice(0, 5)
  return (
    <figure className="preview" aria-label="Live preview of this week's case queue">
      <div className="preview-head">
        <strong>Case queue</strong>
        <span>{q.summary.capacity} cases fit this week</span>
      </div>
      <ol className="preview-rows">
        {rows.map((c) => (
          <li key={c.case_id}>
            <a href={`#/case/${c.case_id}`}>
              <span className="pr-rank">{c.rank}</span>
              <span className="pr-who"><b>{c.provider_name}</b><small>{c.provider_id}, <span className="cap">{words(c.pattern)}</span></small></span>
              <span className="pr-risk"><Meter value={c.risk_score} />{pct(c.risk_score)}</span>
              <span className="pr-money">{money(c.potential_dollars)}</span>
              <Tier tier={c.tier} />
            </a>
          </li>
        ))}
      </ol>
      <figcaption>Live from the {t.currency === '₹' ? 'India' : 'US'} demo data. Select a row to open its case.</figcaption>
    </figure>
  )
}
