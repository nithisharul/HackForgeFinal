import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import SignIn, { roleNote, useSession } from './SignIn.jsx'

// Sign-in plus, for admins, every account and its role. The server enforces roles; this only manages them.
export default function Accounts() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const session = useSession()
  const admin = session?.role === 'admin'
  const load = () => api.users().then(setData).catch((e) => { setData(null); setError(e.message) })
  useEffect(() => { setError(null); if (admin) load(); else setData(null) }, [admin, session?.investigator])

  const change = (investigator, role) => { setError(null); api.setRole(investigator, role).then(load).catch((e) => setError(e.message)) }
  return (
    <section className="sec" aria-labelledby="access-h">
      <h2 id="access-h">Access</h2>
      <p className="sec-note">Each role includes the ones before it: viewer, investigator, lead, admin.</p>
      <SignIn hint="Sign in to see your role. Admins manage everyone's role here." />
      {error && admin && <p className="notice error" role="alert">{error}</p>}
      {admin && data && (
        <div className="table-wrap">
          <table className="data">
            <thead><tr><th>Account</th><th>Role</th><th>May</th><th>Created</th></tr></thead>
            <tbody>
              {data.users.map((u) => (
                <tr key={u.investigator}>
                  <td>{u.investigator}{u.source === '.env' && <small> (server file)</small>}</td>
                  <td>
                    {u.source === '.env' ? u.role : (
                      <select value={u.role} aria-label={`Role for ${u.investigator}`} onChange={(e) => change(u.investigator, e.target.value)}>
                        {data.roles.map((r) => <option key={r} value={r}>{r}</option>)}
                      </select>
                    )}
                  </td>
                  <td>{roleNote(u.role)}</td>
                  <td className="nowrap">{u.created ? u.created.replace('T', ' ') : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}
