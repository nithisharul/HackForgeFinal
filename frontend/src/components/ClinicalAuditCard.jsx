// Clinical record audit (ported from feature/clinical-audit-rag). The status comes from deterministic checks;
// a local model's reading is fetched second and shown apart as unverified. Read-only: nothing here writes.
import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

const STATUS = {
  discrepancy_found: ['Discrepancy found', 'high'],
  no_discrepancy: ['No discrepancy found', 'ok'],
  insufficient_evidence: ['Insufficient evidence', 'medium'],
  unavailable: ['Unavailable', 'low'],
}
const RESULT = {
  match: ['Matches', 'ok'], consistent: ['Consistent', 'ok'], conflict: ['Conflict in record', 'high'],
  mismatch: ['Mismatch', 'high'], no_claims: ['Not corroborated', 'medium'], not_checked: ['Not checked', 'low'],
}

export default function ClinicalAuditCard({ caseId }) {
  const [a, setA] = useState(null)
  const [model, setModel] = useState(null)
  const [error, setError] = useState(null)
  const [tick, setTick] = useState(0)

  useEffect(() => {
    let live = true
    setA(null); setModel(null); setError(null)
    api.clinicalAudit(caseId, false)
      .then((r) => {
        if (!live) return
        setA(r)
        if (r.llm?.status !== 'not_run' || r.llm?.reason !== 'Not requested') return
        setModel({ status: 'loading' })
        api.clinicalAudit(caseId, true)
          .then((x) => live && setModel(x.llm))
          .catch((e) => live && setModel({ status: 'error', reason: e.message }))
      })
      .catch((e) => live && setError(e.message))
    return () => { live = false }
  }, [caseId, tick])

  return (
    <section className="card clinical" aria-labelledby="ca-title" aria-busy={!a && !error}>
      <h3 id="ca-title">Clinical record audit<small>read-only · synthetic records</small></h3>
      {!a && !error && <p className="muted" role="status">Reading this case's clinical record and running the checks…</p>}
      {error && (
        <div className="notice error" role="alert">
          Clinical audit could not load: {error}
          <div className="btn-row"><button type="button" className="btn" onClick={() => setTick((n) => n + 1)}>Try again</button></div>
        </div>
      )}
      {a && <Audit a={a} model={model || a.llm} />}
    </section>
  )
}

function Chip({ map, value }) {
  const [label, tone] = map[value] || [value, 'low']
  return <span className={`ca-chip ca-${tone}`}>{label}</span>
}

function Audit({ a, model }) {
  return (
    <>
      <p className="ca-status"><Chip map={STATUS} value={a.status} /> {a.status_reason}</p>
      {a.source && (
        <p className="ca-source">
          Source: <strong>{a.source.name}</strong>{a.source.document_title && <> · {a.source.document_title}</>}
          {a.document_facts?.date_of_service && <> · dated {a.document_facts.date_of_service}</>}
          {a.document_facts?.author && <> · {a.document_facts.author}</>} · synthetic record
        </p>
      )}

      {a.findings.length > 0 && (
        <div className="ca-block">
          <h4>{a.status === 'discrepancy_found' ? 'Findings' : 'Stated in the record, not corroborated'}</h4>
          {a.findings.map((f, i) => (
            <div key={i} className={`ca-finding ${f.corroborated_by_claims ? '' : 'weak'}`}>
              <strong>{f.type}</strong>
              <p>{f.detail}</p>
              <Excerpts lines={f.evidence} />
              <small>Basis: {f.basis}{f.corroborated_by_claims ? '; the record is tied to this case’s claims' : '; not tied to a claim in the claims data'}</small>
            </div>
          ))}
        </div>
      )}

      {a.checks.length > 0 && (
        <div className="ca-block">
          <h4>Deterministic checks</h4>
          <ul className="ca-checks">
            {a.checks.map((c) => (
              <li key={c.id}>
                <div><b>{c.label}</b> <Chip map={RESULT} value={c.result} /></div>
                <p>{c.detail}</p>
                {c.result === 'conflict' || c.result === 'mismatch' ? <Excerpts lines={c.evidence} /> : null}
              </li>
            ))}
          </ul>
        </div>
      )}

      {a.recommended_verification.length > 0 && (
        <div className="ca-block">
          <h4>Recommended verification</h4>
          <ol className="checklist">{a.recommended_verification.map((v, i) => <li key={i}>{v}</li>)}</ol>
        </div>
      )}

      {a.source && <ModelReading m={model} />}

      {a.text && (
        <details className="ca-record">
          <summary>View the record ({a.source.characters.toLocaleString()} characters{a.source.truncated ? ', truncated' : ''})</summary>
          {a.document_facts.events.length > 0 && (
            <ol className="ca-events" aria-label="Timestamped events in the record">
              {a.document_facts.events.map((e, i) => (
                <li key={i} className={/BILLED|CLAIM/i.test(e.type) ? 'billed' : undefined}>
                  <time>{e.time}</time> <b>{e.type}</b> <span>{e.detail}</span>
                </li>
              ))}
            </ol>
          )}
          <pre className="ca-text">{a.text}</pre>
        </details>
      )}
    </>
  )
}

function Excerpts({ lines }) {
  if (!lines?.length) return null
  return <ul className="ca-excerpts" aria-label="Excerpts from the record">{lines.map((l, i) => <li key={i}><q>{l}</q></li>)}</ul>
}

function ModelReading({ m }) {
  if (!m) return null
  return (
    <div className="ca-block ca-llm">
      <h4>Local model reading <small>{m.model || 'llama3.2'} · unverified</small></h4>
      {m.status === 'loading' && <p className="muted" role="status">Asking the local model…</p>}
      {(m.status === 'unavailable' || m.status === 'error' || m.status === 'not_run') && (
        <p className="muted">AI reading offline: {m.reason}. The deterministic checks above do not depend on it.</p>
      )}
      {m.status === 'completed' && (
        <>
          <p>
            {m.discrepancy === true ? 'The model reads a discrepancy' : m.discrepancy === false ? 'The model reads no discrepancy' : 'The model gave no clear answer'}
            {m.type && <> ({m.type})</>}: {m.finding || 'no explanation given.'}
          </p>
          <Excerpts lines={m.quotes_verified} />
          {m.quotes_rejected > 0 && <small className="warn">{m.quotes_rejected} quote(s) dropped: not found in the record.</small>}
          {!m.supported && <small className="warn">No quote supports this reading, so treat it with extra caution.</small>}
          <small>{m.note}</small>
        </>
      )}
    </div>
  )
}
