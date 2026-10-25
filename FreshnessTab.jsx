import { useState } from "react";
import { postFile } from "../api.js";
import { AnalyzeButton, Badge, ErrorBox, FilePicker, Metric, SourceBadge, useRun } from "./ui.jsx";

const COLOR = { Fresh: "green", "Moderately Fresh": "amber", Spoiled: "red" };
const LABELS = [["texture", "Surface texture"], ["discoloration", "Discoloration"], ["wrinkling", "Wrinkling"], ["mold", "Mold / slime"]];

export default function FreshnessTab() {
  const [file, setFile] = useState(null);
  const { loading, error, result: r, run } = useRun();
  const c = r ? COLOR[r.stage] : "grey";

  return (
    <section>
      <h2>Food Freshness & Spoilage Diagnostic</h2>
      <FilePicker accept="image/*" file={file} onChange={setFile} label="Upload a perishable item (fruit, vegetable, meat, dairy)" />
      <AnalyzeButton loading={loading} disabled={!file} onClick={() => run(() => postFile("/api/freshness/analyze", file))}>
        🧪 Diagnose freshness
      </AnalyzeButton>
      <ErrorBox error={error} />
      {r && (
        <div className="card">
          <SourceBadge res={r} />
          <h3>{r.item}</h3>
          <Badge color={c}>Stage: {r.stage}</Badge>
          <Badge color={c}>🛡️ {r.advice}</Badge>
          <Badge color="blue">📦 {r.category}</Badge>
          <Badge color="grey">Confidence {Math.round((r.confidence || 0) * 100)}%</Badge>
          {r.stage === "Spoiled" && <div className="notice err">🚫 Discard immediately. Do not taste-test, and wash hands and surfaces that touched it.</div>}
          {r.stage === "Moderately Fresh" && <div className="notice warn">⏳ Use within 24 hours. Cook thoroughly if it is meat, seafood or dairy-based.</div>}
          {r.stage === "Fresh" && <div className="notice ok">✅ Safe to consume. Store properly to keep it that way.</div>}
          <div className="grid2">
            <div>
              <h4>Visual indicators</h4>
              <ul>{LABELS.map(([k, l]) => <li key={k}><b>{l}:</b> {r.indicators?.[k] || "n/a"}</li>)}</ul>
              <p><b>Estimated shelf life:</b> {r.shelf_life_estimate || "n/a"}</p>
            </div>
            <div>
              <h4>Preservation & storage tips</h4>
              <ul>{r.storage_tips.map((t, i) => <li key={i}>{t}</li>)}</ul>
            </div>
          </div>
          {r.signals && (
            <details>
              <summary>🔬 OpenCV pixel-level signal check (heuristic)</summary>
              <div className="grid4">
                <Metric label="Dark-spot area" value={`${r.signals.dark_pct.toFixed(1)}%`} />
                <Metric label="Browning area" value={`${r.signals.brown_pct.toFixed(1)}%`} />
                <Metric label="Texture variance" value={r.signals.texture_var.toFixed(0)} />
                <Metric label="Spoilage index" value={r.signals.spoilage_index.toFixed(2)} />
              </div>
              <p className="muted">Simple color/texture statistics. Naturally dark or brown foods can score high. Treat as a hint, not a verdict.</p>
            </details>
          )}
        </div>
      )}
    </section>
  );
}
