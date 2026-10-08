// PrecedentGuard in the UI: why each precedent counts (or not), and revoking a wrong verdict as precedent.
import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import SignIn, { useSession } from './SignIn.jsx'
import { Status, pct, toast } from './bits.jsx'

const EFFECT = { accepted: 'Accepted', reduced: 'Reduced', rejected: 'Set aside', revoked: 'Revoked' }
const pts = (d) => `${d >= 0 ? '+' : '−'}${Math.abs(Math.round(d * 100))} pts`

export function PrecedentEffects({ precedents, effects = [], revoked = [], capped }) {
  const byId = Object.fromEntries(effects.map((e) => [e.case_id, e]))
  return (
    <>
      {precedents.map((p) => {
        const e = byId[p.case_id]
        return (
          <div key={p.case_id} className="prec">
            <a className="wikilink" href={`#/brain/${p.case_id}`}>{p.case_id}</a>{' '}
            <Status status={p.verdict} />{' '}
            {e && <span className={`effect effect-${e.status}`}>{EFFECT[e.status]}{e.status !== 'rejected' && ` ${pts(e.delta)}`}</span>}{' '}
            <small>{p.why.join(', ')}, closed {p.closed}</small>
            {e && e.status !== 'accepted' && <p className="effect-why">{e.why.join('; ')}</p>}
            <p>{p.reasoning}</p>
          </div>
        )
      })}
      {capped && <p className="muted">The combined precedent adjustment is capped at −35 to +30 points.</p>}
      {revoked.length > 0 && (
        <div className="revoked-list">
          <h4>Revoked precedents <small>kept for the record, no weight</small></h4>
          {revoked.map((r) => (
            <p key={r.case_id}>
              <a className="wikilink" href={`#/brain/${r.case_id}`}>{r.case_id}</a> <Status status={r.verdict} />{' '}
              <span className="effect effect-revoked">Revoked</span>{' '}
              <small>{r.revoked} by {r.revoked_by}: {r.reason}</small>
            </p>
          ))}
        </div>
      )}
    </>
  )
}

// A closed verdict's pull on the open queue, and the control to withdraw it. inline: inside a Second Brain page.
export function PrecedentInfluence({ caseId, inline }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [revoking, setRevoking] = useState(false)
  const [reason, setReason] = useState('')
  const [busy, setBusy] = useState(false)
  const session = useSession()
  const load = () => { setError(null); api.precedentInfluence(caseId).then(setData).catch((e) => setError(e.message)) }
  useEffect(() => { setData(null); setRevoking(false); load() }, [caseId])

  const revoke = () => {
    setBusy(true); setError(null)
    api.revokePrecedent(caseId, reason.trim())
      .then((r) => {
        toast(`${caseId} revoked as precedent · ${r.restored.length} open case${r.restored.length === 1 ? '' : 's'} re-scored`)
        setRevoking(false); setReason(''); load()
      })
      .catch((e) => setError(e.message))
      .finally(() => setBusy(false))
  }

  const body = (
    <>
      {!data && !error && <p className="muted" role="status">Checking which open cases this verdict moves…</p>}
      {error && <p className="notice error" role="alert">{error}</p>}
      {data && data.revoked && (
        <p className="pg-revoked">
          <span className="effect effect-revoked">Revoked</span> on {data.revoked} by {data.revoked_by}: {data.revoke_reason}{' '}
          The verdict still stands for this case; it no longer moves any other case's score or rank.
        </p>
      )}
      {data && !data.revoked && (
        <>
          {data.affected.length === 0
            ? <p className="muted">This verdict currently moves no open case's score.</p>
            : (
              <div className="table-wrap">
                <table className="pg-table">
                  <caption className="sr-only">Open cases this precedent moves, with and without it</caption>
                  <thead><tr><th>Case</th><th className="num">Confidence now → without</th><th>Tier</th><th className="num">Rank now → without</th></tr></thead>
                  <tbody>
                    {data.affected.map((r) => (
                      <tr key={r.case_id} className={r.tier_changed ? 'changed' : undefined}>
                        <td><a href={`#/case/${r.case_id}`}>{r.case_id}</a></td>
                        <td className="num">{pct(r.score)} → {pct(r.score_without)}</td>
                        <td>{r.tier}{r.tier_changed && ` → ${r.tier_without}`}</td>
                        <td className="num">{r.rank ?? '–'} → {r.rank_without ?? '–'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          {!revoking && (
            <div className="btn-row">
              <button type="button" className="btn" onClick={() => setRevoking(true)}>Revoke as precedent…</button>
            </div>
          )}
          {revoking && (
            <div className="pg-revoke">
              <label className="field">Why should this verdict stop guiding other cases?
                <textarea rows="2" value={reason} onChange={(e) => setReason(e.target.value)} maxLength={1000}
                  placeholder="For example: the records later showed the referrals were independent." />
                <small className={reason.trim().length >= 10 ? 'count ok' : 'count'}>{reason.trim().length} / 10 characters minimum</small>
              </label>
              <p className="hint">The case page and the log keep the verdict and this reason. Scores and ranks above are restored at once.</p>
              <SignIn />
              <div className="btn-row">
                <button type="button" className="btn primary" disabled={busy || !session || reason.trim().length < 10} onClick={revoke}>
                  {busy ? 'Revoking…' : 'Revoke and re-score'}
                </button>
                <button type="button" className="btn" onClick={() => setRevoking(false)}>Cancel</button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  )
  if (inline) return <section className="pg-inline" aria-label="Influence as precedent"><h4>Influence as precedent <small>PrecedentGuard</small></h4>{body}</section>
  return (
    <section className="card" aria-labelledby={`pg-${caseId}`}>
      <h3 id={`pg-${caseId}`}>Influence as precedent<small>PrecedentGuard</small></h3>
      {body}
    </section>
  )
}
