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

const CAN = { viewer: 'read only', investigator: 'can record verdicts', lead: 'can approve documents', admin: 'can manage accounts' }
export const roleNote = (role) => CAN[role] || ''

// Writes need a signed-in account with the right role. The server checks the passcode and the role on every
// request; only the session token is kept, in this tab.
export default function SignIn({ name: initial = '', onDone, compact, hint = 'Sign in to approve this change. You stay signed in for this tab.' }) {
  const [mode, setMode] = useState('login') // login | register
  const [name, setName] = useState(initial)
  const [passcode, setPasscode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [note, setNote] = useState(null)
  const session = useSession()
  useEffect(() => { if (getSession()) api.refreshRole().catch(() => {}) }, [])

  if (session) {
    if (compact) return null
    return (
      <p className="signed-in">
        Signed in as <strong>{session.investigator}</strong>{session.role && <> ({session.role})</>}{' '}
        <button type="button" className="linklike" onClick={() => api.logout()}>Sign out</button>
        {session.role === 'viewer' && <><br /><small>Viewers can read only. Ask an admin for the investigator or lead role.</small></>}
      </p>
    )
  }
  const submit = (e) => {
    e.preventDefault()
    setBusy(true); setError(null); setNote(null)
    const who = name.trim()
    const go = mode === 'register'
      ? api.register(who, passcode).then((r) => { setNote(r.message); return api.login(who, passcode) })
      : api.login(who, passcode)
    go.then((s) => { setPasscode(''); toast(`Signed in as ${s.investigator}`); onDone?.() })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false))
  }
  const short = mode === 'register' && passcode.length < 12
  return (
    <form className="signin" onSubmit={submit} aria-label={mode === 'register' ? 'Create account' : 'Sign in'}>
      {(!compact || mode === 'register') && (
        <p className="hint">{mode === 'register'
          ? 'The first account on this server becomes the admin. Later accounts can read only until an admin gives them a role.'
          : hint}</p>
      )}
      <label className="field">Name
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="username" required />
      </label>
      <label className="field">Passcode{mode === 'register' && ' (12 or more characters)'}
        <input type="password" value={passcode} onChange={(e) => setPasscode(e.target.value)}
          autoComplete={mode === 'register' ? 'new-password' : 'current-password'} required />
      </label>
      {error && <p className="notice error" role="alert">{error}</p>}
      {note && <p className="hint">{note}</p>}
      <div className="signin-actions">
        <button className="btn primary" disabled={busy || name.trim().length < 2 || !passcode || short}>
          {busy ? 'Working…' : mode === 'register' ? 'Create account and sign in' : 'Sign in'}
        </button>
        <button type="button" className="linklike" onClick={() => { setMode(mode === 'register' ? 'login' : 'register'); setError(null) }}>
          {mode === 'register' ? 'I already have an account' : 'Create an account'}
        </button>
      </div>
    </form>
  )
}

// Sidebar chip: sign in once, every approve button in the app unlocks.
export function AccountChip() {
  const session = useSession()
  const ref = useRef(null)
  if (session) {
    return (
      <span className="account">
        <span className="avatar" aria-hidden="true">{session.investigator.slice(0, 1).toUpperCase()}</span>
        <span className="account-name">{session.investigator}{session.role && <small>{session.role}</small>}</span>
        <button type="button" className="top-btn" onClick={() => { api.logout(); toast('Signed out') }}>Sign out</button>
      </span>
    )
  }
  return (
    <>
      <button type="button" className="top-btn" onClick={() => ref.current?.showModal()}>Sign in</button>
      <dialog ref={ref} className="modal" aria-label="Sign in" onClick={(e) => e.target === ref.current && ref.current.close()}>
        <div className="modal-body">
          <h3>Sign in</h3>
          <p className="hint">Needed to record verdicts and add to the Second Brain.</p>
          <SignIn compact onDone={() => ref.current?.close()} />
          <button type="button" className="modal-x" aria-label="Close" onClick={() => ref.current?.close()}>×</button>
        </div>
      </dialog>
    </>
  )
}
