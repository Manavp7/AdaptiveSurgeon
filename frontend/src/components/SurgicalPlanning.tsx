import { useMemo, useState } from "react";
import { api, ApiError } from "../api/client";
import DigitalTwin from "./DigitalTwin";
import ErrorBoundary from "./ErrorBoundary";
import type { DigitalTwinT, PlanResult } from "../types";

// A few realistic laparoscopic port entry points (scene-space).
const ENTRY_PRESETS: Record<string, number[]> = {
  "Umbilical port": [0.0, 2.2, 1.6],
  "Epigastric port": [0.1, 2.0, -0.3],
  "Right subcostal": [1.4, 1.6, 0.6],
};

function structureCenter(geo: Record<string, unknown>): number[] {
  if (geo.type === "ellipsoid") return geo.center as number[];
  if (geo.type === "cylinder") {
    const f = geo.from as number[];
    const t = geo.to as number[];
    return [(f[0] + t[0]) / 2, (f[1] + t[1]) / 2, (f[2] + t[2]) / 2];
  }
  return [0, 0, 0];
}

export default function SurgicalPlanning({
  procedureId,
  twin,
}: {
  procedureId: string;
  twin: DigitalTwinT;
}) {
  const targets = useMemo(
    () => twin.structures.map((s) => ({ name: s.name, center: structureCenter(s.geometry as Record<string, unknown>) })),
    [twin]
  );
  const [entryName, setEntryName] = useState(Object.keys(ENTRY_PRESETS)[0]);
  const [targetName, setTargetName] = useState(
    targets.find((t) => t.name === "gallbladder")?.name || targets[0]?.name || ""
  );
  const [plan, setPlan] = useState<PlanResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const runPlan = async () => {
    setBusy(true);
    setErr("");
    try {
      const entry = ENTRY_PRESETS[entryName];
      const target = targets.find((t) => t.name === targetName)?.center || [0, 0, 0];
      setPlan(await api.planApproach(procedureId, entry, target));
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <ErrorBoundary fallback={<div className="muted small">3D viewer unavailable.</div>}>
        <DigitalTwin structures={twin.structures} plan={plan ? { trajectory: plan.trajectory, safe: plan.safe } : null} />
      </ErrorBoundary>
      <div className="legend">
        <span><span className="dot" style={{ background: "var(--safe)" }} />Safe</span>
        <span><span className="dot" style={{ background: "var(--caution)" }} />Caution</span>
        <span><span className="dot" style={{ background: "var(--critical)" }} />Critical</span>
        <span><span className="dot" style={{ background: "#4f8cff" }} />Entry port</span>
        <span><span className="dot" style={{ background: "#e0a800" }} />Target</span>
      </div>

      <div className="flex" style={{ gap: 8, marginTop: 12, flexWrap: "wrap" }}>
        <select value={entryName} onChange={(e) => setEntryName(e.target.value)} style={{ width: "auto" }}>
          {Object.keys(ENTRY_PRESETS).map((n) => <option key={n} value={n}>{n}</option>)}
        </select>
        <span className="muted">→</span>
        <select value={targetName} onChange={(e) => setTargetName(e.target.value)} style={{ width: "auto" }}>
          {targets.map((t) => <option key={t.name} value={t.name}>{t.name.replace(/_/g, " ")}</option>)}
        </select>
        <button className="primary" onClick={runPlan} disabled={busy}>{busy ? "Planning…" : "Plan approach"}</button>
      </div>
      {err && <div className="err" style={{ marginTop: 8 }}>{err}</div>}

      {plan && (
        <div style={{ marginTop: 12 }}>
          <div className="flex" style={{ justifyContent: "space-between" }}>
            <span className="muted small">Approach safety</span>
            <span className="score-ring" style={{ fontSize: 22, color: plan.safe ? "var(--safe)" : "var(--critical)" }}>
              {plan.safety_score}<span className="muted" style={{ fontSize: 12 }}>/100</span>
            </span>
          </div>
          {plan.warnings.map((w, i) => (
            <div key={i} className={`feed-item small ${w.startsWith("DANGER") ? "" : ""}`}
              style={{ borderLeftColor: w.startsWith("DANGER") ? "var(--critical)" : w.startsWith("Caution") ? "var(--caution)" : "var(--safe)" }}>
              {w}
            </div>
          ))}
          <table style={{ marginTop: 8 }}>
            <thead><tr><th>Structure</th><th>Criticality</th><th>Clearance</th></tr></thead>
            <tbody>
              {plan.clearances.map((c) => (
                <tr key={c.structure}>
                  <td>{c.structure.replace(/_/g, " ")}</td>
                  <td><span className={`sev-${c.criticality === "critical" ? "critical" : c.criticality === "caution" ? "medium" : "low"}`}>{c.criticality}</span></td>
                  <td className={c.breach ? "sev-critical" : ""}>{c.clearance.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="muted small" style={{ marginTop: 8 }}>{plan.disclaimer}</div>

          {/* Teleoperation — explicitly simulation-only / non-autonomous */}
          <div className="feed-item" style={{ marginTop: 10, borderLeftColor: "var(--caution)" }}>
            <b className="sev-medium">Robotic teleoperation: SIMULATION ONLY</b>
            <div className="small muted" style={{ marginTop: 4 }}>
              The animated probe previews the planned tool path. This build performs
              <b> no autonomous motion</b> and sends no commands to any robot. Real
              integration (e.g. Intuitive/Medtronic) would require hardware, safety
              interlocks, and regulatory clearance.
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
