import { useCallback, useEffect, useState } from "react";
import { del, getJson } from "../api.js";
import { Badge, ErrorBox } from "./ui.jsx";

const KIND = { food: ["🍽️ Food", "green"], freshness: ["🧪 Freshness", "amber"], hygiene: ["🧼 Hygiene", "blue"], recipes: ["👩‍🍳 Recipes", "purple"], planner: ["📅 Planner", "grey"] };

export default function HistoryTab() {
  const [rows, setRows] = useState([]);
  const [kind, setKind] = useState("");
  const [open, setOpen] = useState({});
  const [error, setError] = useState("");

  const load = useCallback(() => {
    getJson(`/api/history${kind ? `?kind=${kind}` : ""}`).then(setRows).catch((e) => setError(e.message));
  }, [kind]);
  useEffect(load, [load]);

  async function toggle(id) {
    if (open[id]) return setOpen((o) => ({ ...o, [id]: null }));
    try { const rec = await getJson(`/api/history/${id}`); setOpen((o) => ({ ...o, [id]: rec.result })); }
    catch (e) { setError(e.message); }
  }
  async function remove(id) {
    try { await del(`/api/history/${id}`); load(); } catch (e) { setError(e.message); }
  }

  return (
    <section>
      <h2>Saved History (database)</h2>
      <select value={kind} onChange={(e) => setKind(e.target.value)} style={{ maxWidth: 240 }}>
        <option value="">All types</option>
        {Object.entries(KIND).map(([k, [l]]) => <option key={k} value={k}>{l}</option>)}
      </select>{" "}
      <button className="btn secondary" onClick={load}>🔄 Refresh</button>
      <ErrorBox error={error} />
      {rows.length === 0 && <p className="muted">Nothing saved yet. Run an analysis in any other tab and it appears here.</p>}
      {rows.map((r) => (
        <div className="card" key={r.id}>
          <Badge color={(KIND[r.kind] || ["", "grey"])[1]}>{(KIND[r.kind] || [r.kind])[0]}</Badge>
          <b>{r.title}</b> <span className="muted">· {new Date(r.created_at).toLocaleString()}</span>
          <div style={{ marginTop: 8 }}>
            <button className="btn secondary" onClick={() => toggle(r.id)}>{open[r.id] ? "Hide JSON" : "View JSON"}</button>{" "}
            <button className="btn danger" onClick={() => remove(r.id)}>🗑 Delete</button>
          </div>
          {open[r.id] && <pre>{JSON.stringify(open[r.id], null, 2)}</pre>}
        </div>
      ))}
    </section>
  );
}
