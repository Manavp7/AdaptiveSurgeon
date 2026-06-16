import { useEffect, useState } from "react";
import { api } from "../api/client";
import type { EventT } from "../types";

export default function AnnotationsPanel({
  procedureId,
  currentTime,
  canEdit,
  onSeek,
}: {
  procedureId: string;
  currentTime: number;
  canEdit: boolean;
  onSeek: (t: number) => void;
}) {
  const [items, setItems] = useState<EventT[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const load = () => api.listAnnotations(procedureId).then(setItems).catch(() => {});
  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [procedureId]);

  const add = async () => {
    if (!text.trim()) return;
    setBusy(true);
    try {
      await api.addAnnotation(procedureId, text.trim(), Math.round(currentTime * 10) / 10);
      setText("");
      await load();
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    await api.deleteAnnotation(procedureId, id);
    await load();
  };

  return (
    <div>
      {items.length === 0 && <div className="muted small">No annotations yet.</div>}
      {items.map((a) => (
        <div key={a.id} className="feed-item" style={{ borderLeftColor: "var(--accent)" }}>
          <div className="flex" style={{ justifyContent: "space-between" }}>
            <span style={{ cursor: "pointer" }} onClick={() => onSeek(a.t_start_s)}>{a.label}</span>
            <span className="flex">
              <span className="t" style={{ cursor: "pointer" }} onClick={() => onSeek(a.t_start_s)}>
                {a.t_start_s.toFixed(1)}s
              </span>
              {canEdit && (
                <button style={{ padding: "1px 7px" }} onClick={() => remove(a.id)}>✕</button>
              )}
            </span>
          </div>
        </div>
      ))}
      {canEdit && (
        <div className="flex" style={{ marginTop: 8 }}>
          <input
            placeholder={`Note at ${currentTime.toFixed(1)}s…`}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && add()}
          />
          <button className="primary" disabled={busy} onClick={add}>Add</button>
        </div>
      )}
    </div>
  );
}
