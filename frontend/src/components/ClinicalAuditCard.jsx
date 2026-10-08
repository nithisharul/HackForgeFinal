import React, { useState, useEffect } from "react";

export default function ClinicalAuditCard({ caseId }) {
  const activeId = caseId || "CASE-P209";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showFullLogs, setShowFullLogs] = useState(false);

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
        Running forensic chart cross-reference with Llama 3.2 RAG...
      </div>
    );
  }

  if (!data || !data.artifact) return null;
  const art = data.artifact;

  // Split lines to detect and highlight the conflicting claim encounter
  const logLines = (art.text_content || "").split("\n");

  return (
    <div style={{
      marginTop: "18px",
      borderTop: "1px solid #e2e8f0",
      paddingTop: "16px"
    }}>
      {/* Header bar */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.06em", color: "#475569" }}>
              Clinical Chart & ADR Audit
            </span>
            <span style={{
              background: "#f1f5f9",
              color: "#475569",
              fontSize: "10px",
              fontWeight: "600",
              padding: "1px 6px",
              borderRadius: "4px"
            }}>
              RAG Engine
            </span>
          </div>
          <div style={{ fontSize: "11px", color: "#64748b", marginTop: "2px" }}>
            Record: <strong style={{ color: "#334155" }}>{data.source_file}</strong> · DOS: {art.date_of_service}
          </div>
        </div>

        <span style={{
          padding: "3px 10px",
          borderRadius: "12px",
          fontSize: "11px",
          fontWeight: "600",
          background: art.discrepancy_found ? "#fef2f2" : "#f0fdf4",
          color: art.discrepancy_found ? "#b91c1c" : "#15803d",
          border: art.discrepancy_found ? "1px solid #fecaca" : "1px solid #bbf7d0",
          display: "inline-flex",
          alignItems: "center",
          gap: "5px"
        }}>
          {art.discrepancy_found ? "● Discrepancy Flagged" : "✓ Records Substantiated"}
        </span>
      </div>

      {/* Llama 3.2 Finding Callout - styled like the Primary Directive */}
      <div style={{
        background: art.discrepancy_found ? "#fffbeb" : "#f0fdf4",
        border: art.discrepancy_found ? "1px solid #fef3c7" : "1px solid #dcfce7",
        borderLeft: art.discrepancy_found ? "4px solid #d97706" : "4px solid #16a34a",
        borderRadius: "6px",
        padding: "12px 14px",
        marginBottom: "12px"
      }}>
        <div style={{
          fontSize: "10px",
          fontWeight: "800",
          textTransform: "uppercase",
          letterSpacing: "0.05em",
          color: art.discrepancy_found ? "#b45309" : "#15803d",
          marginBottom: "4px"
        }}>
          {art.discrepancy_type}
        </div>
        <p style={{ margin: 0, fontSize: "12px", lineHeight: "1.55", color: "#1e293b" }}>
          {art.finding}
        </p>
        <div style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginTop: "8px",
          paddingTop: "6px",
          borderTop: art.discrepancy_found ? "1px solid #fde68a" : "1px solid #bbf7d0",
          fontSize: "10px",
          color: "#64748b"
        }}>
          <span><strong>Statutory Basis:</strong> {art.statute}</span>
          <span>Audited by <strong style={{ color: "#0f172a" }}>{art.model_auditor}</strong></span>
        </div>
      </div>

      {/* Forensic Log Excerpt - Clean Light Canvas */}
      <div style={{
        background: "#f8fafc",
        border: "1px solid #e2e8f0",
        borderRadius: "6px",
        padding: "10px 12px"
      }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "6px" }}>
          <span style={{ fontSize: "10px", fontWeight: "700", textTransform: "uppercase", letterSpacing: "0.04em", color: "#64748b" }}>
            Physical Badge & EHR Access Trail
          </span>
          <button
            onClick={() => setShowFullLogs(!showFullLogs)}
            style={{
              background: "none",
              border: "none",
              color: "#2563eb",
              fontSize: "11px",
              cursor: "pointer",
              padding: 0,
              fontWeight: "600"
            }}
          >
            {showFullLogs ? "Collapse log" : "View complete log"}
          </button>
        </div>

        <div style={{
          fontFamily: "ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace",
          fontSize: "11px",
          lineHeight: "1.6",
          color: "#334155",
          maxHeight: showFullLogs ? "320px" : "140px",
          overflowY: "auto",
          paddingRight: "4px"
        }}>
          {logLines.map((line, idx) => {
            const isConflict = line.includes("CONCURRENT BILLED CLAIM") || line.includes("North Austin");
            return (
              <div
                key={idx}
                style={{
                  padding: isConflict ? "3px 6px" : "1px 0",
                  margin: isConflict ? "3px 0" : "0",
                  background: isConflict ? "#fef2f2" : "transparent",
                  color: isConflict ? "#b91c1c" : "#334155",
                  fontWeight: isConflict ? "700" : "400",
                  borderRadius: isConflict ? "4px" : "0",
                  borderLeft: isConflict ? "3px solid #ef4444" : "none"
                }}
              >
                {line}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
