import { useEffect, useRef, useState } from 'react'
import { api, getSession } from '../api/client.js'
import { toast } from './bits.jsx'

// Re-renders whenever someone signs in or out, anywhere on the page.
export function useSession() {
  const [, tick] = useState(0)
  useEffect(() => {
    const on = () => tick((n) => n + 1)
    window.addEventListener('csn-session', on)
    return () => window.removeEventListener('csn-session', on)
  }, [])
  return getSession()
}

// Writes need a signed-in investigator. The server checks the passcode; only the session token is kept, in this tab.
export default function SignIn({ name: initial = '', onDone, compact }) {
  const [name, setName] = useState(initial)
  const [passcode, setPasscode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const session = useSession()

  if (session) {
    if (compact) return null
    return (
      <p className="signed-in">
        Signed in as <strong>{session.investigator}</strong>{' '}
        <button type="button" className="linklike" onClick={() => api.logout()}>Sign out</button>
      </p>
    )
  }
  const submit = (e) => {
    e.preventDefault()
    setBusy(true); setError(null)
    api.login(name.trim(), passcode)
      .then((s) => { setPasscode(''); toast(`Signed in as ${s.investigator}`); onDone?.() })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false))
  }
  return (
    <form className="signin" onSubmit={submit} aria-label="Investigator sign-in">
      {!compact && <p className="hint">Sign in as an investigator to approve this change. You stay signed in for this tab.</p>}
      <label className="field">Investigator name
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="username" required />
      </label>
      <label className="field">Passcode
        <input type="password" value={passcode} onChange={(e) => setPasscode(e.target.value)} autoComplete="current-password" required />
      </label>
      {error && <p className="notice error" role="alert">{error}</p>}
      <button className="btn primary" disabled={busy || name.trim().length < 2 || !passcode}>{busy ? 'Signing in…' : 'Sign in'}</button>
    </form>
  )
}

// Header chip: sign in once, every approve button in the app unlocks.
export function AccountChip() {
  const session = useSession()
  const ref = useRef(null)
  if (session) {
    return (
      <span className="account">
        <span className="avatar" aria-hidden="true">{session.investigator.slice(0, 1).toUpperCase()}</span>
        <span className="account-name">{session.investigator}</span>
        <button type="button" className="top-btn" onClick={() => { api.logout(); toast('Signed out') }}>Sign out</button>
      </span>
    )
  }
  return (
    <>
      <button type="button" className="top-btn" onClick={() => ref.current?.showModal()}>Sign in</button>
      <dialog ref={ref} className="modal" aria-label="Investigator sign-in" onClick={(e) => e.target === ref.current && ref.current.close()}>
        <div className="modal-body">
          <h3>Investigator sign-in</h3>
          <p className="hint">Needed to record verdicts and add to the Second Brain.</p>
          <SignIn compact onDone={() => ref.current?.close()} />
          <button type="button" className="modal-x" aria-label="Close" onClick={() => ref.current?.close()}>×</button>
        </div>
      </dialog>
    </>
  )
}
