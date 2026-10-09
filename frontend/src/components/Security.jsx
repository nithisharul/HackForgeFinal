import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { useSession } from './SignIn.jsx'

const SEVERITY = { CRITICAL: 'conflict', HIGH: 'warn', MEDIUM: 'warn', LOW: 'muted' }

// Integrity status and system health for everyone; the signed audit trail and the security events for leads and admins.
export default function Security() {
  const [status, setStatus] = useState(undefined)
  const [health, setHealth] = useState(null)
  const [audit, setAudit] = useState(null)
  const [events, setEvents] = useState(null)
  const [reason, setReason] = useState('')
  const [error, setError] = useState(null)
  const session = useSession()
  const role = session?.role
  const privileged = role === 'lead' || role === 'admin'

  const load = () => {
    api.securityStatus().then(setStatus).catch(() => setStatus(null))
    api.health().then(setHealth).catch(() => setHealth(null))
    if (privileged) {
      api.auditTrail().then((r) => setAudit(r.entries)).catch((e) => setError(e.message))
      api.securityEvents().then((r) => setEvents(r.events)).catch((e) => setError(e.message))
    }
  }
  useEffect(load, [privileged])

  if (status === undefined) return <section className="sec" aria-busy="true"><span className="sk sk-line" /></section>
  const bad = status && !status.ok
  const detectors = health ? Object.values(health.pipeline.detectors) : []
  return (
    <>
      <section className="sec" aria-labelledby="integrity-h">
        <h2 id="integrity-h">Knowledge integrity</h2>
        <p className="sec-note">Every approved change to the Second Brain is written to a signed, hash-chained log. The files on disk are compared with it.</p>
        {!status && <p className="notice error" role="alert">The integrity check did not answer. Try again in a moment.</p>}
        {status && (
          <div className={bad ? 'integrity bad' : 'integrity ok'} role={bad ? 'alert' : undefined}>
            <strong>{bad ? `Integrity alert: ${status.problems.length} ${status.problems.length === 1 ? 'problem' : 'problems'}` : 'Verified'}</strong>
            <span>{status.files_checked} knowledge files checked against {status.entries} signed {status.entries === 1 ? 'entry' : 'entries'}. Log chain {status.chain_valid ? 'intact' : 'broken'}.</span>
          </div>
        )}
        {bad && (
          <ul className="plain problems">
            {status.problems.slice(0, 12).map((p, i) => <li key={i}><span className="id">{p.path}</span>: {p.issue}</li>)}
          </ul>
        )}
        {bad && role === 'admin' && (
          <form className="reseal" onSubmit={(e) => { e.preventDefault(); setError(null); api.reseal(reason).then(() => { setReason(''); load() }).catch((er) => setError(er.message)) }}>
            <label className="field">After restoring the files, why accept the current state?
              <input value={reason} onChange={(e) => setReason(e.target.value)} placeholder="What was found and what was restored" />
            </label>
            <button className="btn" disabled={reason.trim().length < 10}>Accept current files</button>
          </form>
        )}
      </section>

      {health && (
        <section className="sec" aria-labelledby="health-h">
          <h2 id="health-h">System health</h2>
          <p className="sec-note">The app keeps working when a part is down; this says what it is working without.</p>
          <dl className="health">
            {detectors.length === 0 && <div><dt>Detection pipeline</dt><dd>No run recorded on this server</dd></div>}
            {detectors.map((d) => (
              <div key={d.label}><dt>{d.label}</dt><dd className={d.ok ? 'ok' : 'bad'}>{d.ok ? `Ran in ${d.seconds}s` : `Failed: ${d.error}`}</dd></div>
            ))}
            {health.pipeline.ran_at && <div><dt>Last pipeline run</dt><dd>{health.pipeline.ran_at.replace('T', ' ')}</dd></div>}
            <div><dt>Language model</dt><dd className={health.llm.reachable ? 'ok' : 'bad'}>{health.llm.reachable ? `Reachable (${health.llm.model})` : 'Not reachable: summaries and answers use templates'}</dd></div>
          </dl>
        </section>
      )}

      <section className="sec" aria-labelledby="events-h">
        <h2 id="events-h">Security events and audit trail</h2>
        {!privileged && <p className="sec-note">Sign in as a lead or admin to see what the defences caught and who approved each change.</p>}
        {error && <p className="notice error" role="alert">{error}</p>}
        {privileged && events && (
          <>
            <h3>Security events</h3>
            {events.length === 0 ? <p className="muted">Nothing caught so far.</p> : (
              <div className="table-wrap">
                <table className="data">
                  <thead><tr><th>When</th><th>Event</th><th>Severity</th><th>Detail</th><th>Action</th></tr></thead>
                  <tbody>
                    {events.slice(0, 20).map((e) => (
                      <tr key={e.event_id}>
                        <td className="nowrap">{e.ts.replace('T', ' ')}</td>
                        <td><span className="id">{e.type}</span></td>
                        <td><span className={`sev sev-${SEVERITY[e.severity] || 'muted'}`}>{e.severity}</span></td>
                        <td>{e.detail}</td>
                        <td>{e.action}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
        {privileged && audit && (
          <>
            <h3>Audit trail</h3>
            <div className="table-wrap">
              <table className="data">
                <thead><tr><th className="num">#</th><th>When</th><th>Who</th><th>What</th><th className="num">Files</th><th>Signature</th></tr></thead>
                <tbody>
                  {audit.slice(0, 30).map((a) => (
                    <tr key={a.seq}>
                      <td className="num">{a.seq}</td>
                      <td className="nowrap">{a.ts.replace('T', ' ')}</td>
                      <td>{a.actor}</td>
                      <td><b>{a.action.replace(/_/g, ' ')}</b> {a.target}{a.detail && `: ${a.detail}`}</td>
                      <td className="num">{a.files}</td>
                      <td><span className="id">{a.hash}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </>
  )
}
