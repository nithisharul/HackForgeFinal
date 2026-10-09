import { Component, useEffect, useState } from 'react'
import Landing from './pages/Landing.jsx'
import Queue from './pages/Queue.jsx'
import CaseDetail from './pages/CaseDetail.jsx'
import Wiki from './pages/Wiki.jsx'
import Admin from './pages/Admin.jsx'
import { getRegion, setRegion, terms } from './region.js'
import { AccountChip } from './components/SignIn.jsx'
import Palette, { MOD } from './components/Palette.jsx'
import { Icon, Logo, RegionSwitch, Toaster } from './components/bits.jsx'
import { api } from './api/client.js'
function useHash() {
  const [hash, setHash] = useState(window.location.hash || '#/')
  useEffect(() => {
    const on = () => setHash(window.location.hash || '#/')
    window.addEventListener('hashchange', on)
    return () => window.removeEventListener('hashchange', on)
  }, [])
  return [hash, setHash]
}

export default function App() {
  const [hash, setHash] = useHash()
  const [, section, arg] = hash.split('?')[0].split('/')
  const [horizon, setHorizon] = useState(90)
  const [investigators, setInvestigators] = useState(3)
  const [region, setRegionState] = useState(getRegion())

  // Case IDs and wiki pages belong to one region, so a switch from inside one opens the new region's queue.
  const switchRegion = (r) => {
    if (r === region) return
    setRegion(r)
    setRegionState(r)
    // Route state changes in the same render as the region, so the old case never loads under the new region.
    if (section === 'case' || section === 'brain') { window.location.hash = '#/queue'; setHash('#/queue') }
    window.scrollTo(0, 0)
  }
  const [health, setHealth] = useState(null)

  // The app keeps working when a detector, the LLM or a page check is down; this says what it is working without.
  useEffect(() => { api.health().then(setHealth).catch(() => setHealth(null)) }, [section, arg, region])

  useEffect(() => {
    window.scrollTo(0, 0)
    const page = section === 'case' && arg ? arg : section === 'brain' ? 'Second Brain' : section === 'queue' ? 'Case queue' : section === 'security' ? 'Security and access' : null
    document.title = page ? `${page} – ClaimShield Nexus` : 'ClaimShield Nexus – fraud leads, ranked and explained'
  }, [section, arg])

  if (!section) return <><Landing key={region} region={region} onSwitch={switchRegion} /><Toaster /><Palette /></>

  let page
  if (section === 'case' && arg) page = <CaseDetail caseId={arg} horizon={horizon} />
  else if (section === 'brain') page = <Wiki name={arg || 'index'} />
  else if (section === 'security') page = <Admin />
  else page = <Queue horizon={horizon} setHorizon={setHorizon} investigators={investigators} setInvestigators={setInvestigators} />
  const t = terms()

  return (
    <div className="app">
      <a className="skip" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById('main').focus() }}>Skip to content</a>
      <aside className="sidebar">
        <a className="brand" href="#/"><Logo /><span><strong>ClaimShield</strong><small>{region === 'in' ? 'PM-JAY anti-fraud' : 'SIU workspace'}</small></span></a>
        <button type="button" className="goto" onClick={() => window.dispatchEvent(new Event('csn-palette'))} aria-keyshortcuts="Control+K Meta+K">
          <Icon name="search" /><span>Search</span><kbd>{MOD} K</kbd>
        </button>
        <nav aria-label="Main">
          <a className={section === 'queue' || section === 'case' ? 'on' : ''} aria-current={section === 'queue' ? 'page' : undefined} href="#/queue"><Icon name="queue" />Case queue</a>
          <a className={section === 'brain' ? 'on' : ''} aria-current={section === 'brain' ? 'page' : undefined} href="#/brain/index"><Icon name="brain" />Second Brain</a>
          <a className={section === 'security' ? 'on' : ''} aria-current={section === 'security' ? 'page' : undefined} href="#/security"><Icon name="shield" />Security and access</a>
          <a href="#/"><Icon name="home" />About ClaimShield</a>
        </nav>
        <div className="side-foot">
          <p className="side-label">Region</p>
          <RegionSwitch region={region} onSwitch={switchRegion} />
          <p className="synthetic"><Icon name="info" />Synthetic {t.currency === '₹' ? 'PM-JAY' : 'CMS-style'} data only</p>
          <AccountChip />
        </div>
      </aside>
      <main id="main" tabIndex="-1" key={region}>
        {health && health.notes.length > 0 && (
          <div className="degraded" role="status">
            <strong>Running in degraded mode.</strong> {health.notes.join(' ')} <a href="#/security">See system health</a>
          </div>
        )}
        <Boundary key={hash}>{page}</Boundary>
      </main>
      <Toaster />
      <Palette />
    </div>
  )
}

// One failing page shows a recoverable message instead of a blank app. Resets on navigation (keyed by the route).
class Boundary extends Component {
  state = { error: null }
  static getDerivedStateFromError(error) { return { error } }
  componentDidCatch(error, info) { console.error('Page failed to render', error, info.componentStack) }
  render() {
    if (!this.state.error) return this.props.children
    return (
      <div className="notice error" role="alert">
        <strong>This page could not be shown.</strong> {String(this.state.error.message || this.state.error)}
        <p>Your other work is safe. Reload the page, or go back to the case queue.</p>
        <div className="btn-row">
          <button type="button" className="btn primary" onClick={() => window.location.reload()}>Reload</button>
          <a className="btn" href="#/queue">Case queue</a>
        </div>
      </div>
    )
  }
}
