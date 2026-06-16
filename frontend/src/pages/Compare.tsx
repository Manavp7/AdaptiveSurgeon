import { useCallback, useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import VideoOverlay from "../components/VideoOverlay";
import PhaseTimeline from "../components/PhaseTimeline";
import SkillScorecard from "../components/SkillScorecard";
import RiskPanel from "../components/RiskPanel";
import type { Procedure, UnifiedAnalysis } from "../types";

function Side({
  analysis,
  videoRef,
  label,
  onTime,
}: {
  analysis: UnifiedAnalysis;
  videoRef: React.RefObject<HTMLVideoElement>;
  label: string;
  onTime: (t: number) => void;
}) {
  const [t, setT] = useState(0);
  const dur = analysis.video_duration_s || 0;
  return (
    <div className="flex-col">
      <div className="panel">
        <h3>{label}</h3>
        {analysis.video_uri && (
          <VideoOverlay
            src={analysis.video_uri}
            analysis={analysis}
            videoRef={videoRef}
            onTime={(x) => { setT(x); onTime(x); }}
            showTracks
            showAnatomy
          />
        )}
        <div style={{ marginTop: 8 }}>
          <PhaseTimeline phases={analysis.phases} duration={dur} currentTime={t}
            onSeek={(s) => { if (videoRef.current) videoRef.current.currentTime = s; }} />
        </div>
      </div>
      <div className="panel">
        <h3>Skill <span className="tag">{analysis.skill?.score ?? "—"}/100</span></h3>
        <SkillScorecard skill={analysis.skill} />
      </div>
      <div className="panel">
        <h3>Risk</h3>
        <RiskPanel risks={analysis.risks} currentTime={t}
          onSeek={(s) => { if (videoRef.current) videoRef.current.currentTime = s; }} />
      </div>
    </div>
  );
}

export default function Compare() {
  const [params, setParams] = useSearchParams();
  const [procs, setProcs] = useState<Procedure[]>([]);
  const [aId, setAId] = useState(params.get("a") || "");
  const [bId, setBId] = useState(params.get("b") || "");
  const [aAnalysis, setAAnalysis] = useState<UnifiedAnalysis | null>(null);
  const [bAnalysis, setBAnalysis] = useState<UnifiedAnalysis | null>(null);
  const aRef = useRef<HTMLVideoElement>(null);
  const bRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    api.listProcedures().then((p) => {
      const items = p.items.filter((x) => x.status === "analyzed");
      setProcs(items);
      if (!aId && items[0]) setAId(items[0].id);
      if (!bId && items[1]) setBId(items[1].id);
    });
  }, []);

  const loadBoth = useCallback(async () => {
    if (aId) setAAnalysis(await api.getAnalysis(aId));
    if (bId) setBAnalysis(await api.getAnalysis(bId));
    const next = new URLSearchParams();
    if (aId) next.set("a", aId);
    if (bId) next.set("b", bId);
    setParams(next, { replace: true });
  }, [aId, bId, setParams]);

  useEffect(() => {
    loadBoth();
  }, [loadBoth]);

  const scrub = (t: number) => {
    if (aRef.current) aRef.current.currentTime = t;
    if (bRef.current) bRef.current.currentTime = t;
  };
  const playBoth = () => {
    aRef.current?.play();
    bRef.current?.play();
  };
  const pauseBoth = () => {
    aRef.current?.pause();
    bRef.current?.pause();
  };

  const label = (id: string) => {
    const p = procs.find((x) => x.id === id);
    return p ? `${p.surgeon_name} · ${p.procedure_type.replace(/_/g, " ")}` : id;
  };
  const maxDur = Math.max(aAnalysis?.video_duration_s || 0, bAnalysis?.video_duration_s || 0);

  return (
    <div>
      <h1 className="page-title">Compare Cases</h1>
      <p className="page-sub">Side-by-side comparison with a shared, synchronized scrubber.</p>

      <div className="panel" style={{ marginBottom: 16, padding: 12 }}>
        <div className="flex" style={{ gap: 10, flexWrap: "wrap" }}>
          <select value={aId} onChange={(e) => setAId(e.target.value)} style={{ flex: 1 }}>
            {procs.map((p) => <option key={p.id} value={p.id}>{label(p.id)}</option>)}
          </select>
          <span className="muted">vs</span>
          <select value={bId} onChange={(e) => setBId(e.target.value)} style={{ flex: 1 }}>
            {procs.map((p) => <option key={p.id} value={p.id}>{label(p.id)}</option>)}
          </select>
        </div>
        <div className="flex" style={{ marginTop: 10, gap: 10 }}>
          <button onClick={playBoth}>▶ Play both</button>
          <button onClick={pauseBoth}>⏸ Pause</button>
          <input type="range" min={0} max={maxDur} step={0.1} defaultValue={0}
            onChange={(e) => scrub(parseFloat(e.target.value))} style={{ flex: 1 }} />
        </div>
      </div>

      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr" }}>
        {aAnalysis && <Side analysis={aAnalysis} videoRef={aRef} label={label(aId)} onTime={() => {}} />}
        {bAnalysis && <Side analysis={bAnalysis} videoRef={bRef} label={label(bId)} onTime={() => {}} />}
      </div>
    </div>
  );
}
