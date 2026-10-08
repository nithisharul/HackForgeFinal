import { useState } from 'react'
import { api, getSession } from '../api/client.js'

// Writes need a signed-in investigator. The server checks the passcode; only the session token is kept, in this tab.
export default function SignIn({ name: initial = '', onChange }) {
  const session = getSession()
  const [name, setName] = useState(initial)
  const [passcode, setPasscode] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  if (session) {
    return (
      <p className="signed-in">
        Signed in as <strong>{session.investigator}</strong>{' '}
        <button type="button" className="linklike" onClick={() => { api.logout(); onChange?.() }}>Sign out</button>
      </p>
    )
  }
  const submit = (e) => {
    e.preventDefault()
    setBusy(true); setError(null)
    api.login(name.trim(), passcode)
      .then(() => { setPasscode(''); onChange?.() })
      .catch((err) => setError(err.message))
      .finally(() => setBusy(false))
  }
  return (
    <form className="signin" onSubmit={submit} aria-label="Investigator sign-in">
      <p className="hint">Sign in as an investigator to approve this change.</p>
      <label className="field">Investigator name
        <input value={name} onChange={(e) => setName(e.target.value)} autoComplete="username" />
      </label>
      <label className="field">Passcode
        <input type="password" value={passcode} onChange={(e) => setPasscode(e.target.value)} autoComplete="current-password" />
      </label>
      {error && <p className="notice error" role="alert">{error}</p>}
      <button className="btn primary" disabled={busy || name.trim().length < 2 || !passcode}>{busy ? 'Signing in…' : 'Sign in'}</button>
    </form>
  )
}
