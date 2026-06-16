import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { Patient, Procedure } from "../types";

interface Row extends Procedure {
  patientName: string;
  mrn: string;
  skill: number | null;
}

export default function Dashboard() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    (async () => {
      const [procs, patients] = await Promise.all([api.listProcedures(), api.listPatients()]);
      const pmap = new Map<string, Patient>(patients.map((p) => [p.id, p]));
      const withSkill = await Promise.all(
        procs.map(async (p) => {
          let skill: number | null = null;
          if (p.status === "analyzed") {
            try {
              const a = await api.getAnalysis(p.id);
              skill = a.skill?.score ?? null;
            } catch {
              /* ignore */
            }
          }
          const pat = pmap.get(p.patient_id);
          return {
            ...p,
            patientName: pat?.display_name ?? "Unknown",
            mrn: pat?.external_mrn ?? "",
            skill,
          };
        })
      );
      setRows(withSkill);
      setLoading(false);
    })();
  }, []);

  const analyzed = rows.filter((r) => r.status === "analyzed");
  const avgSkill =
    analyzed.length > 0
      ? Math.round((analyzed.reduce((s, r) => s + (r.skill ?? 0), 0) / analyzed.length) * 10) / 10
      : 0;

  return (
    <div>
      <h1 className="page-title">Surgical Operations</h1>
      <p className="page-sub">
        Every case flows through one pipeline: video → instruments → timeline → skill → risk →
        copilot → digital twin.
      </p>

      <div className="kpi" style={{ marginBottom: 18 }}>
        <div className="item">
          <div className="v">{rows.length}</div>
          <div className="l">Procedures</div>
        </div>
        <div className="item">
          <div className="v">{analyzed.length}</div>
          <div className="l">Analyzed</div>
        </div>
        <div className="item">
          <div className="v">{avgSkill || "—"}</div>
          <div className="l">Avg skill score</div>
        </div>
      </div>

      {loading ? (
        <div className="spinner">Loading procedures…</div>
      ) : (
        <div className="cards">
          {rows.map((r) => (
            <div key={r.id} className="card" onClick={() => nav(`/procedures/${r.id}`)}>
              <div className="row">
                <b>{r.patientName}</b>
                <span className={`badge ${r.status}`}>{r.status}</span>
              </div>
              <div className="muted small" style={{ marginTop: 4 }}>
                {r.procedure_type.replace(/_/g, " ")}
              </div>
              <div className="muted small">
                {r.mrn} · {r.surgeon_name || r.surgeon_id}
              </div>
              <div className="row" style={{ marginTop: 12 }}>
                <span className="muted small">Skill score</span>
                <span
                  className="score-ring"
                  style={{ fontSize: 24, color: skillColor(r.skill) }}
                >
                  {r.skill != null ? r.skill : "—"}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export function skillColor(score: number | null): string {
  if (score == null) return "var(--text-dim)";
  if (score >= 85) return "var(--safe)";
  if (score >= 70) return "var(--caution)";
  return "var(--critical)";
}
