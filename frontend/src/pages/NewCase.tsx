import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { canWrite, useAuth } from "../auth";

export default function NewCase() {
  const { role } = useAuth();
  const nav = useNavigate();
  const [mrn, setMrn] = useState("");
  const [name, setName] = useState("");
  const [age, setAge] = useState("50");
  const [sex, setSex] = useState("F");
  const [surgeon, setSurgeon] = useState("Dr. New");
  const [procType, setProcType] = useState("laparoscopic_cholecystectomy");
  const [file, setFile] = useState<File | null>(null);
  const [step, setStep] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  if (!canWrite(role)) {
    return (
      <div>
        <h1 className="page-title">New Surgery</h1>
        <div className="panel">Read-only accounts cannot upload surgeries. Sign in as a surgeon.</div>
      </div>
    );
  }

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErr("");
    if (!file) {
      setErr("Please choose a surgery video file.");
      return;
    }
    setBusy(true);
    try {
      setStep("Creating patient…");
      const patient = await api.createPatient({
        external_mrn: mrn || `MRN-${Date.now()}`,
        display_name: name || "New Patient",
        age: parseInt(age) || null,
        sex,
      } as never);

      setStep("Registering procedure…");
      const proc = await api.createProcedure({
        patient_id: patient.id,
        procedure_type: procType,
        surgeon_name: surgeon,
      });

      setStep("Uploading video…");
      await api.uploadMedia(proc.id, file, "video");

      setStep("Running full pipeline (detection → timeline → skill → risk → copilot → twin)…");
      await api.analyzeAndWait(proc.id, (p, m) => setStep(`${m} ${Math.round(p * 100)}%`));

      setStep("Done!");
      nav(`/procedures/${proc.id}`);
    } catch (e2) {
      setErr(e2 instanceof ApiError ? e2.message : String(e2));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">New Surgery</h1>
      <p className="page-sub">
        Upload a surgery → the platform processes the video and generates the full analysis in one
        step.
      </p>
      <form className="panel" style={{ maxWidth: 620 }} onSubmit={submit}>
        <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
          <label className="flex-col">
            <span className="small muted">Patient name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Patient name" />
          </label>
          <label className="flex-col">
            <span className="small muted">MRN (de-identified)</span>
            <input value={mrn} onChange={(e) => setMrn(e.target.value)} placeholder="auto" />
          </label>
          <label className="flex-col">
            <span className="small muted">Age</span>
            <input value={age} onChange={(e) => setAge(e.target.value)} />
          </label>
          <label className="flex-col">
            <span className="small muted">Sex</span>
            <select value={sex} onChange={(e) => setSex(e.target.value)}>
              <option>F</option>
              <option>M</option>
              <option>Other</option>
            </select>
          </label>
          <label className="flex-col">
            <span className="small muted">Surgeon</span>
            <input value={surgeon} onChange={(e) => setSurgeon(e.target.value)} />
          </label>
          <label className="flex-col">
            <span className="small muted">Procedure type</span>
            <input value={procType} onChange={(e) => setProcType(e.target.value)} />
          </label>
        </div>
        <label className="flex-col" style={{ marginTop: 12 }}>
          <span className="small muted">Surgery video (mp4)</span>
          <input type="file" accept="video/*" onChange={(e) => setFile(e.target.files?.[0] || null)} />
        </label>
        <div className="small muted" style={{ marginTop: 8 }}>
          No video handy? The “Seed demo data” script generates synthetic surgeries you can explore
          from the dashboard.
        </div>
        {err && <div className="err" style={{ marginTop: 10 }}>{err}</div>}
        {busy && <div className="muted small" style={{ marginTop: 10 }}>{step}</div>}
        <button className="primary" type="submit" disabled={busy} style={{ marginTop: 14 }}>
          {busy ? "Processing…" : "Upload & analyze"}
        </button>
      </form>
    </div>
  );
}
