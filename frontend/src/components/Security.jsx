import { useEffect, useState } from 'react'
import { api, getSession } from '../api/client.js'

const TONE = { CRITICAL: '#b91c1c', HIGH: '#c2410c', MEDIUM: '#a16207', LOW: '#475569' }

// Integrity status for everyone; the signed audit trail and the security events for leads and admins.
export default function Security({ tick }) {
  const [status, setStatus] = useState(null)
  const [health, setHealth] = useState(null)
  const [audit, setAudit] = useState(null)
  const [events, setEvents] = useState(null)
  const [open, setOpen] = useState(false)
  const [reason, setReason] = useState('')
  const [error, setError] = useState(null)
  const [, bump] = useState(0)
  const role = getSession()?.role
  const privileged = role === 'lead' || role === 'admin'

  const load = () => {
    api.securityStatus().then(setStatus).catch(() => setStatus(null))
    api.health().then(setHealth).catch(() => setHealth(null))
    if (privileged && open) {
      api.auditTrail().then((r) => setAudit(r.entries)).catch((e) => setError(e.message))
      api.securityEvents().then((r) => setEvents(r.events)).catch((e) => setError(e.message))
    }
  }
  useEffect(load, [tick, open, privileged])
  useEffect(() => {
    const sync = () => bump((n) => n + 1)
    window.addEventListener('csn-session', sync)
    return () => window.removeEventListener('csn-session', sync)
  }, [])

  if (!status) return null
  const bad = !status.ok
  return (
    <section className="card security">
      <h3>Security<small>signed audit log and tamper check</small></h3>
      <p className={bad ? 'notice error' : 'sec-ok'} role={bad ? 'alert' : undefined}>
        {bad
          ? `Integrity alert: ${status.problems.length} problem(s) found.`
          : `Integrity verified: ${status.files_checked} knowledge files match the signed log (${status.entries} entries).`}
      </p>
      {bad && (
        <ul className="plain">
          {status.problems.slice(0, 8).map((p, i) => (
            <li key={i}><a className="wikilink" href={`#/brain/${p.page}`}>{p.path}</a>: {p.issue}</li>
          ))}
        </ul>
      )}
      {bad && role === 'admin' && (
        <form className="ask" onSubmit={(e) => { e.preventDefault(); setError(null); api.reseal(reason).then(() => { setReason(''); load() }).catch((er) => setError(er.message)) }}>
          <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="After restoring the files: reason for accepting the current state" />
          <button className="btn" disabled={reason.trim().length < 10}>Accept current files</button>
        </form>
      )}
      {error && <p className="notice error" role="alert">{error}</p>}
      {health && (
        <p className="hint">
          <strong>System health.</strong>{' '}
          {Object.values(health.pipeline.detectors).map((d) => `${d.label}: ${d.ok ? 'ran' : 'FAILED'}`).join(' · ') || 'No pipeline run recorded'}.
          {health.pipeline.ran_at && <> Last run {health.pipeline.ran_at.replace('T', ' ')}.</>}{' '}
          LLM: {health.llm.reachable ? `reachable (${health.llm.model})` : 'not reachable, template mode'}.
        </p>
      )}
      <button type="button" className="linklike" onClick={() => setOpen(!open)}>
        {open ? 'Hide audit trail and security events' : 'Show audit trail and security events'}
      </button>
      {open && !privileged && <p className="hint">Sign in as a lead or admin to see the audit trail and security events.</p>}
      {open && privileged && (
        <>
          <h4>Security events</h4>
          {events && events.length === 0 && <p className="hint">Nothing caught so far.</p>}
          {events && events.length > 0 && (
            <table className="accounts-table">
              <thead><tr><th>Event</th><th>Type</th><th>Severity</th><th>Detail</th><th>Action</th></tr></thead>
              <tbody>
                {events.slice(0, 12).map((e) => (
                  <tr key={e.event_id}>
                    <td>{e.event_id}<br /><small>{e.ts.replace('T', ' ')}</small></td>
                    <td><small>{e.type}</small></td>
                    <td><strong style={{ color: TONE[e.severity] }}>{e.severity}</strong></td>
                    <td><small>{e.detail}</small></td>
                    <td><small>{e.action}</small></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <h4>Audit trail</h4>
          {audit && (
            <table className="accounts-table">
              <thead><tr><th>#</th><th>When</th><th>Who</th><th>What</th><th>Files</th><th>Signature</th></tr></thead>
              <tbody>
                {audit.slice(0, 20).map((a) => (
                  <tr key={a.seq}>
                    <td>{a.seq}</td>
                    <td><small>{a.ts.replace('T', ' ')}</small></td>
                    <td>{a.actor}</td>
                    <td><small><strong>{a.action.replace(/_/g, ' ')}</strong> {a.target}{a.detail && `: ${a.detail}`}</small></td>
                    <td>{a.files}</td>
                    <td><code>{a.hash}</code></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  )
}
