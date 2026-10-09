import Accounts from '../components/Accounts.jsx'
import Security from '../components/Security.jsx'

// Who may approve what, and whether the Second Brain is intact.
export default function Admin() {
  return (
    <>
      <header className="page-head">
        <div>
          <h1>Security and access</h1>
          <p>Accounts and roles, the signed audit trail, and a tamper check of every knowledge file in both regions.</p>
        </div>
      </header>
      <div className="admin">
        <div className="doc"><Security /></div>
        <aside className="rail"><Accounts /></aside>
      </div>
    </>
  )
}
