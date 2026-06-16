import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import type { AskResponse, SimilarCase } from "../types";

export default function CaseSearch() {
  const nav = useNavigate();
  const [q, setQ] = useState("bleeding during dissection");
  const [results, setResults] = useState<SimilarCase[]>([]);
  const [provider, setProvider] = useState("");
  const [ask, setAsk] = useState<AskResponse | null>(null);
  const [busy, setBusy] = useState(false);

  const doSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api.search(q);
      setResults(r.results);
      setProvider(r.provider);
      setAsk(await api.ask(q));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div>
      <h1 className="page-title">Case Search & Knowledge</h1>
      <p className="page-sub">
        Foundation-model scaffold: semantic case retrieval + grounded Q&A over the outcome database.
      </p>
      <form className="flex" onSubmit={doSearch} style={{ marginBottom: 16 }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask or search cases…" />
        <button className="primary" disabled={busy}>{busy ? "…" : "Search"}</button>
      </form>

      {ask && (
        <div className="panel" style={{ marginBottom: 16 }}>
          <h3>Answer <span className="tag">embedding provider: {ask.provider}</span></h3>
          <div>{ask.answer}</div>
        </div>
      )}

      {results.length > 0 && (
        <div className="panel">
          <h3>Retrieved cases <span className="tag">provider: {provider}</span></h3>
          <table>
            <thead>
              <tr><th>Procedure</th><th>Match</th><th>Complications</th><th>Summary</th></tr>
            </thead>
            <tbody>
              {results.map((c) => (
                <tr key={c.procedure_id} style={{ cursor: "pointer" }} onClick={() => nav(`/procedures/${c.procedure_id}`)}>
                  <td>{c.procedure_type.replace(/_/g, " ")}</td>
                  <td>{(c.similarity * 100) | 0}%</td>
                  <td>{c.complications.length ? c.complications.join(", ") : "—"}</td>
                  <td className="muted small">{c.text_summary.slice(0, 90)}…</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
