import type { RiskAssessment } from "../types";

export default function RiskPanel({
  risks,
  currentTime,
  onSeek,
}: {
  risks: RiskAssessment[];
  currentTime: number;
  onSeek: (t: number) => void;
}) {
  if (!risks.length) return <div className="muted small">No risk events predicted.</div>;

  // Highest-probability events first; dedupe to most relevant per type+time.
  const sorted = [...risks].sort((a, b) => b.probability - a.probability).slice(0, 8);

  return (
    <div>
      {sorted.map((r, i) => {
        const active = Math.abs(r.t_s - currentTime) < 2.5;
        return (
          <div
            key={i}
            className={`feed-item ${active ? "active" : ""}`}
            style={{ borderLeftColor: `var(--${r.severity})`, cursor: "pointer" }}
            onClick={() => onSeek(r.t_s)}
          >
            <div className="flex" style={{ justifyContent: "space-between" }}>
              <b className={`sev-${r.severity}`}>{r.event_type.replace(/_/g, " ")}</b>
              <span className={`sev-${r.severity}`}>{(r.probability * 100) | 0}%</span>
            </div>
            <div className="t">
              @ {r.t_s.toFixed(1)}s · {r.drivers.join(", ")}
            </div>
          </div>
        );
      })}
    </div>
  );
}
