import React, { useState, useEffect } from "react";

function parseLogData(rawText) {
  if (!rawText) return { header: [], events: [], summary: "" };

  const lines = rawText.split("\n").map((l) => l.trim()).filter(Boolean);
  const header = [];
  const events = [];
  let summaryLines = [];
  let inSummary = false;

  const timeRegex = /^\[(\d{1,2}:\d{2}(?::\d{2})?\s*[A-Za-z]*)\]\s*([^:]+):\s*(.*)$/;

  for (const line of lines) {
    if (line.toUpperCase().includes("SECURITY OFFICER AUDIT SUMMARY") || line.toUpperCase().includes("AUDIT SUMMARY:")) {
      inSummary = true;
      continue;
    }

    if (inSummary) {
      summaryLines.push(line);
      continue;
    }

    const match = line.match(timeRegex);
    if (match) {
      const type = match[2].trim();
      const isConflict =
        type.includes("CONCURRENT") ||
        type.includes("BILLED CLAIM");

      events.push({
        time: match[1].trim(),
        type: type,
        detail: match[3].trim(),
        isConflict: isConflict
      });
    } else if (events.length === 0) {
      if (!line.startsWith("===") && !line.startsWith("---") && !line.includes("PATIENT PRIVILEGED")) {
        header.push(line);
      }
    } else {
      events.push({
        time: "LOG",
        type: "NOTE",
        detail: line,
        isConflict: false
      });
    }
  }

  return {
    header,
    events,
    summary: summaryLines.join(" ")
  };
}

function getBadgeStyle(type, isConflict) {
  if (isConflict) {
    return { bg: "#fee2e2", text: "#991b1b", border: "#fecaca" };
  }
  if (type.includes("BADGE")) {
    return { bg: "#e0f2fe", text: "#0369a1", border: "#bae6fd" };
  }
  if (type.includes("EHR")) {
    return { bg: "#f3e8ff", text: "#6b21a8", border: "#e9d5ff" };
  }
  if (type.includes("CLINICAL")) {
    return { bg: "#ccfbf1", text: "#0f766e", border: "#99f6e4" };
  }
  if (type.includes("CAFETERIA")) {
    return { bg: "#fef3c7", text: "#92400e", border: "#fde68a" };
  }
  return { bg: "#f1f5f9", text: "#475569", border: "#e2e8f0" };
}

export default function ClinicalAuditCard({ caseId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!caseId) return;
    let live = true;
    setLoading(true);
    setData(null);
    fetch(`/api/cases/${caseId}/clinical-audit`)
      .then((r) => (r.ok ? r.json() : null))
      .then((res) => { if (live) { setData(res); setLoading(false); } })
      .catch(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, [caseId]);

  if (loading) {
    return (
      <div style={{
        marginTop: "16px",
        padding: "16px",
        background: "#f8fafc",
        border: "1px dashed #cbd5e1",
        borderRadius: "8px",
        display: "flex",
        alignItems: "center",
        gap: "10px",
        color: "#64748b",
        fontSize: "12px"
      }}>
        <div style={{
          width: "14px",
          height: "14px",
          border: "2px solid #94a3b8",
          borderTopColor: "transparent",
          borderRadius: "50%",
          animation: "spin 1s linear infinite"
        }} />
        Checking for a provider record on this case...
      </div>
    );
  }

  if (!data) return null;
  if (!data.artifact) {
    return (
      <p style={{ marginTop: "16px", paddingTop: "12px", borderTop: "1px solid #e2e8f0", fontSize: "12px", color: "#64748b" }}>
        <strong>Provider record review:</strong> no record has been received for this case yet.
      </p>
    );
  }
  const art = data.artifact;
  const read = data.status === "read";
  const tone = !read ? "none" : art.discrepancy_found ? "flag" : "ok";
  const badge = {
    none: { label: "Not read by the LLM · review manually", bg: "#f1f5f9", fg: "#475569", bd: "#e2e8f0" },
    flag: { label: "● Possible discrepancy · needs investigator review", bg: "#fef2f2", fg: "#b91c1c", bd: "#fecaca" },
    ok: { label: "No discrepancy found by the LLM · still review", bg: "#f0fdf4", fg: "#15803d", bd: "#bbf7d0" },
  }[tone];
  const parsed = parseLogData(art.text_content);

  return (
    <div style={{
      marginTop: "18px",
      borderTop: "1px solid #e2e8f0",
      paddingTop: "16px"
    }}>
      {/* 1. Header Bar */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "#334155" }}>
              Provider record review
            </span>
            <span style={{
              background: "#e2e8f0",
              color: "#475569",
              fontSize: "10px",
              fontWeight: "600",
              padding: "1px 6px",
              borderRadius: "4px"
            }}>
              {read ? `LLM: ${art.model_auditor}` : "Synthetic sample record"}
            </span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
            Source: <strong style={{ color: "#334155" }}>{art.author}</strong> · DOS: {art.date_of_service} · File: {data.source_file}
          </div>
        </div>

        <span style={{
          padding: "3px 10px",
          borderRadius: "12px",
          fontSize: "11px",
          fontWeight: "600",
          background: badge.bg,
          color: badge.fg,
          border: `1px solid ${badge.bd}`,
          display: "inline-flex",
          alignItems: "center",
          gap: "5px"
        }}>
          {badge.label}
        </span>
      </div>

      {/* 2. Structured Forensic Audit Timeline */}
      <div style={{
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "6px",
        overflow: "hidden",
        marginBottom: "12px",
        boxShadow: "0 1px 2px rgba(0,0,0,0.03)"
      }}>
        <div style={{
          padding: "8px 12px",
          background: "#f8fafc",
          borderBottom: "1px solid #e2e8f0",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between"
        }}>
          <span style={{ fontSize: "10px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.05em", color: "#475569" }}>
            Record as received (synthetic sample)
          </span>
          <span style={{ fontSize: "10px", color: "#94a3b8" }}>
            {parsed.events.length} Recorded Checkpoints
          </span>
        </div>

        <div style={{ maxHeight: "220px", overflowY: "auto", padding: "6px 8px" }}>
          {parsed.events.map((evt, idx) => {
            const style = getBadgeStyle(evt.type, evt.isConflict);
            return (
              <div
                key={idx}
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "10px",
                  padding: evt.isConflict ? "8px 10px" : "5px 8px",
                  margin: "2px 0",
                  borderRadius: "5px",
                  background: evt.isConflict ? "#fff1f2" : "transparent",
                  border: evt.isConflict ? "1px solid #fecdd3" : "1px solid transparent",
                  transition: "background 0.15s ease"
                }}
              >
                {/* Monospace Timestamp */}
                <span style={{
                  fontFamily: "ui-monospace, monospace",
                  fontSize: "10.5px",
                  fontWeight: "600",
                  color: evt.isConflict ? "#991b1b" : "#64748b",
                  minWidth: "90px",
                  paddingTop: "1px"
                }}>
                  {evt.time}
                </span>

                {/* Event Category Badge */}
                <span style={{
                  fontSize: "9.5px",
                  fontWeight: "700",
                  textTransform: "uppercase",
                  letterSpacing: "0.03em",
                  padding: "2px 6px",
                  borderRadius: "4px",
                  background: style.bg,
                  color: style.text,
                  border: `1px solid ${style.border}`,
                  whiteSpace: "nowrap"
                }}>
                  {evt.isConflict ? "⚠️ CLAIM CONFLICT" : evt.type}
                </span>

                {/* Event Description */}
                <span style={{
                  fontSize: "11.5px",
                  color: evt.isConflict ? "#7f1d1d" : "#334155",
                  fontWeight: evt.isConflict ? "600" : "400",
                  lineHeight: "1.45",
                  flex: 1
                }}>
                  {evt.detail}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* 3. Differentiated Security Officer Audit Summary */}
      {parsed.summary && (
        <div style={{
          background: "#f0f9ff",
          border: "1px solid #bae6fd",
          borderLeft: "4px solid #0284c7",
          borderRadius: "6px",
          padding: "10px 14px",
          marginBottom: "12px"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "6px", marginBottom: "3px" }}>
            <span style={{ fontSize: "10.5px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.05em", color: "#0369a1" }}>
              Summary written on the record
            </span>
          </div>
          <p style={{ margin: 0, fontSize: "12px", lineHeight: "1.5", color: "#0c4a6e" }}>
            {parsed.summary}
          </p>
        </div>
      )}

      {/* 4. LLM reading */}
      <div style={{
        background: tone === "flag" ? "#fffbeb" : tone === "ok" ? "#f0fdf4" : "#f8fafc",
        border: "1px solid #e2e8f0",
        borderLeft: `4px solid ${tone === "flag" ? "#d97706" : tone === "ok" ? "#16a34a" : "#94a3b8"}`,
        borderRadius: "6px",
        padding: "12px 14px"
      }}>
        <div style={{ fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.05em", color: "#475569", marginBottom: "4px" }}>
          {read ? `LLM reading${art.discrepancy_type ? `: ${art.discrepancy_type}` : ""}` : "LLM reading unavailable"}
        </div>
        <p style={{ margin: 0, fontSize: "12px", lineHeight: "1.55", color: "#1e293b" }}>
          {read ? art.finding : data.message}
        </p>
        <div style={{ marginTop: "8px", paddingTop: "6px", borderTop: "1px solid #e2e8f0", fontSize: "10px", color: "#64748b" }}>
          {read && <>A lead for review, not a finding. The investigator decides. </>}
          <strong>Background:</strong> {art.statute}
        </div>
      </div>
    </div>
  );
}
