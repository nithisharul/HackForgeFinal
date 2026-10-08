import { useEffect, useState } from 'react'
import Queue from './pages/Queue.jsx'
import CaseDetail from './pages/CaseDetail.jsx'
import Wiki from './pages/Wiki.jsx'
import { getRegion, setRegion } from './region.js'

const REGIONS = [['us', 'US'], ['in', 'India']]

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

  // Case IDs and wiki pages belong to one region, so a switch returns to that region's queue or index.
  const switchRegion = (r) => {
    if (r === region) return
    setRegion(r)
    setRegionState(r)
    if (section === 'case') window.location.hash = '#/'
    else if (section === 'brain') window.location.hash = '#/brain/index'
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
        <div className="region" role="group" aria-label="Region">
          {REGIONS.map(([r, label]) => (
            <button type="button" key={r} className={r === region ? 'on' : ''} aria-pressed={r === region} onClick={() => switchRegion(r)}>{label}</button>
          ))}
        </div>
        <span className="synthetic">Synthetic data only</span>
      </header>
      <main id="main" tabIndex="-1" key={region}>{page}</main>
    </div>
  )
}
