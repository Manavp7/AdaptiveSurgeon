import type { SkillReport } from "../types";
import { skillColor } from "../pages/Dashboard";

const LABELS: Record<string, string> = {
  motion_economy: "Motion Economy",
  precision: "Precision",
  tremor_control: "Tremor Control",
  camera_stability: "Camera Stability",
  tool_handling: "Tool Handling",
  workflow_adherence: "Workflow Adherence",
};

function barColor(v: number) {
  if (v >= 85) return "var(--safe)";
  if (v >= 70) return "var(--caution)";
  return "var(--critical)";
}

export default function SkillScorecard({ skill }: { skill: SkillReport | null }) {
  if (!skill) return <div className="muted small">No skill assessment.</div>;
  return (
    <div>
      <div className="flex" style={{ justifyContent: "space-between", marginBottom: 14 }}>
        <span className="muted small">Overall</span>
        <span className="score-ring" style={{ color: skillColor(skill.score) }}>
          {skill.score}
          <span className="muted" style={{ fontSize: 14 }}>/100</span>
        </span>
      </div>
      {Object.entries(skill.subscores).map(([k, v]) => (
        <div className="sub-row" key={k}>
          <span className="small">{LABELS[k] || k}</span>
          <div className="bar">
            <div style={{ width: `${v}%`, background: barColor(v) }} />
          </div>
          <span className="small" style={{ textAlign: "right" }}>{v}</span>
        </div>
      ))}
      <div style={{ marginTop: 12 }}>
        <div className="muted small" style={{ marginBottom: 6 }}>Findings</div>
        {skill.findings.map((f, i) => (
          <div key={i} className="small" style={{ marginBottom: 4 }}>• {f}</div>
        ))}
      </div>
    </div>
  );
}
