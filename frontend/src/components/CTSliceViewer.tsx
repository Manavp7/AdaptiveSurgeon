import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";

interface Vol {
  depth: number;
  height: number;
  width: number;
  data: Uint8Array;
}

function decode(b64: string): Uint8Array {
  const bin = atob(b64);
  const arr = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) arr[i] = bin.charCodeAt(i);
  return arr;
}

export default function CTSliceViewer({ procedureId }: { procedureId: string }) {
  const [vol, setVol] = useState<Vol | null>(null);
  const [z, setZ] = useState(0);
  const [err, setErr] = useState("");
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    api
      .getTwinVolume(procedureId)
      .then((v) => {
        setVol({ depth: v.depth, height: v.height, width: v.width, data: decode(v.data_b64) });
        setZ(Math.floor(v.depth / 2));
      })
      .catch((e) => setErr(String(e)));
  }, [procedureId]);

  const sliceSize = useMemo(() => (vol ? vol.width * vol.height : 0), [vol]);

  useEffect(() => {
    if (!vol) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    canvas.width = vol.width;
    canvas.height = vol.height;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const img = ctx.createImageData(vol.width, vol.height);
    const off = z * sliceSize;
    for (let i = 0; i < sliceSize; i++) {
      const v = vol.data[off + i];
      img.data[i * 4] = v;
      img.data[i * 4 + 1] = v;
      img.data[i * 4 + 2] = v;
      img.data[i * 4 + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  }, [vol, z, sliceSize]);

  if (err) return <div className="muted small">CT volume unavailable.</div>;
  if (!vol) return <div className="muted small">Loading CT volume…</div>;

  return (
    <div>
      <canvas
        ref={canvasRef}
        style={{ width: "100%", imageRendering: "pixelated", borderRadius: 8, background: "#000", border: "1px solid var(--border)" }}
      />
      <div className="flex" style={{ marginTop: 8 }}>
        <span className="muted small">Axial slice {z + 1}/{vol.depth}</span>
        <input type="range" min={0} max={vol.depth - 1} value={z} onChange={(e) => setZ(parseInt(e.target.value))} style={{ flex: 1 }} />
      </div>
    </div>
  );
}
