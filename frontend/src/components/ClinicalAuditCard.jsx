import React, { useState, useEffect } from "react";

function parseArtifact(rawText) {
  if (!rawText) return { isTimeline: false, lines: [], summary: "" };

  const rawLines = rawText.split("\n").map((l) => l.trim()).filter(Boolean);
  const events = [];
  const noteLines = [];
  let summary = "";
  let inSummary = false;

  const timeRegex = /^\[(\d{1,2}:\d{2}(?::\d{2})?\s*[A-Za-z]*)\]\s*([^:]+):\s*(.*)$/;

  for (const line of rawLines) {
    if (line.toUpperCase().includes("SECURITY OFFICER AUDIT SUMMARY") || line.toUpperCase().includes("AUDIT SUMMARY:")) {
      inSummary = true;
      continue;
    }
    if (inSummary) {
      summary += " " + line;
      continue;
    }

    const match = line.match(timeRegex);
    if (match) {
      const type = match[2].trim();
      const isConflict = type.includes("CONCURRENT") || line.includes("North Austin") || type.includes("BILLED CLAIM");
      events.push({
        time: match[1].trim(),
        type: type,
        detail: match[3].trim(),
        isConflict: isConflict
      });
    } else {
      if (!line.startsWith("===") && !line.startsWith("---") && !line.includes("PATIENT PRIVILEGED")) {
        noteLines.push(line);
      }
    }
  }

  return {
    isTimeline: events.length > 0,
    events,
    noteLines,
    summary: summary.trim()
  };
}

function getBadgeStyle(type, isConflict) {
  if (isConflict) return { bg: "#fee2e2", text: "#991b1b", border: "#fecaca" };
  if (type.includes("BADGE")) return { bg: "#e0f2fe", text: "#0369a1", border: "#bae6fd" };
  if (type.includes("EHR")) return { bg: "#f3e8ff", text: "#6b21a8", border: "#e9d5ff" };
  if (type.includes("CLINICAL")) return { bg: "#ccfbf1", text: "#0f766e", border: "#99f6e4" };
  if (type.includes("CAFETERIA")) return { bg: "#fef3c7", text: "#92400e", border: "#fde68a" };
  return { bg: "#f1f5f9", text: "#475569", border: "#e2e8f0" };
}

export default function ClinicalAuditCard({ caseId }) {
  const activeId = caseId || "CASE-P209";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!activeId) return;
    setLoading(true);
    fetch(`http://127.0.0.1:8000/api/cases/${activeId}/clinical-audit`)
      .then((r) => (r.ok ? r.json() : null))
      .then((res) => {
        if (res && res.artifact) setData(res);
        setLoading(false);
      })
      .catch(() => {
        fetch(`/api/cases/${activeId}/clinical-audit`)
          .then((r) => (r.ok ? r.json() : null))
          .then((res) => {
            if (res && res.artifact) setData(res);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  }, [activeId]);

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
        Cross-referencing medical record against CMS statutory guidelines...
      </div>
    );
  }

  if (!data || !data.artifact) return null;
  const art = data.artifact;
  const parsed = parseArtifact(art.text_content);

  return (
    <div style={{ marginTop: "18px", borderTop: "1px solid #e2e8f0", paddingTop: "16px" }}>
      {/* 1. Header Bar */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "#334155" }}>
              Clinical Chart & ADR Documentation Audit
            </span>
            <span style={{ background: "#e2e8f0", color: "#475569", fontSize: "10px", fontWeight: "600", padding: "1px 6px", borderRadius: "4px" }}>
              {art.model_auditor !== "template" ? art.model_auditor : "CMS Rules Engine"}
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
          background: art.discrepancy_found ? "#fef2f2" : "#f0fdf4",
          color: art.discrepancy_found ? "#b91c1c" : "#15803d",
          border: art.discrepancy_found ? "1px solid #fecaca" : "1px solid #bbf7d0"
        }}>
          {art.discrepancy_found ? "● Discrepancy Confirmed" : "✓ Records Substantiated"}
        </span>
      </div>

      {/* 2. Structured Content: Timeline OR Clinical Encounter Note */}
      <div style={{
        background: "#ffffff",
        border: "1px solid #e2e8f0",
        borderRadius: "6px",
        overflow: "hidden",
        marginBottom: "12px"
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
            {parsed.isTimeline ? "Chronological Access Trail & EHR Log" : "Clinical Progress Note Transcript"}
          </span>
          <span style={{ fontSize: "10px", color: "#94a3b8" }}>
            {parsed.isTimeline ? `${parsed.events.length} Checkpoints` : "Official Medical Record"}
          </span>
        </div>

        <div style={{ maxHeight: "200px", overflowY: "auto", padding: "8px 12px" }}>
          {parsed.isTimeline ? (
            parsed.events.map((evt, idx) => {
              const style = getBadgeStyle(evt.type, evt.isConflict);
              return (
                <div key={idx} style={{
                  display: "flex",
                  alignItems: "flex-start",
                  gap: "10px",
                  padding: evt.isConflict ? "6px 8px" : "4px 6px",
                  margin: "2px 0",
                  borderRadius: "4px",
                  background: evt.isConflict ? "#fff1f2" : "transparent",
                  border: evt.isConflict ? "1px solid #fecdd3" : "none"
                }}>
                  <span style={{ fontFamily: "ui-monospace, monospace", fontSize: "10.5px", color: evt.isConflict ? "#991b1b" : "#64748b", minWidth: "85px" }}>
                    {evt.time}
                  </span>
                  <span style={{ fontSize: "9px", fontWeight: "700", textTransform: "uppercase", padding: "1px 5px", borderRadius: "3px", background: style.bg, color: style.text, border: `1px solid ${style.border}`, whiteSpace: "nowrap" }}>
                    {evt.isConflict ? "⚠️ CLAIM CONFLICT" : evt.type}
                  </span>
                  <span style={{ fontSize: "11.5px", color: evt.isConflict ? "#7f1d1d" : "#334155", fontWeight: evt.isConflict ? "600" : "400", flex: 1 }}>
                    {evt.detail}
                  </span>
                </div>
              );
            })
          ) : (
            <div style={{ fontFamily: "ui-monospace, monospace", fontSize: "11.5px", lineHeight: "1.6", color: "#334155" }}>
              {parsed.noteLines.map((line, idx) => {
                const isHighlight = line.includes("TIME:") || line.includes("LEVEL") || line.includes("99215") || line.includes("MINUTES") || line.includes("Straightforward");
                return (
                  <div key={idx} style={{
                    padding: isHighlight ? "3px 6px" : "1px 0",
                    background: isHighlight ? "#fffbeb" : "transparent",
                    color: isHighlight ? "#b45309" : "#334155",
                    fontWeight: isHighlight ? "700" : "400",
                    borderRadius: "3px"
                  }}>
                    {line}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* 3. Security Officer Summary (if present) */}
      {parsed.summary && (
        <div style={{
          background: "#f0f9ff",
          border: "1px solid #bae6fd",
          borderLeft: "4px solid #0284c7",
          borderRadius: "6px",
          padding: "10px 14px",
          marginBottom: "12px"
        }}>
          <div style={{ fontSize: "10.5px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.05em", color: "#0369a1", marginBottom: "2px" }}>
            Security Officer Audit Summary · On-Site Verifier
          </div>
          <p style={{ margin: 0, fontSize: "12px", lineHeight: "1.5", color: "#0c4a6e" }}>
            {parsed.summary}
          </p>
        </div>
      )}

      {/* 4. Forensic Finding Callout */}
      <div style={{
        background: art.discrepancy_found ? "#fffbeb" : "#f0fdf4",
        border: art.discrepancy_found ? "1px solid #fef3c7" : "1px solid #dcfce7",
        borderLeft: art.discrepancy_found ? "4px solid #d97706" : "4px solid #16a34a",
        borderRadius: "6px",
        padding: "12px 14px"
      }}>
        <div style={{ fontSize: "10px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.05em", color: art.discrepancy_found ? "#b45309" : "#15803d", marginBottom: "4px" }}>
          Forensic Finding: {art.discrepancy_type}
        </div>
        <p style={{ margin: 0, fontSize: "12px", lineHeight: "1.55", color: "#1e293b" }}>
          {art.finding}
        </p>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: "8px",
          paddingTop: "6px",
          borderTop: art.discrepancy_found ? "1px solid #fde68a" : "1px solid #bbf7d0",
          fontSize: "11px",
          color: "#64748b"
        }}>
          <span><strong>Statutory Basis:</strong> {art.statute}</span>
          <span style={{ fontSize: "10px" }}>Engine: <strong style={{ color: "#0f172a" }}>{art.model_auditor}</strong></span>
        </div>
      </div>
    </div>
  );
}
