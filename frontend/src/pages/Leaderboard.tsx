import { useEffect, useState } from "react";
import { api } from "../api/client";
import { LineChart } from "../components/charts";
import { skillColor } from "./Dashboard";
import type { SurgeonScorecard } from "../types";

export default function Leaderboard() {
  const [rows, setRows] = useState<SurgeonScorecard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.surgeonScorecards().then((r) => {
      setRows(r.surgeons);
      setLoading(false);
    });
  }, []);

  return (
    <div>
      <h1 className="page-title">Surgeon Scorecards</h1>
      <p className="page-sub">
        Objective, measurable skill assessment across cases — the teaching-hospital wedge.
      </p>

      {loading ? (
        <div className="spinner">Loading…</div>
      ) : (
        <div className="cards">
          {rows.map((s, i) => (
            <div key={s.surgeon} className="panel">
              <div className="row flex" style={{ justifyContent: "space-between" }}>
                <b>#{i + 1} {s.surgeon}</b>
                <span className="score-ring" style={{ fontSize: 24, color: skillColor(s.avg_skill) }}>
                  {s.avg_skill ?? "—"}
                </span>
              </div>
              <div className="muted small" style={{ marginBottom: 8 }}>
                {s.cases} cases · {s.analyzed} analyzed · complication rate {s.complication_rate}
              </div>
              {s.trend.length > 1 && (
                <LineChart
                  height={80}
                  yLabel="skill trend"
                  series={[{
                    label: "skill",
                    color: "#21d4a8",
                    points: s.trend.map((t, idx) => [idx, t.score] as [number, number]),
                  }]}
                />
              )}
              <div className="legend">
                {s.procedure_types.map((t) => (
                  <span key={t} className="muted">{t.replace(/_/g, " ")}</span>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
