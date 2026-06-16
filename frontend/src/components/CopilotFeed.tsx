import type { Advisory } from "../types";

export default function CopilotFeed({
  advisories,
  currentTime,
  onSeek,
}: {
  advisories: Advisory[];
  currentTime: number;
  onSeek: (t: number) => void;
}) {
  if (!advisories.length) return <div className="muted small">No advisories generated.</div>;
  return (
    <div>
      {advisories.map((a, i) => {
        const active =
          currentTime >= a.t_start_s && (a.t_end_s == null || currentTime <= a.t_end_s);
        return (
          <div
            key={i}
            className={`feed-item ${active ? "active" : ""}`}
            style={{ borderLeftColor: `var(--${a.severity})`, cursor: "pointer" }}
            onClick={() => onSeek(a.t_start_s)}
          >
            <div className={`sev-${a.severity}`} style={{ fontWeight: 600, fontSize: 13 }}>
              {a.label}
            </div>
            <div className="t">
              @ {a.t_start_s.toFixed(1)}s
              {a.payload?.source ? ` · ${String(a.payload.source).replace(/_/g, " ")}` : ""}
            </div>
          </div>
        );
      })}
    </div>
  );
}
