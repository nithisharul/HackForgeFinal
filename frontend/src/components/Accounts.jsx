import { useEffect, useState } from 'react'
import { api, getSession } from '../api/client.js'
import SignIn from './SignIn.jsx'

const CAN = {
  viewer: 'read only',
  investigator: 'record verdicts, keep answers',
  lead: 'also approve documents and new patterns',
  admin: 'also manage accounts',
}

// Sign-in plus, for admins, the list of accounts and their roles.
export default function Accounts() {
  const [, tick] = useState(0)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const session = getSession()
  const admin = session?.role === 'admin'
  const load = () => api.users().then(setData).catch((e) => { setData(null); setError(e.message) })

  useEffect(() => { setError(null); if (admin) load(); else setData(null) }, [admin, session?.investigator])

  const change = (investigator, role) => {
    setError(null)
    api.setRole(investigator, role).then(load).catch((e) => setError(e.message))
  }
  return (
    <section className="card accounts">
      <h3>Access<small>who may approve what</small></h3>
      <SignIn hint="Sign in to approve changes." onChange={() => tick((n) => n + 1)} />
      {error && admin && <p className="notice error" role="alert">{error}</p>}
      {admin && data && (
        <table className="accounts-table">
          <thead><tr><th>Account</th><th>Role</th><th>May</th></tr></thead>
          <tbody>
            {data.users.map((u) => (
              <tr key={u.investigator}>
                <td>{u.investigator}{u.source === '.env' && <small> (.env)</small>}</td>
                <td>
                  {u.source === '.env' ? u.role : (
                    <select value={u.role} aria-label={`Role for ${u.investigator}`} onChange={(e) => change(u.investigator, e.target.value)}>
                      {data.roles.map((r) => <option key={r} value={r}>{r}</option>)}
                    </select>
                  )}
                </td>
                <td><small>{CAN[u.role]}</small></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {session && !admin && <p className="hint">Roles: {Object.entries(CAN).map(([r, t]) => `${r} (${t})`).join('; ')}.</p>}
    </section>
  )
}
