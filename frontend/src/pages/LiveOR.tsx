import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";

interface LiveEvent {
  type: string;
  category: string;
  clock: number;
  label: string;
  severity: string;
}

export default function LiveOR() {
  const { id } = useParams<{ id: string }>();
  const [events, setEvents] = useState<LiveEvent[]>([]);
  const [clock, setClock] = useState(0);
  const [duration, setDuration] = useState(0);
  const [status, setStatus] = useState("connecting");
  const [speed, setSpeed] = useState(4);
  const wsRef = useRef<WebSocket | null>(null);
  const feedRef = useRef<HTMLDivElement>(null);

  const connect = (spd: number) => {
    wsRef.current?.close();
    setEvents([]);
    setClock(0);
    setStatus("connecting");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/api/ws/procedures/${id}/live?speed=${spd}`);
    wsRef.current = ws;
    ws.onopen = () => setStatus("live");
    ws.onclose = () => setStatus((s) => (s === "done" ? "done" : "ended"));
    ws.onmessage = (m) => {
      const msg = JSON.parse(m.data);
      if (msg.type === "meta") setDuration(msg.duration);
      else if (msg.type === "event") {
        setClock(msg.clock);
        setEvents((prev) => [...prev, msg]);
      } else if (msg.type === "done") {
        setClock(msg.clock);
        setStatus("done");
      } else if (msg.type === "error") {
        setStatus("error: " + msg.message);
      }
    };
  };

  useEffect(() => {
    connect(speed);
    return () => wsRef.current?.close();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    feedRef.current?.scrollTo(0, feedRef.current.scrollHeight);
  }, [events]);

  const pct = duration ? Math.min(100, (clock / duration) * 100) : 0;

  return (
    <div>
      <h1 className="page-title">Live OR Copilot</h1>
      <p className="page-sub">
        Real-time replay (WebSocket) — phases, risk and advisories stream as the procedure unfolds.
      </p>

      <div className="panel" style={{ marginBottom: 16 }}>
        <div className="flex" style={{ justifyContent: "space-between" }}>
          <div>
            <span className={`badge ${status === "live" ? "analyzed" : "registered"}`}>{status}</span>
            <span className="muted small" style={{ marginLeft: 10 }}>
              t = {clock.toFixed(1)}s / {duration.toFixed(0)}s
            </span>
          </div>
          <div className="flex">
            <span className="muted small">Speed</span>
            <select value={speed} onChange={(e) => { const s = parseFloat(e.target.value); setSpeed(s); connect(s); }} style={{ width: 80 }}>
              <option value={2}>2×</option>
              <option value={4}>4×</option>
              <option value={8}>8×</option>
            </select>
            <button onClick={() => connect(speed)}>↻ Restart</button>
          </div>
        </div>
        <div className="bar" style={{ marginTop: 10 }}>
          <div style={{ width: `${pct}%`, background: "var(--accent)" }} />
        </div>
      </div>

      <div className="panel">
        <h3>Live event stream</h3>
        <div ref={feedRef} style={{ maxHeight: 420, overflowY: "auto" }}>
          {events.map((e, i) => (
            <div key={i} className="feed-item" style={{ borderLeftColor: `var(--${e.severity})` }}>
              <div className="flex" style={{ justifyContent: "space-between" }}>
                <span className={`sev-${e.severity}`}>
                  <b>[{e.category}]</b> {e.label}
                </span>
                <span className="t">{e.clock.toFixed(1)}s</span>
              </div>
            </div>
          ))}
          {events.length === 0 && <div className="muted small">Waiting for stream…</div>}
        </div>
      </div>
    </div>
  );
}
