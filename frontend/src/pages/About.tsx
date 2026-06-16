const SUBSYSTEMS = [
  ["1 · Surgical Data Platform", "Patient → Procedure → Media → Events → Outcome, with object storage.", "live"],
  ["2 · Video Intelligence", "Instrument detection + tracking + motion analytics.", "live"],
  ["3 · Anatomy Understanding", "Segmentation provider (synthetic regions, SAM-ready).", "interface"],
  ["4 · Procedure Timeline", "Phase recognition from video evidence.", "live"],
  ["5 · Skill Engine", "Motion economy, precision, tremor, camera, workflow → score.", "live"],
  ["6 · Surgical Copilot", "Advisory-only, context-aware guidance.", "live"],
  ["7 · Risk Prediction", "Per-phase event probabilities from motion features.", "live"],
  ["8 · Digital Twin", "3D anatomy + expected-vs-actual comparison.", "live"],
  ["9 · Foundation Model", "Case embeddings + similarity search + grounded Q&A.", "live"],
  ["10 · Autonomous Assistance", "Smart camera / navigation / robotics.", "roadmap"],
];

const PROVIDERS = [
  "InstrumentDetectionProvider (synthetic → YOLO)",
  "AnatomySegmentationProvider (synthetic → SAM)",
  "ProcedurePhaseProvider (heuristic → temporal model)",
  "RiskAssessmentProvider (rules → trained model)",
  "CopilotProvider (rules → LLM)",
  "EmbeddingProvider (hashing → sentence-transformer)",
];

export default function About() {
  return (
    <div>
      <h1 className="page-title">Architecture</h1>
      <p className="page-sub">
        A coherent Surgical Intelligence OS — every subsystem connected through one workflow.
      </p>

      <div className="panel" style={{ marginBottom: 16 }}>
        <h3>The connected workflow</h3>
        <div className="small" style={{ lineHeight: 2 }}>
          Upload surgery → process video → instruments detected/tracked → procedure timeline →
          skill metrics → risk events → copilot advisories → digital twin → unified dashboard.
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", marginBottom: 16 }}>
        <div className="panel">
          <h3>Subsystems</h3>
          <table>
            <tbody>
              {SUBSYSTEMS.map(([n, d, s]) => (
                <tr key={n}>
                  <td><b>{n}</b><div className="muted small">{d}</div></td>
                  <td style={{ width: 90 }}>
                    <span className={`badge ${s === "live" ? "analyzed" : "registered"}`}>{s}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="panel">
          <h3>Swappable provider interfaces</h3>
          <p className="muted small">
            Synthetic/heuristic defaults run fully offline. Real models drop in via config with no
            architectural change.
          </p>
          {PROVIDERS.map((p) => (
            <div key={p} className="feed-item small">{p}</div>
          ))}
        </div>
      </div>
    </div>
  );
}
