import { BarChart } from "./charts";
import type { Track } from "../types";

const CLASS_COLORS: Record<string, string> = {
  grasper: "#3c6eff",
  hook: "#22dc55",
  scissors: "#e6e600",
  clip_applier: "#e23ce2",
  needle_holder: "#22e0e0",
};

export default function TrackAnalytics({ tracks }: { tracks: Track[] }) {
  if (!tracks.length) return <div className="muted small">No instrument tracks.</div>;

  // aggregate per instrument class
  const byClass = new Map<string, { path: number; jerk: number[]; speed: number[] }>();
  for (const t of tracks) {
    const e = byClass.get(t.class_name) || { path: 0, jerk: [], speed: [] };
    e.path += t.path_length_m;
    e.jerk.push(t.jerk);
    e.speed.push(t.mean_speed_cm_s);
    byClass.set(t.class_name, e);
  }
  const classes = [...byClass.entries()];
  const color = (c: string) => CLASS_COLORS[c] || "#9fb0d8";
  const short = (c: string) => c.replace("_applier", "").replace("needle_holder", "needle").slice(0, 8);

  return (
    <div>
      <div className="muted small" style={{ marginBottom: 6 }}>Path length (m) per instrument</div>
      <BarChart
        height={110}
        data={classes.map(([c, e]) => ({ label: short(c), value: Math.round(e.path * 1000) / 1000, color: color(c) }))}
      />
      <div className="muted small" style={{ margin: "14px 0 6px" }}>Tremor proxy (mean jerk) per instrument</div>
      <BarChart
        height={110}
        data={classes.map(([c, e]) => ({
          label: short(c),
          value: Math.round((e.jerk.reduce((a, b) => a + b, 0) / e.jerk.length) * 100) / 100,
          color: color(c),
        }))}
      />
    </div>
  );
}
