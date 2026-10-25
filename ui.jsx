import { useEffect, useMemo, useState } from "react";

export const Badge = ({ color = "blue", children }) => <span className={`badge b-${color}`}>{children}</span>;

export const Metric = ({ label, value, sub }) => (
  <div className="metric">
    <div className="metric-label">{label}</div>
    <div className="metric-value">{value}</div>
    {sub && <div className="metric-sub">{sub}</div>}
  </div>
);

export function Ring({ value = 0, label, suffix = "" }) {
  const r = 52, c = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(100, value));
  const color = pct >= 75 ? "#2e9e5b" : pct >= 50 ? "#e0a100" : "#d64545";
  return (
    <div className="ring">
      <svg viewBox="0 0 120 120" width="150" height="150">
        <circle cx="60" cy="60" r={r} fill="none" stroke="rgba(127,127,127,.2)" strokeWidth="10" />
        <circle cx="60" cy="60" r={r} fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={`${(c * pct) / 100} ${c}`} transform="rotate(-90 60 60)" />
        <text x="60" y="66" textAnchor="middle" fontSize="24" fontWeight="700" fill="currentColor">
          {Math.round(pct)}{suffix}
        </text>
      </svg>
      <div className="ring-label">{label}</div>
    </div>
  );
}

export function SourceBadge({ res }) {
  if (!res) return null;
  return (
    <div style={{ marginBottom: 8 }}>
      {res._source === "live" ? <Badge color="green">🟢 Live AI analysis</Badge> : null}
      {res._source === "demo" ? <Badge color="amber">🟡 Demo mode (sample data)</Badge> : null}
      {res.saved === false ? <Badge color="grey">Not saved (database unavailable)</Badge> : null}
      {res.warning ? <div className="notice warn">{res.warning}</div> : null}
    </div>
  );
}

export const ErrorBox = ({ error }) => (error ? <div className="notice err">⚠️ {error}</div> : null);

/** Runs an async fn and tracks loading / error / result. */
export function useRun() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState(null);
  async function run(fn) {
    setLoading(true);
    setError("");
    try {
      setResult(await fn());
    } catch (e) {
      setError(e.message || String(e));
    } finally {
      setLoading(false);
    }
  }
  return { loading, error, result, run, setResult };
}

export function FilePicker({ accept, file, onChange, label }) {
  const url = useMemo(() => (file ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => url && URL.revokeObjectURL(url), [url]);
  const isVideo = file && file.type.startsWith("video/");
  return (
    <div className="card">
      <label className="drop">
        <input type="file" accept={accept} onChange={(e) => onChange(e.target.files[0] || null)} hidden />
        <span>{file ? `📎 ${file.name}` : `⬆️ ${label}`}</span>
      </label>
      {url && (isVideo ? <video src={url} controls className="preview" /> : <img src={url} alt="preview" className="preview" />)}
    </div>
  );
}

export const AnalyzeButton = ({ loading, disabled, onClick, children }) => (
  <button className="btn" disabled={loading || disabled} onClick={onClick}>
    {loading ? "⏳ Working…" : children}
  </button>
);

export const MACRO_COLORS = { Protein: "#3b7ddd", Carbs: "#e0a100", Fats: "#d64545", Fiber: "#2e9e5b" };
