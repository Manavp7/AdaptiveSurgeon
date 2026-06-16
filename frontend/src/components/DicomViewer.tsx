import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "../api/client";
import type { DicomVolume, ImagingStudy } from "../types";

type Plane = "axial" | "coronal" | "sagittal";

interface Vol {
  meta: DicomVolume;
  data: Int16Array;
}

function decodeInt16(b64: string): Int16Array {
  const bin = atob(b64);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
  return new Int16Array(bytes.buffer);
}

/** Dimensions of a given MPR plane: [width, height, numSlices]. */
function planeDims(m: DicomVolume, plane: Plane): [number, number, number] {
  if (plane === "axial") return [m.cols, m.rows, m.depth];
  if (plane === "coronal") return [m.cols, m.depth, m.rows];
  return [m.rows, m.depth, m.cols]; // sagittal
}

/** Read a voxel value for a plane at (slice, px, py). */
function voxel(vol: Vol, plane: Plane, slice: number, px: number, py: number): number {
  const { rows, cols } = vol.meta;
  const idx = (z: number, y: number, x: number) => z * rows * cols + y * cols + x;
  if (plane === "axial") return vol.data[idx(slice, py, px)];
  if (plane === "coronal") return vol.data[idx(py, slice, px)];
  return vol.data[idx(py, px, slice)]; // sagittal: x=slice, columns map to rows(y)
}

/** mm-per-pixel for [x, y] axes of a plane. */
function mmPerPixel(m: DicomVolume, plane: Plane): [number, number] {
  const [sy, sx] = [m.pixel_spacing[0], m.pixel_spacing[1]];
  const st = m.slice_thickness || 1;
  if (plane === "axial") return [sx, sy];
  if (plane === "coronal") return [sx, st];
  return [sy, st]; // sagittal
}

const DISPLAY = 360;

export default function DicomViewer({ studies }: { studies: ImagingStudy[] }) {
  const [activeId, setActiveId] = useState(studies[0]?.id || "");
  const [vol, setVol] = useState<Vol | null>(null);
  const [plane, setPlane] = useState<Plane>("axial");
  const [slice, setSlice] = useState(0);
  const [center, setCenter] = useState(40);
  const [width, setWidth] = useState(400);
  const [zoom, setZoom] = useState(1);
  const [hover, setHover] = useState<{ vx: number; vy: number; val: number } | null>(null);
  const [measure, setMeasure] = useState<[number, number][]>([]);
  const [loading, setLoading] = useState(true);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // load volume when active study changes
  useEffect(() => {
    if (!activeId) return;
    setLoading(true);
    api.imagingVolume(activeId).then((m) => {
      setVol({ meta: m, data: decodeInt16(m.data_b64) });
      setCenter(m.default_window[0] ?? 40);
      setWidth(m.default_window[1] ?? 400);
      setPlane("axial");
      setMeasure([]);
      setLoading(false);
    });
  }, [activeId]);

  const [pw, ph, pn] = useMemo(
    () => (vol ? planeDims(vol.meta, plane) : [1, 1, 1]),
    [vol, plane]
  );

  useEffect(() => {
    if (vol) setSlice(Math.floor(pn / 2));
  }, [vol, plane, pn]);

  // render slice with window/level + measurement overlay
  useEffect(() => {
    if (!vol) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    const off = document.createElement("canvas");
    off.width = pw;
    off.height = ph;
    const octx = off.getContext("2d")!;
    const img = octx.createImageData(pw, ph);
    const lo = center - width / 2;
    for (let y = 0; y < ph; y++) {
      for (let x = 0; x < pw; x++) {
        const v = voxel(vol, plane, slice, x, y);
        let g = ((v - lo) / width) * 255;
        g = g < 0 ? 0 : g > 255 ? 255 : g;
        const o = (y * pw + x) * 4;
        img.data[o] = img.data[o + 1] = img.data[o + 2] = g;
        img.data[o + 3] = 255;
      }
    }
    octx.putImageData(img, 0, 0);

    canvas.width = DISPLAY;
    canvas.height = DISPLAY;
    ctx.imageSmoothingEnabled = false;
    ctx.fillStyle = "#000";
    ctx.fillRect(0, 0, DISPLAY, DISPLAY);
    // fit + zoom (centered)
    const base = Math.min(DISPLAY / pw, DISPLAY / ph);
    const scale = base * zoom;
    const dw = pw * scale;
    const dh = ph * scale;
    const dx = (DISPLAY - dw) / 2;
    const dy = (DISPLAY - dh) / 2;
    ctx.drawImage(off, dx, dy, dw, dh);

    // measurement overlay
    if (measure.length) {
      ctx.strokeStyle = "#21d4a8";
      ctx.fillStyle = "#21d4a8";
      ctx.lineWidth = 1.5;
      const toCanvas = (p: number[]) => [dx + p[0] * scale, dy + p[1] * scale];
      ctx.beginPath();
      measure.forEach((p, i) => {
        const [cx, cy] = toCanvas(p);
        ctx.fillRect(cx - 2, cy - 2, 4, 4);
        if (i === 0) ctx.moveTo(cx, cy);
        else ctx.lineTo(cx, cy);
      });
      if (measure.length === 2) ctx.stroke();
    }
  }, [vol, plane, slice, center, width, zoom, pw, ph, measure]);

  const distanceMm = useMemo(() => {
    if (!vol || measure.length !== 2) return null;
    const [mx, my] = mmPerPixel(vol.meta, plane);
    const dx = (measure[1][0] - measure[0][0]) * mx;
    const dy = (measure[1][1] - measure[0][1]) * my;
    return Math.sqrt(dx * dx + dy * dy);
  }, [vol, measure, plane]);

  if (loading || !vol) return <div className="muted small">Loading DICOM volume…</div>;
  const m = vol.meta;

  const onMouse = (e: React.MouseEvent, click: boolean) => {
    const canvas = canvasRef.current!;
    const rect = canvas.getBoundingClientRect();
    const cx = ((e.clientX - rect.left) / rect.width) * DISPLAY;
    const cy = ((e.clientY - rect.top) / rect.height) * DISPLAY;
    const base = Math.min(DISPLAY / pw, DISPLAY / ph) * zoom;
    const dx = (DISPLAY - pw * base) / 2;
    const dy = (DISPLAY - ph * base) / 2;
    const vx = Math.floor((cx - dx) / base);
    const vy = Math.floor((cy - dy) / base);
    if (vx < 0 || vy < 0 || vx >= pw || vy >= ph) return;
    setHover({ vx, vy, val: voxel(vol, plane, slice, vx, vy) });
    if (click) setMeasure((prev) => (prev.length >= 2 ? [[vx, vy]] : [...prev, [vx, vy]]));
  };

  return (
    <div>
      <div className="flex" style={{ gap: 8, flexWrap: "wrap", marginBottom: 8 }}>
        <select value={activeId} onChange={(e) => setActiveId(e.target.value)} style={{ width: "auto" }}>
          {studies.map((s) => (
            <option key={s.id} value={s.id}>{s.modality} · {s.depth} slice{s.depth > 1 ? "s" : ""} · {s.filename}</option>
          ))}
        </select>
        <select value={plane} onChange={(e) => setPlane(e.target.value as Plane)} style={{ width: "auto" }} disabled={m.depth === 1}>
          <option value="axial">Axial</option>
          <option value="coronal">Coronal</option>
          <option value="sagittal">Sagittal</option>
        </select>
        <span className="badge analyzed">REAL DICOM · {m.modality}</span>
      </div>

      <div className="flex" style={{ gap: 14, alignItems: "flex-start", flexWrap: "wrap" }}>
        <canvas
          ref={canvasRef}
          style={{ width: DISPLAY, height: DISPLAY, background: "#000", borderRadius: 8, border: "1px solid var(--border)", cursor: "crosshair" }}
          onMouseMove={(e) => onMouse(e, false)}
          onClick={(e) => onMouse(e, true)}
          onMouseLeave={() => setHover(null)}
        />
        <div style={{ minWidth: 200, flex: 1 }}>
          <div className="sub-row" style={{ gridTemplateColumns: "70px 1fr 52px" }}>
            <span className="small">Slice</span>
            <input type="range" min={0} max={pn - 1} value={slice} onChange={(e) => setSlice(+e.target.value)} />
            <span className="small">{slice + 1}/{pn}</span>
          </div>
          <div className="sub-row" style={{ gridTemplateColumns: "70px 1fr 52px" }}>
            <span className="small">Level</span>
            <input type="range" min={m.value_min} max={m.value_max} value={center} onChange={(e) => setCenter(+e.target.value)} />
            <span className="small">{Math.round(center)}</span>
          </div>
          <div className="sub-row" style={{ gridTemplateColumns: "70px 1fr 52px" }}>
            <span className="small">Window</span>
            <input type="range" min={1} max={Math.max(2, m.value_max - m.value_min)} value={width} onChange={(e) => setWidth(+e.target.value)} />
            <span className="small">{Math.round(width)}</span>
          </div>
          <div className="sub-row" style={{ gridTemplateColumns: "70px 1fr 52px" }}>
            <span className="small">Zoom</span>
            <input type="range" min={1} max={5} step={0.1} value={zoom} onChange={(e) => setZoom(+e.target.value)} />
            <span className="small">{zoom.toFixed(1)}×</span>
          </div>
          <div className="flex" style={{ gap: 6, flexWrap: "wrap", margin: "6px 0" }}>
            {Object.entries(m.window_presets).map(([name, wl]) => (
              <button key={name} style={{ padding: "3px 8px", fontSize: 12 }}
                onClick={() => { if (wl[0] != null) setCenter(wl[0]!); if (wl[1] != null) setWidth(wl[1]!); }}>
                {name}
              </button>
            ))}
          </div>
          <div className="small muted" style={{ lineHeight: 1.8 }}>
            {hover && <div>Cursor: ({hover.vx}, {hover.vy}) · {m.is_hu ? `${hover.val} HU` : `value ${hover.val}`}</div>}
            <div>
              Measure: {measure.length < 2 ? "click two points" : distanceMm != null ? `${distanceMm.toFixed(1)} mm` : ""}
              {measure.length > 0 && <button style={{ marginLeft: 8, padding: "1px 7px" }} onClick={() => setMeasure([])}>clear</button>}
            </div>
            <div style={{ marginTop: 6 }}>
              Spacing {m.pixel_spacing[0]}×{m.pixel_spacing[1]} mm · thickness {m.slice_thickness} mm
            </div>
            <div>Dims {m.cols}×{m.rows}×{m.depth} · {m.is_hu ? "Hounsfield units" : "raw intensity"}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
