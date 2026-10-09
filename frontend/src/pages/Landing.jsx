import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { RingHero } from './Network.jsx'
import { Icon, Logo, Meter, RegionSwitch, Tier, money, pct, useCountUp, words } from '../components/bits.jsx'
import { terms } from '../region.js'

// The public front page. Every number on it comes from the live API for the selected region.
export default function Landing({ region, onSwitch }) {
  const [q, setQ] = useState(null)
  const [m, setM] = useState(null)
  useEffect(() => {
    api.queue(90, 3).then(setQ).catch(() => setQ(false))
    api.metrics().then(setM).catch(() => {})
  }, [])
  const t = terms()
  const s = q?.summary
  const open = q ? q.cases.filter((c) => c.status === 'open') : []
  const ring = open.find((c) => c.network)
  const pl = m?.provider_level
  const tr = m?.triage
  const dataset = region === 'in' ? 'PM-JAY-style hospital admissions' : 'CMS-style provider claims'

  return (
    <div className="site">
      <header className="site-nav">
        <a className="brand" href="#/"><Logo /><strong>ClaimShield Nexus</strong></a>
        <nav aria-label="Sections">
          <a href="#how" onClick={jump('how')}>How it works</a>
          <a href="#features" onClick={jump('features')}>Features</a>
          <a href="#results" onClick={jump('results')}>Results</a>
        </nav>
        <RegionSwitch region={region} onSwitch={onSwitch} />
        <a className="btn primary" href="#/queue">Open the app</a>
      </header>

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

      {s && (
        <section className="band" aria-label="This week in numbers">
          <Figure n={s.claims} label="claims analysed" />
          <Figure n={s.raw_alerts} label="alerts raised by rules, the anomaly model and network analysis" />
          <Figure n={s.actionable ?? s.open_cases} label="cases opened with evidence" />
          <Figure n={s.capacity} label={`cases that fit this week with 3 investigators`} />
        </section>
      )}

      <section id="how" className="section">
        <header className="section-head">
          <h2>From thousands of claims to one week of work</h2>
          <p>Three steps, with an investigator in charge of the one that matters.</p>
        </header>
        <ol className="steps-grid">
          <li><span className="step-n">1</span><h3>Detect</h3><p>Billing rules, an anomaly model and network analysis each score every {t.provider}. Cases need agreement before they reach the queue.</p></li>
          <li><span className="step-n">2</span><h3>Decide</h3><p>An investigator reads the brief, checks the evidence and precedents, and confirms, clears or marks the case inconclusive with a reason.</p></li>
          <li><span className="step-n">3</span><h3>Learn</h3><p>The decision is written into the Second Brain as precedent. Similar open cases are re-scored, and the queue shows what moved.</p></li>
        </ol>
      </section>

      <section id="features" className="section">
        <header className="section-head">
          <h2>Everything an investigator needs, on one page</h2>
          <p>Built around the questions a {t.unit} reviewer actually asks about a lead.</p>
        </header>
        <div className="features">
          <Feature icon="rank" title="Ranked by capacity">Priority blends risk, money at stake, {t.member} impact, severity and confidence, and the queue marks how many cases your team can take this week.</Feature>
          <Feature icon="brief" title="Fact-checked briefs">Each case gets a written summary. Every ID, code and amount in it is checked against the claims data before you see it.</Feature>
          <Feature icon="network" title="Fraud ring detection">Shared {t.member === 'member' ? 'members' : 'beneficiaries'}, referral loops and common owners are found as networks, not one {t.provider} at a time.</Feature>
          <Feature icon="check" title="Human decisions">Nothing is confirmed automatically. Investigators preview exactly what changes before they approve a verdict.</Feature>
          <Feature icon="learn" title="A memory that grows">The Second Brain keeps patterns, policies and closed cases as linked pages you can browse or ask questions of.</Feature>
          <Feature icon="export" title="Standard exports">Every case exports as FHIR JSON, ready for case-management and audit systems.</Feature>
        </div>
      </section>

      {ring && (
        <section className="section split">
          <div>
            <h2>Rings show up as loops</h2>
            <p>
              Network {ring.network} is {open.filter((c) => c.network === ring.network).length} {t.providers} under one owner,
              referring the same {t.member === 'member' ? 'members' : 'beneficiaries'} to each other in a closed loop. No single
              {' '}{t.provider} looks extreme on its own, which is why claim-by-claim rules miss it.
            </p>
            <a className="btn" href={`#/case/${ring.case_id}`}>Open the {ring.provider_id} case file</a>
          </div>
          <div className="split-figure"><RingHero c={ring} /></div>
        </section>
      )}

      {pl && (
        <section id="results" className="section">
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
      )}

      <section className="cta-band">
        <h2>See this week's queue</h2>
        <p>Start with the highest-priority case, or open the fraud ring.</p>
        <div className="btn-row">
          <a className="btn primary lg" href="#/queue">Open the case queue</a>
          <a className="btn lg" href="#/brain/index">Browse the Second Brain</a>
        </div>
      </section>

      <footer className="site-foot">
        <span className="brand"><Logo /><strong>ClaimShield Nexus</strong></span>
        <p>All claims, {t.providers} and people shown are synthetic. Not for real claims decisions.</p>
      </footer>
    </div>
  )
}

const jump = (id) => (e) => {
  e.preventDefault()
  document.getElementById(id)?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })
}

function Figure({ n, label }) {
  return <div><strong>{useCountUp(n).toLocaleString('en-US')}</strong><span>{label}</span></div>
}

function Feature({ icon, title, children }) {
  return <div className="feature"><span className="feature-icon"><Icon name={icon} /></span><h3>{title}</h3><p>{children}</p></div>
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
