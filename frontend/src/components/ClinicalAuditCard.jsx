import { useEffect, useState } from 'react'
import { api } from '../api/client.js'

// Provider record review: a record returned for a records request, read by the LLM against the flagged claims.
// The record is drawn as one connected timeline. Checkpoint colours follow the evidence palette:
// slate = administrative (badge access), purple = digital (EHR), cyan = clinical, crimson = the billed claim that conflicts.
const KIND = [[/CONCURRENT|BILLED CLAIM/, 'conflict', 'Claim conflict'], [/EHR/, 'digital', 'EHR'],
  [/CLINICAL/, 'clinical', 'Clinical'], [/BADGE|ACCESS/, 'admin', 'Access']]
const kindOf = (type) => KIND.find(([re]) => re.test(type)) || [null, 'admin', 'Note']

function parse(text) {
  const events = []
  const summary = []
  let inSummary = false
  for (const raw of text.split('\n')) {
    const line = raw.trim()
    if (!line) continue
    if (/AUDIT SUMMARY:/i.test(line)) { inSummary = true; continue }
    if (inSummary) { summary.push(line); continue }
    const m = line.match(/^\[(\d{1,2}:\d{2})(?::\d{2})?\s*[A-Za-z]*\]\s*([^:]+):\s*(.*)$/)
    if (m) events.push({ time: m[1], type: m[2].trim(), detail: m[3].trim() })
  }
  return { events, summary: summary.join(' ') }
}

export default function ClinicalAuditCard({ caseId }) {
  const [data, setData] = useState(undefined)
  useEffect(() => {
    let live = true
    setData(undefined)
    api.clinicalAudit(caseId).then((d) => live && setData(d)).catch(() => live && setData(null))
    return () => { live = false }
  }, [caseId])

  if (data === undefined || data === null) return null
  if (!data.artifact) return null // no record received: nothing to show, the action plan asks for one
  const a = data.artifact
  const read = data.status === 'read'
  const { events, summary } = parse(a.text_content)
  const tone = !read ? 'unread' : a.discrepancy_found ? 'flag' : 'ok'
  return (
    <section className="sec record" aria-labelledby="record-h">
      <div className="record-head">
        <div>
          <h2 id="record-h">Provider record review</h2>
          <p className="sec-note">{a.author}, date of service {a.date_of_service}. File <span className="id">{data.source_file}</span>, a synthetic sample.</p>
        </div>
        <span className={`record-verdict ${tone}`}>
          {tone === 'flag' ? 'Possible discrepancy' : tone === 'ok' ? 'No discrepancy found' : 'Not read by the LLM'}
        </span>
      </div>
      {read && a.finding && (
        <p className={tone === 'flag' ? 'record-finding flag' : 'record-finding'}>
          {a.finding} <small>Read by {a.model_auditor}. A lead for review, not a finding.</small>
        </p>
      )}
      <ol className="checkpoints" aria-label={`${events.length} checkpoints in the record`}>
        {events.map((e, i) => {
          const [, k, label] = kindOf(e.type)
          return (
            <li key={i} className={`cp cp-${k}`}>
              <time className="id">{e.time}</time>
              <span className={`cp-kind cp-kind-${k}`}>{label}</span>
              <span className="cp-detail">{e.detail}</span>
            </li>
          )
        })}
      </ol>
      {summary && <p className="record-summary"><b>Record summary:</b> {summary}</p>}
      {a.statute && <p className="formula">Background: {a.statute}.</p>}
    </section>
  )
}
