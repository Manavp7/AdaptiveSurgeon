import { LineChart } from "./charts";
import type { VitalPoint } from "../types";

export default function VitalsPanel({
  series,
  currentTime,
}: {
  series: VitalPoint[];
  currentTime: number;
}) {
  if (!series.length) return <div className="muted small">No vitals recorded.</div>;

  const hr = series.map((p) => [p.t, p.hr] as [number, number]);
  const bpSys = series.map((p) => [p.t, p.bp_sys] as [number, number]);
  const bpDia = series.map((p) => [p.t, p.bp_dia] as [number, number]);
  const spo2 = series.map((p) => [p.t, p.spo2] as [number, number]);

  // nearest sample to playhead for the live readout
  const cur = series.reduce((a, b) => (Math.abs(b.t - currentTime) < Math.abs(a.t - currentTime) ? b : a));

  return (
    <div>
      <div className="kpi" style={{ marginBottom: 10 }}>
        <div className="item"><div className="v" style={{ color: "var(--critical)" }}>{cur.hr}</div><div className="l">HR bpm</div></div>
        <div className="item"><div className="v">{cur.bp_sys}/{cur.bp_dia}</div><div className="l">BP mmHg</div></div>
        <div className="item"><div className="v" style={{ color: "var(--accent-2)" }}>{cur.spo2}%</div><div className="l">SpO₂</div></div>
      </div>
      <LineChart
        height={120}
        playheadX={currentTime}
        yLabel="HR / BP"
        series={[
          { label: "HR", color: "#e0455e", points: hr },
          { label: "BP sys", color: "#4f8cff", points: bpSys },
          { label: "BP dia", color: "#21a0d4", points: bpDia },
        ]}
      />
      <LineChart
        height={70}
        playheadX={currentTime}
        yLabel="SpO₂"
        series={[{ label: "SpO₂", color: "#21d4a8", points: spo2 }]}
      />
    </div>
  );
}
