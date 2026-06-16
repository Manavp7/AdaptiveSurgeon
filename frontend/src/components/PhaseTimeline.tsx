import type { PhaseSegment } from "../types";

const PHASE_COLORS: Record<string, string> = {
  access: "#4f8cff",
  exposure: "#21a0d4",
  dissection: "#e0a800",
  clipping: "#e0455e",
  removal: "#a05ce0",
  closure: "#2e9e5b",
};

export default function PhaseTimeline({
  phases,
  duration,
  currentTime,
  onSeek,
}: {
  phases: PhaseSegment[];
  duration: number;
  currentTime: number;
  onSeek: (t: number) => void;
}) {
  if (!phases.length || duration <= 0) return <div className="muted small">No phase timeline.</div>;
  const pct = Math.min(100, (currentTime / duration) * 100);

  return (
    <div>
      <div style={{ position: "relative" }}>
        <div className="timeline">
          {phases.map((p) => {
            const width = ((p.t_end_s - p.t_start_s) / duration) * 100;
            return (
              <div
                key={p.phase}
                className="seg"
                title={`${p.phase} (${p.t_start_s.toFixed(1)}–${p.t_end_s.toFixed(1)}s, conf ${(p.confidence * 100) | 0}%)`}
                style={{ width: `${width}%`, background: PHASE_COLORS[p.phase] || "#555" }}
                onClick={() => onSeek(p.t_start_s)}
              >
                {width > 7 ? p.phase : ""}
              </div>
            );
          })}
        </div>
        <div className="playhead" style={{ left: `${pct}%` }} />
      </div>
      <div className="legend">
        {phases.map((p) => (
          <span key={p.phase}>
            <span className="dot" style={{ background: PHASE_COLORS[p.phase] || "#555" }} />
            {p.phase}
          </span>
        ))}
      </div>
    </div>
  );
}
