// Every backend call lives here.
const BASE = import.meta.env.VITE_API_URL || '/api'

// Writes need a signed-in investigator (POST /api/auth/login). The session lives in this tab only.
const SESSION_KEY = 'csn-session'
let session = null
try { session = JSON.parse(sessionStorage.getItem(SESSION_KEY)) } catch { /* storage blocked: sign in again */ }
export const getSession = () => (session && session.expires * 1000 > Date.now() ? session : null)
function setSession(s) {
  session = s
  try { s ? sessionStorage.setItem(SESSION_KEY, JSON.stringify(s)) : sessionStorage.removeItem(SESSION_KEY) } catch { /* ignore */ }
  try { window.dispatchEvent(new Event('csn-session')) } catch { /* not in a browser */ }
}

async function request(path, options = {}) {
  const s = getSession()
  const auth = s && (options.method === 'POST' || options.auth) ? { Authorization: `Bearer ${s.token}` } : {}
  const res = await fetch(BASE + path, { ...options, headers: { ...options.headers, ...auth } })
  if (!res.ok) {
    if (res.status === 401 && s) setSession(null) // expired or revoked: the next write asks to sign in again
    const body = await res.json().catch(() => ({}))
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join('; ') : body.detail
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return res.json()
}

const post = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  login: (investigator, passcode) => post('/auth/login', { investigator, passcode }).then((s) => { setSession(s); return s }),
  logout: () => setSession(null),
  register: (investigator, passcode) => post('/auth/register', { investigator, passcode }),
  // The server decides what a role may do; this only keeps the label on screen current.
  refreshRole: () => request('/auth/session', { auth: true }).then((r) => { const cur = getSession(); if (cur) setSession({ ...cur, role: r.role }); return r }),
  users: () => request('/auth/users', { auth: true }),
  securityStatus: () => request('/security/status'),
  health: () => request('/health'),
  auditTrail: () => request('/security/audit', { auth: true }),
  securityEvents: () => request('/security/events', { auth: true }),
  reseal: (reason) => post('/security/reseal', { reason }),
  setRole: (investigator, role) => post('/auth/users/role', { investigator, role }),
  queue: (horizon, investigators) => request(`/queue?horizon=${horizon}&investigators=${investigators}`),
  metrics: () => request('/metrics'),
  getCase: (id, horizon) => request(`/cases/${id}?horizon=${horizon}`),
  graph: (providerId) => request(`/graph/${providerId}`),
  previewVerdict: (id, body) => post(`/cases/${id}/verdict/preview`, body),
  submitVerdict: (id, body) => post(`/cases/${id}/verdict`, body),
  wikiPages: () => request('/wiki'),
  wikiPage: (name) => request(`/wiki/page/${name}`),
  wikiLint: () => request('/wiki/lint'),
  ask: (question) => post('/wiki/ask', { question }),
  fileNote: (body) => post('/wiki/notes', body),
  previewSource: (body) => post('/wiki/sources/preview', body),
  addSource: (body) => post('/wiki/sources', body),
}
