import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { SkeletonCards } from "../components/Skeleton";
import type { Patient, Procedure } from "../types";

interface Row extends Procedure {
  patientName: string;
  mrn: string;
  skill: number | null;
  complications: number;
}

export default function Dashboard() {
  const [rows, setRows] = useState<Row[]>([]);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");
  const [surgeon, setSurgeon] = useState("all");
  const [statusF, setStatusF] = useState("all");
  const [skillBand, setSkillBand] = useState("all");
  const [compOnly, setCompOnly] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    (async () => {
      const [procPage, patientPage] = await Promise.all([api.listProcedures(), api.listPatients()]);
      const procs = procPage.items;
      const pmap = new Map<string, Patient>(patientPage.items.map((p) => [p.id, p]));
      const withSkill = await Promise.all(
        procs.map(async (p) => {
          let skill: number | null = null;
          let complications = 0;
          if (p.status === "analyzed") {
            try {
              const [a, detail] = await Promise.all([api.getAnalysis(p.id), api.getProcedure(p.id)]);
              skill = a.skill?.score ?? null;
              complications = detail.outcome?.complications.length ?? 0;
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
            complications,
          };
        })
      );
      setRows(withSkill);
      setLoading(false);
    })();
  }, []);

  const surgeons = Array.from(new Set(rows.map((r) => r.surgeon_name).filter(Boolean)));
  const filtered = rows.filter((r) => {
    if (surgeon !== "all" && r.surgeon_name !== surgeon) return false;
    if (statusF !== "all" && r.status !== statusF) return false;
    if (compOnly && r.complications === 0) return false;
    if (skillBand !== "all" && r.skill != null) {
      if (skillBand === "high" && r.skill < 85) return false;
      if (skillBand === "mid" && (r.skill < 70 || r.skill >= 85)) return false;
      if (skillBand === "low" && r.skill >= 70) return false;
    }
    if (query) {
      const q = query.toLowerCase();
      const hay = `${r.patientName} ${r.mrn} ${r.surgeon_name} ${r.procedure_type}`.toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
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

      <div className="panel" style={{ marginBottom: 16, padding: 12 }}>
        <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
          <input
            placeholder="Search patient, MRN, surgeon…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 2, minWidth: 180 }}
          />
          <select value={surgeon} onChange={(e) => setSurgeon(e.target.value)} style={{ flex: 1, minWidth: 120 }}>
            <option value="all">All surgeons</option>
            {surgeons.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select value={statusF} onChange={(e) => setStatusF(e.target.value)} style={{ width: 130 }}>
            <option value="all">All status</option>
            <option value="analyzed">Analyzed</option>
            <option value="registered">Registered</option>
          </select>
          <select value={skillBand} onChange={(e) => setSkillBand(e.target.value)} style={{ width: 150 }}>
            <option value="all">All skill</option>
            <option value="high">High (≥85)</option>
            <option value="mid">Mid (70–85)</option>
            <option value="low">Low (&lt;70)</option>
          </select>
          <label className="small flex">
            <input type="checkbox" style={{ width: "auto" }} checked={compOnly} onChange={(e) => setCompOnly(e.target.checked)} />
            Complications only
          </label>
        </div>
      </div>

      {loading ? (
        <SkeletonCards />
      ) : (
        <div className="cards">
          {filtered.map((r) => (
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
                {r.complications > 0 && (
                  <span className="sev-high"> · {r.complications} complication{r.complications > 1 ? "s" : ""}</span>
                )}
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
          {filtered.length === 0 && <div className="muted">No procedures match the filters.</div>}
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
