import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { api, ApiError } from "../api/client";
import { canWrite, useAuth } from "../auth";
import VideoOverlay from "../components/VideoOverlay";
import PhaseTimeline from "../components/PhaseTimeline";
import SkillScorecard from "../components/SkillScorecard";
import RiskPanel from "../components/RiskPanel";
import CopilotFeed from "../components/CopilotFeed";
import DigitalTwin from "../components/DigitalTwin";
import type { DigitalTwinT, ProcedureDetail as PD, SimilarCase, UnifiedAnalysis } from "../types";

export default function ProcedureDetail() {
  const { id } = useParams<{ id: string }>();
  const { role } = useAuth();
  const nav = useNavigate();
  const videoRef = useRef<HTMLVideoElement>(null);

  const [proc, setProc] = useState<PD | null>(null);
  const [analysis, setAnalysis] = useState<UnifiedAnalysis | null>(null);
  const [twin, setTwin] = useState<DigitalTwinT | null>(null);
  const [similar, setSimilar] = useState<SimilarCase[]>([]);
  const [currentTime, setCurrentTime] = useState(0);
  const [showTracks, setShowTracks] = useState(true);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  const load = useCallback(async () => {
    if (!id) return;
    const p = await api.getProcedure(id);
    setProc(p);
    const a = await api.getAnalysis(id);
    setAnalysis(a);
    try {
      setTwin(await api.getTwin(id));
      setSimilar((await api.similar(id, 5)).results);
    } catch {
      /* twin/similar optional */
    }
  }, [id]);

  useEffect(() => {
    load().catch((e) => setErr(String(e)));
  }, [load]);

  const seek = (t: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = t;
      setCurrentTime(t);
    }
  };

  const runAnalysis = async () => {
    if (!id) return;
    setBusy(true);
    setErr("");
    try {
      await api.analyze(id);
      await load();
    } catch (e) {
      setErr(e instanceof ApiError ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  };

  if (err) return <div className="err">{err}</div>;
  if (!proc || !analysis) return <div className="spinner">Loading case…</div>;

  const video = proc.media.find((m) => m.kind === "video");
  const hasAnalysis = analysis.phases.length > 0;
  const duration = analysis.video_duration_s || video?.duration_s || 0;

  return (
    <div>
      <button onClick={() => nav("/")} style={{ marginBottom: 14 }}>← All procedures</button>
      <div className="flex" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <h1 className="page-title">{proc.patient.display_name}</h1>
          <p className="page-sub">
            {proc.procedure_type.replace(/_/g, " ")} · {proc.surgeon_name} ·{" "}
            {proc.patient.age}{proc.patient.sex} · MRN {proc.patient.external_mrn} ·{" "}
            <span className={`badge ${proc.status}`}>{proc.status}</span>
          </p>
        </div>
        {canWrite(role) && (
          <button className="primary" onClick={runAnalysis} disabled={busy}>
            {busy ? "Processing…" : hasAnalysis ? "Re-run analysis" : "Run analysis"}
          </button>
        )}
      </div>

      {!hasAnalysis && (
        <div className="panel" style={{ marginBottom: 16 }}>
          This procedure has not been analyzed yet.{" "}
          {canWrite(role) ? "Click “Run analysis” to process the video." : "Awaiting analysis."}
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: "1.55fr 1fr" }}>
        {/* LEFT: video + timeline + twin */}
        <div className="flex-col">
          <div className="panel">
            <h3>Surgical Video Intelligence <span className="tag">instrument detection + tracking</span></h3>
            {video && analysis.video_uri ? (
              <>
                <VideoOverlay
                  src={analysis.video_uri}
                  analysis={analysis}
                  videoRef={videoRef}
                  onTime={setCurrentTime}
                  showTracks={showTracks}
                />
                <div className="flex" style={{ marginTop: 8, justifyContent: "space-between" }}>
                  <label className="small flex">
                    <input
                      type="checkbox"
                      checked={showTracks}
                      style={{ width: "auto" }}
                      onChange={(e) => setShowTracks(e.target.checked)}
                    />
                    Show instrument tracks
                  </label>
                  <span className="muted small">
                    {analysis.detection_count} detections · {analysis.tracks.length} tracks ·{" "}
                    t={currentTime.toFixed(1)}s
                  </span>
                </div>
              </>
            ) : (
              <div className="muted">No video uploaded.</div>
            )}
          </div>

          <div className="panel">
            <h3>Procedure Timeline <span className="tag">phase recognition</span></h3>
            <PhaseTimeline
              phases={analysis.phases}
              duration={duration}
              currentTime={currentTime}
              onSeek={seek}
            />
          </div>

          {twin && (
            <div className="panel">
              <h3>Digital Twin <span className="tag">3D anatomy · expected vs actual</span></h3>
              <DigitalTwin structures={twin.structures} />
              <div className="legend">
                <span><span className="dot" style={{ background: "var(--safe)" }} />Safe</span>
                <span><span className="dot" style={{ background: "var(--caution)" }} />Caution</span>
                <span><span className="dot" style={{ background: "var(--critical)" }} />Critical</span>
              </div>
              <div style={{ marginTop: 10 }}>
                <div className="muted small" style={{ marginBottom: 6 }}>Expected vs actual</div>
                {twin.expected_vs_actual.map((d, i) => (
                  <div key={i} className="small" style={{ marginBottom: 4 }}>
                    • <b>{String(d.structure)}</b>: {String(d.detail)}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* RIGHT: skill + risk + copilot + similar */}
        <div className="flex-col">
          <div className="panel">
            <h3>Skill Assessment <span className="tag">motion analytics</span></h3>
            <SkillScorecard skill={analysis.skill} />
          </div>
          <div className="panel">
            <h3>Risk Prediction <span className="tag">advisory</span></h3>
            <RiskPanel risks={analysis.risks} currentTime={currentTime} onSeek={seek} />
          </div>
          <div className="panel">
            <h3>Surgical Copilot <span className="tag">advisory only</span></h3>
            <CopilotFeed advisories={analysis.advisories} currentTime={currentTime} onSeek={seek} />
          </div>
          {similar.length > 0 && (
            <div className="panel">
              <h3>Similar Cases <span className="tag">foundation model</span></h3>
              {similar.map((c) => (
                <div
                  key={c.procedure_id}
                  className="feed-item"
                  style={{ cursor: "pointer" }}
                  onClick={() => nav(`/procedures/${c.procedure_id}`)}
                >
                  <div className="flex" style={{ justifyContent: "space-between" }}>
                    <b>{c.procedure_type.replace(/_/g, " ")}</b>
                    <span className="muted small">{(c.similarity * 100) | 0}% match</span>
                  </div>
                  <div className="t">
                    {c.complications.length
                      ? `Complications: ${c.complications.join(", ")}`
                      : "No complications"}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
