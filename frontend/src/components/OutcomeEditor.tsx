import { useState } from "react";
import { api } from "../api/client";
import type { OutcomeT } from "../types";

export default function OutcomeEditor({
  procedureId,
  outcome,
  canEdit,
  onSaved,
}: {
  procedureId: string;
  outcome: OutcomeT | null;
  canEdit: boolean;
  onSaved: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [discharge, setDischarge] = useState(outcome?.discharge_summary ?? "");
  const [complications, setComplications] = useState((outcome?.complications ?? []).join(", "));
  const [los, setLos] = useState(String(outcome?.length_of_stay_days ?? ""));
  const [readmit, setReadmit] = useState(outcome?.readmission_30d ?? false);
  const [mortality, setMortality] = useState(outcome?.mortality ?? false);
  const [busy, setBusy] = useState(false);

  const save = async () => {
    setBusy(true);
    try {
      await api.updateOutcome(procedureId, {
        discharge_summary: discharge,
        complications: complications.split(",").map((s) => s.trim()).filter(Boolean),
        length_of_stay_days: los ? parseFloat(los) : null,
        readmission_30d: readmit,
        mortality,
        notes: outcome?.notes ?? "",
      });
      setEditing(false);
      onSaved();
    } finally {
      setBusy(false);
    }
  };

  if (!editing) {
    return (
      <div>
        {outcome ? (
          <>
            <div className="small" style={{ marginBottom: 6 }}>{outcome.discharge_summary || "—"}</div>
            <div className="small muted">
              Complications: {outcome.complications.length ? outcome.complications.join(", ") : "none"}
              {outcome.length_of_stay_days != null && ` · LOS ${outcome.length_of_stay_days}d`}
              {outcome.readmission_30d && " · readmitted"}
              {outcome.mortality && " · mortality"}
            </div>
          </>
        ) : (
          <div className="muted small">No outcome recorded.</div>
        )}
        {canEdit && (
          <button style={{ marginTop: 10 }} onClick={() => setEditing(true)}>
            Edit outcome
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="flex-col">
      <label className="flex-col">
        <span className="small muted">Discharge summary</span>
        <textarea rows={2} value={discharge} onChange={(e) => setDischarge(e.target.value)} />
      </label>
      <label className="flex-col">
        <span className="small muted">Complications (comma-separated)</span>
        <input value={complications} onChange={(e) => setComplications(e.target.value)} />
      </label>
      <div className="flex">
        <label className="flex-col" style={{ flex: 1 }}>
          <span className="small muted">Length of stay (days)</span>
          <input value={los} onChange={(e) => setLos(e.target.value)} />
        </label>
        <label className="small flex" style={{ marginTop: 18 }}>
          <input type="checkbox" style={{ width: "auto" }} checked={readmit} onChange={(e) => setReadmit(e.target.checked)} />
          Readmit
        </label>
        <label className="small flex" style={{ marginTop: 18 }}>
          <input type="checkbox" style={{ width: "auto" }} checked={mortality} onChange={(e) => setMortality(e.target.checked)} />
          Mortality
        </label>
      </div>
      <div className="flex">
        <button className="primary" disabled={busy} onClick={save}>{busy ? "Saving…" : "Save"}</button>
        <button disabled={busy} onClick={() => setEditing(false)}>Cancel</button>
      </div>
    </div>
  );
}
