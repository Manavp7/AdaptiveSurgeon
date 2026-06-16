/** Lightweight dependency-free SVG charts. */

interface Series {
  label: string;
  color: string;
  points: [number, number][]; // [x, y]
}

function bounds(series: Series[]) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const s of series)
    for (const [x, y] of s.points) {
      minX = Math.min(minX, x);
      maxX = Math.max(maxX, x);
      minY = Math.min(minY, y);
      maxY = Math.max(maxY, y);
    }
  if (!isFinite(minX)) return { minX: 0, maxX: 1, minY: 0, maxY: 1 };
  if (minY === maxY) {
    maxY += 1;
    minY -= 1;
  }
  return { minX, maxX, minY, maxY };
}

export function LineChart({
  series,
  height = 140,
  playheadX,
  yLabel,
}: {
  series: Series[];
  height?: number;
  playheadX?: number; // in data X units
  yLabel?: string;
}) {
  const W = 100;
  const H = 100;
  const pad = 4;
  const { minX, maxX, minY, maxY } = bounds(series);
  const sx = (x: number) => pad + ((x - minX) / (maxX - minX || 1)) * (W - 2 * pad);
  const sy = (y: number) => H - pad - ((y - minY) / (maxY - minY || 1)) * (H - 2 * pad);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" style={{ width: "100%", height }}>
        {series.map((s) => (
          <polyline
            key={s.label}
            fill="none"
            stroke={s.color}
            strokeWidth={0.8}
            vectorEffect="non-scaling-stroke"
            points={s.points.map(([x, y]) => `${sx(x)},${sy(y)}`).join(" ")}
          />
        ))}
        {playheadX != null && (
          <line
            x1={sx(playheadX)}
            x2={sx(playheadX)}
            y1={0}
            y2={H}
            stroke="#ffffff"
            strokeWidth={0.6}
            vectorEffect="non-scaling-stroke"
          />
        )}
      </svg>
      <div className="legend">
        {yLabel && <span className="muted">{yLabel}</span>}
        {series.map((s) => (
          <span key={s.label}>
            <span className="dot" style={{ background: s.color }} />
            {s.label}
          </span>
        ))}
      </div>
    </div>
  );
}

export function BarChart({
  data,
  height = 140,
}: {
  data: { label: string; value: number; color?: string }[];
  height?: number;
}) {
  const max = Math.max(1, ...data.map((d) => d.value));
  return (
    <div style={{ display: "flex", alignItems: "flex-end", gap: 8, height }}>
      {data.map((d) => (
        <div key={d.label} style={{ flex: 1, textAlign: "center", height: "100%", display: "flex", flexDirection: "column", justifyContent: "flex-end" }}>
          <div className="small muted" style={{ marginBottom: 2 }}>{d.value}</div>
          <div
            title={`${d.label}: ${d.value}`}
            style={{
              height: `${(d.value / max) * 100}%`,
              background: d.color || "var(--accent)",
              borderRadius: "4px 4px 0 0",
              minHeight: 2,
            }}
          />
          <div className="small" style={{ marginTop: 4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {d.label}
          </div>
        </div>
      ))}
    </div>
  );
}
