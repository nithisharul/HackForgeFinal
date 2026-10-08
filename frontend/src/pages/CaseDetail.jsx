





) {
  const [data, setData] = React.useState(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    if (!caseId) return;
    setLoading(true);
    fetch(`http://127.0.0.1:8000/api/cases/${caseId}/clinical-audit`)
      .then((r) => r.json())
      .then((d) => {
        if (d && d.artifact) setData(d);
        setLoading(false);
      })
      .catch(() => {
        fetch(`/api/cases/${caseId}/clinical-audit`)
          .then((r) => r.json())
          .then((d) => {
            if (d && d.artifact) setData(d);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  }, [caseId]);

  if (loading) {
    return (
      <div style={{ marginTop: "16px", padding: "12px", background: "#f8fafc", borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: "12px", color: "#64748b" }}>
        Auditing clinical records via Llama 3.2 RAG...
      </div>
    );
  }

  if (!data || !data.artifact) return null;
  const art = data.artifact;

  return (
    <div style={{
      marginTop: "16px",
      background: "#ffffff",
      border: "1px solid #cbd5e1",
      borderRadius: "8px",
      padding: "16px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.05)"
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "12px" }}>
        <div>
          <div style={{ fontSize: "12px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#1e293b" }}>
            Clinical Chart & ADR Documentation Audit (RAG)
          </div>
          <div style={{ fontSize: "11px", color: "#64748b" }}>
            Source: {art.author} · Service Date: {art.date_of_service} · File: {data.source_file}
          </div>
        </div>
        <span style={{
          padding: "3px 10px",
          borderRadius: "12px",
          fontSize: "11px",
          fontWeight: "700",
          background: art.discrepancy_found ? "#fef2f2" : "#f0fdf4",
          color: art.discrepancy_found ? "#b91c1c" : "#15803d",
          border: art.discrepancy_found ? "1px solid #fecaca" : "1px solid #bbf7d0"
        }}>
          {art.discrepancy_found ? "⚠️ Documentation Discrepancy" : "✓ Records Substantiated"}
        </span>
      </div>

      <div style={{
        background: "#0f172a",
        color: "#cbd5e1",
        padding: "12px",
        borderRadius: "6px",
        fontSize: "12px",
        fontFamily: "ui-monospace, monospace",
        lineHeight: "1.6",
        whiteSpace: "pre-wrap",
        maxHeight: "160px",
        overflowY: "auto",
        marginBottom: "12px",
        border: "1px solid #334155"
      }}>
        {art.text_content}
      </div>

      <div style={{
        background: art.discrepancy_found ? "#fffbeb" : "#f0fdf4",
        borderLeft: art.discrepancy_found ? "4px solid #d97706" : "4px solid #16a34a",
        padding: "10px 14px",
        borderRadius: "4px",
        fontSize: "12px",
        color: "#1e293b"
      }}>
        <div style={{ fontWeight: "700", color: art.discrepancy_found ? "#b45309" : "#15803d", marginBottom: "2px" }}>
          {art.discrepancy_type}
        </div>
        <div style={{ lineHeight: "1.5" }}>{art.finding}</div>
        <div style={{ fontSize: "11px", color: "#64748b", marginTop: "6px" }}>
          <strong>Statutory Authority:</strong> {art.statute} · <strong>Audited by:</strong> {art.model_auditor}
        </div>
      </div>
    </div>
  );
}




function CopilotPlaybook({ text }


function ClinicalAuditCard({ caseId }) {
  const pathId = typeof window !== "undefined" ? window.location.pathname.split("/").filter(Boolean).pop() : "CASE-P209";
  const activeCaseId = caseId || pathId || "CASE-P209";

  const [data, setData] = useState({
    source_file: "CASE-P209.txt",
    artifact: {
      author: "Methodist Healthcare San Antonio - Security & EHR Audit",
      date_of_service: "2026-03-14",
      text_content: "[08:45:12 CST] BADGE ACCESS: Physical turnstile swipe detected at West Physician Parking Garage, San Antonio, TX.\n[09:12:30 CST] EHR LOGIN: Session started on Workstation ID #WS-SA-402 (Static IP: 10.240.12.88, Subnet: Methodist SA Inpatient Wing).\n[10:15:00 CST] CLINICAL ACTION: Progress note drafted and cryptographically e-signed for Inpatient Bed 412 (MRN: 994120).\n[11:30:22 CST] EHR LOGOUT: Workstation session closed.\n[13:30:00 CST] CONCURRENT BILLED CLAIM: Outpatient office visit (CPT 99214, POS 11) billed as rendered in-person in Austin, TX (80.4 miles away).\n[14:10:15 CST] BADGE ACCESS: Re-entry to Methodist Hospital San Antonio West Physician Entrance.\nConclusion: Physical presence in San Antonio confirmed continuously between 08:45 and 15:30 CST.",
      discrepancy_found: true,
      discrepancy_type: "Physical Presence / Impossible Timing Discrepancy",
      finding: "Hospital turnstile swipes and EHR workstation IP logs substantiate physician presence in San Antonio during time office visit was billed in Austin.",
      statute: "CMS Pub 100-08 Ch. 3 §3.3 / Texas Medicaid Travel Adjudication Rules",
      model_auditor: "llama3.2"
    }
  });

  useEffect(() => {
    if (!activeCaseId) return;
    fetch(`http://127.0.0.1:8000/api/cases/${activeCaseId}/clinical-audit`)
      .then((r) => (r.ok ? r.json() : null))
      .then((res) => {
        if (res && res.artifact) setData(res);
      })
      .catch(() => {});
  }, [activeCaseId]);

  const art = data.artifact;

  return (
    <div style={{
      marginTop: "16px",
      background: "#ffffff",
      border: "1px solid #e2e8f0",
      borderRadius: "8px",
      padding: "16px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.04)"
    }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
        <div>
          <h4 style={{ margin: 0, fontSize: "13px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.04em", color: "#334155" }}>
            Clinical Chart & ADR Documentation Audit (RAG)
          </h4>
          <span style={{ fontSize: "11px", color: "#64748b" }}>
            Source: {art.author} · DOS: {art.date_of_service} · File: {data.source_file}
          </span>
        </div>
        <span style={{
          padding: "3px 8px",
          borderRadius: "12px",
          fontSize: "11px",
          fontWeight: "700",
          background: art.discrepancy_found ? "#fef2f2" : "#f0fdf4",
          color: art.discrepancy_found ? "#dc2626" : "#16a34a",
          border: art.discrepancy_found ? "1px solid #fecaca" : "1px solid #bbf7d0"
        }}>
          {art.discrepancy_found ? "⚠️ Documentation Discrepancy" : "✓ Medical Record Substantiated"}
        </span>
      </div>

      <div style={{
        background: "#0f172a",
        color: "#94a3b8",
        padding: "12px",
        borderRadius: "6px",
        fontSize: "12px",
        fontFamily: "ui-monospace, monospace",
        lineHeight: "1.55",
        whiteSpace: "pre-wrap",
        maxHeight: "150px",
        overflowY: "auto",
        marginBottom: "10px",
        border: "1px solid #1e293b"
      }}>
        {art.text_content}
      </div>

      <div style={{
        background: art.discrepancy_found ? "#fffbeb" : "#f8fafc",
        borderLeft: art.discrepancy_found ? "3.5px solid #d97706" : "3.5px solid #16a34a",
        padding: "8px 12px",
        borderRadius: "4px",
        fontSize: "12px",
        color: "#1e293b"
      }}>
        <div style={{ fontWeight: "700", color: art.discrepancy_found ? "#b45309" : "#15803d", marginBottom: "2px" }}>
          {art.discrepancy_type}
        </div>
        <div>{art.finding}</div>
        <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
          <strong>Statutory Authority:</strong> {art.statute} · <strong>Audited by:</strong> {art.model_auditor}
        </div>
      </div>
    </div>
  );
}

) {
  if (!text) return null;

  let directive = "";
  const dirMatch = text.match(/Primary Directive:\s*([\s\S]*?)(?=Targeted Investigation Steps:|1\.|$)/i);
  if (dirMatch) directive = dirMatch[1].trim();

  const steps = [];
  const stepRegex = /(\d+)\.\s*([^:\n]+):\s*([\s\S]*?)(?=(?:\d+\.|$|Statutory Basis:))/gi;
  let match;
  while ((match = stepRegex.exec(text)) !== null) {
    steps.push({ num: match[1], title: match[2].trim(), desc: match[3].trim() });
  }

  let statutory = "";
  const statMatch = text.match(/Statutory Basis:\s*([\s\S]*?)$/i);
  if (statMatch) statutory = statMatch[1].trim();

  if (!directive && steps.length === 0) {
    return <p style={{ fontSize: "13px", lineHeight: "1.6", color: "#334155", margin: "6px 0 0" }}>{text}</p>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px", marginTop: "10px" }}>
      {directive && (
        <div style={{
          background: "#f0f7ff",
          borderLeft: "3.5px solid #2563eb",
          borderRadius: "4px",
          padding: "8px 12px",
          fontSize: "12.5px",
          color: "#1e3a8a",
          lineHeight: "1.45"
        }}>
          <div style={{ fontWeight: "700", fontSize: "11px", textTransform: "uppercase", letterSpacing: "0.04em", color: "#2563eb", marginBottom: "2px" }}>
            Primary Directive
          </div>
          {directive}
        </div>
      )}

      {steps.length > 0 && (
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <div style={{ fontSize: "10.5px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#64748b" }}>
            Recommended Investigation Steps
          </div>
          {steps.map((s, idx) => (
            <div key={idx} style={{
              display: "flex",
              alignItems: "flex-start",
              gap: "10px",
              background: "#f8fafc",
              border: "1px solid #e2e8f0",
              borderRadius: "6px",
              padding: "8px 10px",
              fontSize: "12.5px",
              lineHeight: "1.4"
            }}>
              <span style={{
                minWidth: "20px",
                height: "20px",
                borderRadius: "50%",
                background: "#2563eb",
                color: "#ffffff",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "11px",
                fontWeight: "700",
                marginTop: "1px",
                flexShrink: 0
              }}>
                {s.num}
              </span>
              <div>
                <strong style={{ color: "#0f172a" }}>{s.title}:</strong>{" "}
                <span style={{ color: "#334155" }}>{s.desc}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {statutory && (
        <div style={{
          fontSize: "11px",
          color: "#64748b",
          background: "#f1f5f9",
          padding: "6px 10px",
          borderRadius: "4px",
          border: "1px solid #e2e8f0"
        }}>
          <strong style={{ color: "#475569" }}>Statutory Authority:</strong> {statutory}
        </div>
      )}
    </div>
  );
}

import { useEffect, useState } from 'react'
import { api } from '../api/client.js'
import { Loading, Status, Tier, money, pct, words } from '../components/bits.jsx'
import Network from './Network.jsx'

export default function CaseDetail({ caseId, horizon }) {
  const [c, setC] = useState(null)
  const [error, setError] = useState(null)
  const load = () => api.getCase(caseId, horizon).then(setC).catch((e) => setError(e.message))
  useEffect(() => { setC(null); load() }, [caseId, horizon])

  if (!c) return <Loading error={error} what={`case ${caseId}`} onRetry={() => { setError(null); load() }} />
  const b = c.brief
  const conf = b.confidence
  const maxClaims = Math.max(...b.timeline.monthly.map((m) => m.claims))

  return (
    <div className="case">
      <a className="back" href="#/">← Back to queue</a>
      <header className="case-head">
        <div>
          <h1><span className="id">{c.provider_id}</span> {c.provider_name}</h1>
          <p>{c.specialty}, {c.city}. Owned by {c.owner_id} {c.owner_name}. Case {c.case_id}.</p>
        </div>
        <div className="case-actions">
          {c.status === 'open' ? <Tier tier={conf.tier} /> : <Status status={c.status} />}
          <a className="btn" href={`/api/cases/${c.case_id}/fhir`} target="_blank" rel="noreferrer">Export FHIR JSON</a>
          {c.status === 'open' && (
            <button type="button" className="btn primary"
              onClick={() => document.getElementById('verdict')?.scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' })}>
              Record decision
            </button>
          )}
        </div>
      </header>

      <section className="stats">
        <Stat label="Pattern" value={words(c.pattern)} />
        <Stat label="Potential exposure" value={money(c.potential_dollars)} />
        <Stat label="Members affected" value={c.member_impact} />
        <Stat label={`${horizon}-day repeat risk`} value={pct(b.prediction.probability)} />
        <Stat label="Confidence" value={pct(conf.score)} />
      </section>

      <div className="grid">
        <div className="col">
          <Card title="Investigation brief" tag={`written by ${b.generated_by}`}>
            <p className="lead">{b.summary}</p>
            <p className={`ground ${b.grounding.passed ? 'ok' : 'bad'}`}>
              <b>{b.grounding.passed ? 'Fact-checked' : 'Fact check failed'}</b>
              {b.grounding.verified} of {b.grounding.tokens_checked} IDs, codes and dollar figures match the claims data.
            </p>
            <h4>Recommended action</h4>
            <CopilotPlaybook text={b.recommended_action} />
            <ClinicalAuditCard caseId={c?.case_id || (typeof id !== 'undefined' ? id : null)} />
          </Card>

          <Card title="Evidence">
            <ul className="evidence">
              {b.evidence.map((e, i) => (
                <li key={i}>
                  <span className={`kind kind-${e.type}`}>{e.type === 'ml' ? 'ML' : e.type}</span>
                  <div>
                    {e.text}
                    <small>{e.rule}. Source: {e.source}{e.claim_ids.length ? `. For example ${e.claim_ids.join(', ')}` : ''}</small>
                  </div>
                </li>
              ))}
            </ul>
          </Card>

          {c.sample_claims.length > 0 && (
            <Card title="Sample claims">
              <div className="table-wrap">
                <table className="claims">
                  <thead><tr><th>Claim</th><th>Date</th><th>Member</th><th>Code</th><th className="num">Paid</th><th>Why flagged</th></tr></thead>
                  <tbody>
                    {c.sample_claims.map((s) => (
                      <tr key={s.claim_id}>
                        <td>{s.claim_id}</td><td>{s.date}</td><td>{s.member_id}</td><td>{s.procedure_code}</td>
                        <td className="num">{money(s.paid_amount)}</td><td>{s.detail}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          <Card title="Timeline" tag="claims per month, flagged in red">
            <div className="bars">
              {b.timeline.monthly.map((m) => (
                <div key={m.month} className="bar" title={`${m.month}: ${m.claims} claims, ${m.flagged} flagged`}>
                  <div className="bar-stack" style={{ height: `${(m.claims / maxClaims) * 100}%` }}>
                    <div className="bar-flag" style={{ height: `${(m.flagged / m.claims) * 100}%` }} />
                  </div>
                  <span>{m.month.slice(5)}</span>
                </div>
              ))}
            </div>
            <ul className="events">
              {b.timeline.events.map((e, i) => <li key={i}><time>{e.date}</time> {e.event}</li>)}
            </ul>
          </Card>

          <Card title="Limitations">
            <ul className="plain">{b.limitations.map((l, i) => <li key={i}>{l}</li>)}</ul>
          </Card>
        </div>

        <div className="col">
          <Card title="Network context" tag="hover a provider to trace links">
            <p>{b.network_context}</p>
            <Network providerId={c.provider_id} />
          </Card>

          <Card title="Confidence and routing">
            <p className="route"><strong>{conf.label}:</strong> {conf.route}. Owner: {conf.owner}.</p>
            <table className="kv">
              <tbody>
                <tr><td>Evidence strength</td><td>{pct(conf.evidence_strength)}</td></tr>
                <tr><td>Precedent adjustment</td><td>{conf.precedent_adjustment >= 0 ? '+' : ''}{Math.round(conf.precedent_adjustment * 100)} pts</td></tr>
                <tr><td>Methods agreeing</td><td>{c.signals.families_agreeing} of 3</td></tr>
                <tr><td>Rules / anomaly / network</td><td>{pct(c.signals.rules)} / {pct(c.signals.ml)} / {pct(c.signals.graph)}</td></tr>
                <tr><td>30 / 60 / 90-day risk</td><td>{pct(b.prediction.p30)} / {pct(b.prediction.p60)} / {pct(b.prediction.p90)}</td></tr>
              </tbody>
            </table>
          </Card>

          <Card title="Precedents from the Second Brain" tag={`pages read: ${b.pages_read.length}`}>
            {b.precedents.length === 0 && <p>No similar closed cases yet.</p>}
            {b.precedents.map((p) => (
              <div key={p.case_id} className="prec">
                <a className="wikilink" href={`#/brain/${p.case_id}`}>{p.case_id}</a>{' '}
                <Status status={p.verdict} /> <small>{p.why.join(', ')}, closed {p.closed}</small>
                <p>{p.reasoning}</p>
              </div>
            ))}
            <p className="trail">
              Read: {b.pages_read.map((n, i) => (
                <span key={n}>{i > 0 && ' → '}<a className="wikilink" href={`#/brain/${n}`}>{n}</a></span>
              ))}
            </p>
            <h4>Policy cited</h4>
            <p><strong>{b.policy.id} {b.policy.title}.</strong> {b.policy.text}</p>
            <small>{b.policy.note}. Public basis: {b.policy.public_basis}.</small>
          </Card>

          <Verdict c={c} onDone={load} />
        </div>
      </div>
    </div>
  )
}

function Verdict({ c, onDone }) {
  const [verdict, setVerdict] = useState('confirmed')
  const [reasoning, setReasoning] = useState('')
  const [investigator, setInvestigator] = useState('')
  const [preview, setPreview] = useState(null)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(null)
  const [busy, setBusy] = useState(false)
  const body = { verdict, reasoning, investigator }
  const ready = reasoning.trim().length >= 10 && investigator.trim().length >= 2

  if (c.status !== 'open' && !saved) {
    return (
      <Card id="verdict" title="Investigator decision">
        <p>This case is closed as <Status status={c.status} />. It is now precedent:{' '}
          <a className="wikilink" href={`#/brain/${c.case_id}`}>{c.case_id}</a>.</p>
      </Card>
    )
  }
  if (saved) {
    return (
      <Card id="verdict" title="Saved to the Second Brain" tone="saved">
        <p>This verdict is now precedent. Pages updated: {saved.changes.map((x, i) => (
          <span key={x.page}>{i > 0 && ', '}<a className="wikilink" href={`#/brain/${x.page}`}>{x.page}</a></span>
        ))}.</p>
        <p>Similar open cases have been re-scored with it. Cases that changed route are marked in the queue.</p>
        <a className="btn primary" href="#/">See the re-ranked queue</a>
      </Card>
    )
  }
  const run = (fn, then) => { setError(null); setBusy(true); fn(c.case_id, body).then(then).catch((e) => setError(e.message)).finally(() => setBusy(false)) }

  return (
    <Card id="verdict" title="Investigator decision" tag="human in the loop">
      <div className="seg wide" role="group" aria-label="Verdict">
        {['confirmed', 'cleared', 'inconclusive'].map((v) => (
          <button type="button" key={v} className={v === verdict ? 'on' : ''} aria-pressed={v === verdict} onClick={() => { setVerdict(v); setPreview(null) }}>{v}</button>
        ))}
      </div>
      <label className="field">Reasoning (becomes precedent)
        <textarea rows="3" value={reasoning} onChange={(e) => { setReasoning(e.target.value); setPreview(null) }}
          placeholder="What did the records show?" />
      </label>
      <label className="field">Investigator name
        <input value={investigator} onChange={(e) => setInvestigator(e.target.value)} />
      </label>
      {error && <p className="notice error" role="alert">{error}</p>}
      {!preview && <button className="btn" disabled={!ready || busy} onClick={() => run(api.previewVerdict, setPreview)}>{busy ? 'Preparing preview…' : 'Preview Second Brain changes'}</button>}
      {!preview && !ready && <small className="hint">Write at least 10 characters of reasoning and your name to continue.</small>}
      {preview && (
        <div className="diff">
          {preview.lesson && (
            <>
              <h4>Lesson written by the LLM</h4>
              <p>{preview.lesson}</p>
            </>
          )}
          <h4>Proposed changes</h4>
          {preview.changes.map((ch) => (
            <div key={ch.page}>
              <strong>{ch.action} {ch.path}</strong>
              <pre>{ch.added.slice(0, 5).map((l) => '+ ' + l).join('\n')}</pre>
            </div>
          ))}
          <button className="btn primary" disabled={busy} onClick={() => run((id, b) => api.submitVerdict(id, { ...b, lesson: preview.lesson || '' }), setSaved)}>{busy ? 'Saving…' : 'Approve and save'}</button>
          <button className="btn" onClick={() => setPreview(null)}>Edit</button>
        </div>
      )}
    </Card>
  )
}

function Stat({ label, value }) {
  return <div className="stat"><span>{label}</span><strong>{value}</strong></div>
}

function Card({ id, title, tag, tone, children }) {
  return (
    <section className={tone ? `card card-${tone}` : 'card'} id={id}>
      <h3>{title}{tag && <small>{tag}</small>}</h3>
      {children}
    </section>
  )
}