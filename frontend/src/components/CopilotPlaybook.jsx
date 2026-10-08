import React, { useState, useEffect } from "react";

export default function CopilotPlaybook({ text, caseId }) {
  // Resolve ID from props or browser hash (#/cases/P209) without external routing packages
  const hashId = typeof window !== "undefined" ? window.location.hash.split("/").pop() : "";
  const activeId = caseId || hashId || "CASE-P209";

  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showSOP, setShowSOP] = useState(false);

  useEffect(() => {
    if (!activeId) return;
    setLoading(true);

    fetch(`http://127.0.0.1:8000/api/cases/${activeId}/audit-plan`)
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => {
        if (data && data.actions) setPlan(data);
        setLoading(false);
      })
      .catch(() => {
        fetch(`/api/cases/${activeId}/audit-plan`)
          .then((r) => (r.ok ? r.json() : null))
          .then((data) => {
            if (data && data.actions) setPlan(data);
            setLoading(false);
          })
          .catch(() => setLoading(false));
      });
  }, [activeId]);

  return (
    <div style={{
      background: "#ffffff",
      border: "1px solid #e2e8f0",
      borderRadius: "8px",
      padding: "16px",
      marginTop: "16px",
      boxShadow: "0 1px 3px rgba(0,0,0,0.02)"
    }}>
      {/* Header with Title and Optimization Metric */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontSize: "11px", fontWeight: "800", textTransform: "uppercase", letterSpacing: "0.06em", color: "#0f172a" }}>
              AuditNext · Adaptive Investigation Plan
            </span>
            <span style={{
              background: "#eff6ff",
              color: "#1d4ed8",
              fontSize: "10px",
              fontWeight: "700",
              padding: "2px 7px",
              borderRadius: "4px",
              border: "1px solid #bfdbfe"
            }}>
              Active Feature Acquisition
            </span>
          </div>
          <div style={{ fontSize: "11.5px", color: "#64748b", marginTop: "3px" }}>
            Objective: <code style={{ color: "#0369a1", fontWeight: "600" }}>max U(a) = E[ΔH] / Cost(a)</code> under limited audit budgets
          </div>
        </div>

        {plan && (
          <div style={{
            background: "#f8fafc",
            border: "1px solid #e2e8f0",
            borderRadius: "6px",
            padding: "4px 10px",
            textAlign: "right"
          }}>
            <div style={{ fontSize: "9.5px", color: "#64748b", textTransform: "uppercase", fontWeight: "700" }}>Prior Ambiguity</div>
            <div style={{ fontSize: "12px", fontWeight: "800", color: "#0f172a" }}>
              H(p) = {plan.prior_entropy_bits} <span style={{ fontSize: "10px", fontWeight: "400", color: "#64748b" }}>bits</span>
            </div>
          </div>
        )}
      </div>

      {/* AuditNext Utility Ranked Actions */}
      {loading ? (
        <div style={{ padding: "14px", fontSize: "11.5px", color: "#64748b", background: "#f8fafc", borderRadius: "6px" }}>
          Computing expected information gain and verification budget trade-offs...
        </div>
      ) : plan && plan.actions ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {plan.actions.map((act, idx) => (
            <div
              key={act.id}
              style={{
                border: act.is_optimal ? "1.5px solid #0284c7" : "1px solid #e2e8f0",
                background: act.is_optimal ? "#f0f9ff" : "#ffffff",
                borderRadius: "6px",
                padding: "10px 12px",
                position: "relative"
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "8px" }}>
                <div style={{ flex: 1 }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "3px" }}>
                    <span style={{
                      width: "18px",
                      height: "18px",
                      borderRadius: "50%",
                      background: act.is_optimal ? "#0284c7" : "#e2e8f0",
                      color: act.is_optimal ? "#ffffff" : "#475569",
                      fontSize: "10.5px",
                      fontWeight: "700",
                      display: "inline-flex",
                      alignItems: "center",
                      justifyContent: "center"
                    }}>
                      {idx + 1}
                    </span>
                    <span style={{ fontSize: "12.5px", fontWeight: "700", color: act.is_optimal ? "#0369a1" : "#1e293b" }}>
                      {act.name}
                    </span>
                    {act.is_optimal && (
                      <span style={{
                        background: "#0284c7",
                        color: "#ffffff",
                        fontSize: "9px",
                        fontWeight: "800",
                        padding: "1px 6px",
                        borderRadius: "3px",
                        textTransform: "uppercase",
                        letterSpacing: "0.04em"
                      }}>
                        Optimal Next Action (Max ROI)
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: "11px", color: "#475569", lineHeight: "1.45" }}>
                    {act.description}
                  </div>
                </div>

                {/* Score Pill Box */}
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  background: act.is_optimal ? "#e0f2fe" : "#f8fafc",
                  padding: "6px 10px",
                  borderRadius: "5px",
                  border: act.is_optimal ? "1px solid #bae6fd" : "1px solid #e2e8f0"
                }}>
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "9px", color: "#64748b", textTransform: "uppercase" }}>Cost</div>
                    <div style={{ fontSize: "11px", fontWeight: "700", color: "#334155" }}>
                      {act.cost_mins}m <span style={{ color: "#94a3b8", fontWeight: "400" }}>(${act.cost_dollars})</span>
                    </div>
                  </div>
                  <div style={{ width: "1px", height: "20px", background: "#cbd5e1" }} />
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "9px", color: "#64748b", textTransform: "uppercase" }}>Info Gain</div>
                    <div style={{ fontSize: "11px", fontWeight: "700", color: "#16a34a" }}>
                      +{act.info_gain_bits} <span style={{ fontSize: "9px" }}>bits</span>
                    </div>
                  </div>
                  <div style={{ width: "1px", height: "20px", background: "#cbd5e1" }} />
                  <div style={{ textAlign: "right" }}>
                    <div style={{ fontSize: "9px", color: act.is_optimal ? "#0369a1" : "#64748b", textTransform: "uppercase", fontWeight: "700" }}>U(a)</div>
                    <div style={{ fontSize: "12px", fontWeight: "800", color: act.is_optimal ? "#0369a1" : "#0f172a" }}>
                      {act.utility_score}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {/* Collapsible Rulebook / Compliance SOP Section */}
      <div style={{ marginTop: "12px", borderTop: "1px solid #f1f5f9", paddingTop: "8px" }}>
        <button
          onClick={() => setShowSOP(!showSOP)}
          style={{
            background: "none",
            border: "none",
            padding: 0,
            color: "#64748b",
            fontSize: "11px",
            cursor: "pointer",
            fontWeight: "600",
            display: "flex",
            alignItems: "center",
            gap: "4px"
          }}
        >
          {showSOP ? "▾ Hide standard statutory compliance checklist" : "▸ View standard statutory compliance checklist"}
        </button>

        {showSOP && text && (
          <div style={{
            marginTop: "8px",
            padding: "10px 12px",
            background: "#f8fafc",
            borderRadius: "6px",
            fontSize: "11.5px",
            color: "#334155",
            lineHeight: "1.55",
            whiteSpace: "pre-wrap",
            border: "1px solid #e2e8f0"
          }}>
            {text}
          </div>
        )}
      </div>
    </div>
  );
}
