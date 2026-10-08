import { useEffect, useState } from 'react'
import { api, getSession } from '../api/client.js'

// Writes need a signed-in account with the right role. The server checks the passcode and the role on every
// request; only the session token is kept, in this tab.
export default function SignIn({ name: initial = '', onChange, hint = 'Sign in to approve this change.' }) {
  const session = getSession()
  const [mode, setMode] = useState('login') // login | register
  const [name, setName] = useState(initial)
  const [passcode, setPasscode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [note, setNote] = useState(null)
  const [, tick] = useState(0)

  useEffect(() => {
    if (getSession()) api.refreshRole().catch(() => {})
    // Every sign-in box on the page follows the same session.
    const sync = () => { tick((n) => n + 1); onChange?.() }
    window.addEventListener('csn-session', sync)
    return () => window.removeEventListener('csn-session', sync)
  }, [])

  if (session) {
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
    go.then(() => setPasscode(''))
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false))
  }
  const short = mode === 'register' && passcode.length < 12
  return (
    <form className="signin" onSubmit={submit} aria-label={mode === 'register' ? 'Create account' : 'Sign in'}>
      <p className="hint">{mode === 'register'
        ? 'Create an account. The first account on this server becomes the admin; later accounts are read-only until an admin gives them a role.'
        : hint}</p>
      <label className="field">Name
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="username" />
      </label>
      <label className="field">Passcode{mode === 'register' && ' (12 or more characters)'}
        <input type="password" value={passcode} onChange={(e) => setPasscode(e.target.value)}
          autoComplete={mode === 'register' ? 'new-password' : 'current-password'} />
      </label>
      {error && <p className="notice error" role="alert">{error}</p>}
      {note && <p className="hint">{note}</p>}
      <button className="btn primary" disabled={busy || name.trim().length < 2 || !passcode || short}>
        {busy ? 'Working…' : mode === 'register' ? 'Create account and sign in' : 'Sign in'}
      </button>{' '}
      <button type="button" className="linklike" onClick={() => { setMode(mode === 'register' ? 'login' : 'register'); setError(null) }}>
        {mode === 'register' ? 'I already have an account' : 'Create an account'}
      </button>
    </form>
  )
}
