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

  let page
  if (section === 'case' && arg) page = <CaseDetail caseId={arg} horizon={horizon} />
  else if (section === 'brain') page = <Wiki name={arg || 'index'} />
  else page = <Queue horizon={horizon} setHorizon={setHorizon} investigators={investigators} setInvestigators={setInvestigators} />

  return (
    <div className="shell">
      <header className="top">
        <a className="brand" href="#/">
          <span className="mark">CN</span>
          <span>
            <strong>ClaimShield Nexus</strong>
            <small>The SIU's Second Brain</small>
          </span>
        </a>
        <nav>
          <a className={section !== 'brain' ? 'on' : ''} href="#/">SIU queue</a>
          <a className={section === 'brain' ? 'on' : ''} href="#/brain/index">Second Brain</a>
        </nav>
        <span className="synthetic">Synthetic data only</span>
      </header>
      <main>{page}</main>
    </div>
  )
}
