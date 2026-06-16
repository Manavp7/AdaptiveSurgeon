const SUBSYSTEMS = [
  ["1 · Surgical Data Platform", "Patient → Procedure → Media → Events → Outcome, with object storage.", "live"],
  ["2 · Video Intelligence", "Instrument detection + tracking + motion analytics.", "live"],
  ["3 · Anatomy Understanding", "Segmentation provider (synthetic regions, SAM-ready).", "interface"],
  ["4 · Procedure Timeline", "Phase recognition from video evidence.", "live"],
  ["5 · Skill Engine", "Motion economy, precision, tremor, camera, workflow → score.", "live"],
  ["6 · Surgical Copilot", "Advisory-only, context-aware guidance.", "live"],
  ["7 · Risk Prediction", "Per-phase event probabilities from motion features.", "live"],
  ["8 · Digital Twin + Real Imaging", "Real DICOM PACS viewer (HU/MPR) + 3D twin.", "live"],
  ["9 · Foundation Model", "Case embeddings + similarity search + grounded Q&A.", "live"],
  ["10 · Planning & Simulation", "Approach planning + trajectory safety; sim-only teleop (non-autonomous).", "live"],
];

import { useEffect, useState } from "react";
import { api } from "../api/client";

type ProviderStatus = Record<
  string,
  { configured: string; default: string; real_backend: string; real_available: boolean }
>;

export default function About() {
  const [providers, setProviders] = useState<ProviderStatus>({});
  useEffect(() => {
    api.providers().then(setProviders).catch(() => {});
  }, []);

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
          <h3>Swappable provider interfaces <span className="tag">live capability check</span></h3>
          <p className="muted small">
            Synthetic/heuristic defaults run fully offline. Real models drop in via config with no
            architectural change.
          </p>
          <table>
            <thead>
              <tr><th>Provider</th><th>Active</th><th>Real backend</th></tr>
            </thead>
            <tbody>
              {Object.entries(providers).map(([name, p]) => (
                <tr key={name}>
                  <td>{name}</td>
                  <td>
                    <span className={`badge ${p.configured === p.default ? "registered" : "analyzed"}`}>
                      {p.configured}
                    </span>
                  </td>
                  <td className="small">
                    {p.real_backend}{" "}
                    <span className={p.real_available ? "sev-low" : "muted"}>
                      ({p.real_available ? "available" : "not installed"})
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
