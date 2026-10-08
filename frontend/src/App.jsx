import { useEffect, useState } from 'react'
import Queue from './pages/Queue.jsx'
import CaseDetail from './pages/CaseDetail.jsx'
import Wiki from './pages/Wiki.jsx'

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
            <small>The SIU's second brain</small>
          </span>
        </a>
        <nav aria-label="Main">
          <a className={section !== 'brain' ? 'on' : ''} aria-current={section !== 'brain' ? 'page' : undefined} href="#/">Queue</a>
          <a className={section === 'brain' ? 'on' : ''} aria-current={section === 'brain' ? 'page' : undefined} href="#/brain/index">Second Brain</a>
        </nav>
        <span className="synthetic">Synthetic data only</span>
      </header>
      <main id="main" tabIndex="-1">{page}</main>
    </div>
  )
}
