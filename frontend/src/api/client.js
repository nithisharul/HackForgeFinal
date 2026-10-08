// Every backend call lives here. Each one carries the active region (see region.js).
import { getRegion } from '../region.js'

const BASE = import.meta.env.VITE_API_URL || '/api'
const withRegion = (path) => `${path}${path.includes('?') ? '&' : '?'}region=${getRegion()}`

async function request(path, options) {
  const res = await fetch(BASE + withRegion(path), options)
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const detail = Array.isArray(body.detail) ? body.detail.map((d) => d.msg).join('; ') : body.detail
    throw new Error(detail || `Request failed (${res.status})`)
  }
  return res.json()
}

const post = (path, body) =>
  request(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

export const api = {
  queue: (horizon, investigators) => request(`/queue?horizon=${horizon}&investigators=${investigators}`),
  metrics: () => request('/metrics'),
  getCase: (id, horizon) => request(`/cases/${id}?horizon=${horizon}`),
  fhirUrl: (id) => BASE + withRegion(`/cases/${id}/fhir`),
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
