import { useEffect, useState } from 'react'
import Queue, { showOverviewNext } from './pages/Queue.jsx'
import CaseDetail from './pages/CaseDetail.jsx'
import Wiki from './pages/Wiki.jsx'
import { getRegion, setRegion } from './region.js'
import { AccountChip } from './components/SignIn.jsx'
import { Toaster } from './components/bits.jsx'

const REGIONS = [['us', 'US'], ['in', 'India']]

// index.html sets data-theme before first paint (saved choice, else the system setting).
function ThemeToggle() {
  const [theme, setTheme] = useState(document.documentElement.dataset.theme || 'light')
  const flip = () => {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.dataset.theme = next
    try { localStorage.setItem('csn-theme', next) } catch { /* storage blocked: applies to this visit */ }
    setTheme(next)
  }
  return (
    <button type="button" className="top-btn icon" onClick={flip} aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'} title="Toggle theme">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        {theme === 'dark'
          ? <><circle cx="12" cy="12" r="4.5" /><path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8" /></>
          : <path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5Z" />}
      </svg>
    </button>
  )
}

function useHash() {
  const [hash, setHash] = useState(window.location.hash || '#/')
  useEffect(() => {
    const on = () => setHash(window.location.hash || '#/')
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return hash
}

export default function App() {
  const hash = useHash()
  const [, section, arg] = hash.split('/')
  const [horizon, setHorizon] = useState(90)
  const [investigators, setInvestigators] = useState(3)
  const [region, setRegionState] = useState(getRegion())

  // Case IDs and wiki pages belong to one region, so every switch opens the new region's full queue overview at the top.
  const switchRegion = (r) => {
    if (r === region) return
    setRegion(r)
    showOverviewNext()
    setRegionState(r)
    if (section === 'case' || section === 'brain') window.location.hash = '#/'
    window.scrollTo(0, 0)
  }

  useEffect(() => {
    window.scrollTo(0, 0)
    document.title = (section === 'case' && arg ? `${arg} · ` : section === 'brain' ? 'Second Brain · ' : 'Queue · ') + 'ClaimShield Nexus'
  }, [section, arg])

  let page
  if (section === 'case' && arg) page = <CaseDetail caseId={arg} horizon={horizon} />
  else if (section === 'brain') page = <Wiki name={arg || 'index'} />
  else page = <Queue horizon={horizon} setHorizon={setHorizon} investigators={investigators} setInvestigators={setInvestigators} />

  return (
    <div className="shell">
      <a className="skip" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById('main').focus() }}>Skip to content</a>
      <header className="top">
        <a className="brand" href="#/">
          <svg className="mark" viewBox="0 0 32 32" aria-hidden="true">
            <path d="M16 3 5 7v8c0 7 4.6 12 11 14 6.4-2 11-7 11-14V7L16 3Z" />
            <path className="mark-hl" d="M10 17h12" />
          </svg>
          <span>
            <strong>ClaimShield Nexus</strong>
            <small>{region === 'in' ? 'PM-JAY anti-fraud second brain' : "The SIU's second brain"}</small>
          </span>
        </a>
        <nav aria-label="Main">
          <a className={section !== 'brain' ? 'on' : ''} aria-current={section !== 'brain' ? 'page' : undefined} href="#/">Queue</a>
          <a className={section === 'brain' ? 'on' : ''} aria-current={section === 'brain' ? 'page' : undefined} href="#/brain/index">Second Brain</a>
        </nav>
        <div className="top-tools">
          <span className="synthetic" title="All claims, providers and people are synthetic"><span>Synthetic data</span></span>
          <div className="region" role="group" aria-label="Region">
            {REGIONS.map(([r, label]) => (
              <button type="button" key={r} className={r === region ? 'on' : ''} aria-pressed={r === region} onClick={() => switchRegion(r)}>{label}</button>
            ))}
          </div>
          <ThemeToggle />
          <AccountChip />
        </div>
      </header>
      <main id="main" tabIndex="-1" key={region}>{page}</main>
      <Toaster />
    </div>
  )
}
