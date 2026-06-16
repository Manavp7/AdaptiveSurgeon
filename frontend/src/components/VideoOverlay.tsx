import { useEffect, useRef } from "react";
import type { UnifiedAnalysis } from "../types";

const CLASS_COLORS: Record<string, string> = {
  grasper: "#3c6eff",
  hook: "#22dc55",
  scissors: "#e6e600",
  clip_applier: "#e23ce2",
  needle_holder: "#22e0e0",
};

export default function VideoOverlay({
  src,
  analysis,
  videoRef,
  onTime,
  showTracks,
}: {
  src: string;
  analysis: UnifiedAnalysis;
  videoRef: React.RefObject<HTMLVideoElement>;
  onTime: (t: number) => void;
  showTracks: boolean;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const draw = () => {
      const W = video.clientWidth;
      const H = video.clientHeight;
      if (canvas.width !== W || canvas.height !== H) {
        canvas.width = W;
        canvas.height = H;
      }
      ctx.clearRect(0, 0, W, H);
      const t = video.currentTime;

      // Track paths (faint full polylines).
      if (showTracks) {
        for (const tr of analysis.tracks) {
          const color = CLASS_COLORS[tr.class_name] || "#9fb0d8";
          ctx.strokeStyle = color + "55";
          ctx.lineWidth = 1.5;
          ctx.beginPath();
          tr.points.forEach((p, i) => {
            const x = p[1] * W;
            const y = p[2] * H;
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
          });
          ctx.stroke();
        }
      }

      // Detection boxes near current time (sampled at ~5fps -> 0.2s spacing).
      const win = 0.12;
      for (const d of analysis.detections_sample) {
        if (Math.abs(d.t_s - t) > win) continue;
        const color = CLASS_COLORS[d.class_name] || "#fff";
        const x = d.x * W;
        const y = d.y * H;
        const w = d.w * W;
        const h = d.h * H;
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.strokeRect(x, y, w, h);
        ctx.fillStyle = color;
        ctx.font = "11px Inter, sans-serif";
        const label = `${d.class_name} ${(d.confidence * 100) | 0}%`;
        const tw = ctx.measureText(label).width + 8;
        ctx.fillRect(x, y - 15, tw, 15);
        ctx.fillStyle = "#0b1020";
        ctx.fillText(label, x + 4, y - 4);
      }

      onTime(t);
      rafRef.current = requestAnimationFrame(draw);
    };

    rafRef.current = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(rafRef.current);
  }, [analysis, videoRef, onTime, showTracks]);

  return (
    <div className="video-wrap">
      <video ref={videoRef} src={src} controls playsInline />
      <canvas ref={canvasRef} />
    </div>
  );
}
