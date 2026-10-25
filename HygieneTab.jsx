import { useState } from "react";
import { postFile } from "../api.js";
import { AnalyzeButton, Badge, ErrorBox, FilePicker, Metric, Ring, SourceBadge, useRun } from "./ui.jsx";

const STATUS_COLOR = { Compliant: "green", Violation: "red", "Not visible": "grey" };

export default function HygieneTab() {
  const [file, setFile] = useState(null);
  const { loading, error, result: r, run } = useRun();
  const grade = r && r.score != null ? (r.score >= 90 ? ["green", "Excellent"] : r.score >= 70 ? ["amber", "Needs improvement"] : ["red", "Non-compliant"]) : null;
  const critical = r ? r.violations.filter((v) => v.Severity === "Critical").length : 0;

  return (
    <section>
      <h2>Kitchen Hygiene & Food Safety Compliance</h2>
      <FilePicker accept="image/*,video/*" file={file} onChange={setFile} label="Upload a kitchen photo or short video" />
      <AnalyzeButton loading={loading} disabled={!file} onClick={() => run(() => postFile("/api/hygiene/analyze", file))}>
        🧼 Run hygiene audit
      </AnalyzeButton>
      <ErrorBox error={error} />
      {r && (
        <div className="card">
          <SourceBadge res={r} />
          <div className="grid2">
            <div className="center">
              {r.score == null ? <div className="notice warn">No indicators were visible, so a score can't be computed. Try a wider shot.</div> : (
                <>
                  <Ring value={r.score} suffix="%" label="Hygiene Compliance" />
                  <Badge color={grade[0]}>{grade[1]}</Badge>
                </>
              )}
            </div>
            <div>
              <p><b>Summary:</b> {r.summary}</p>
              <Metric label="Violations logged" value={r.violations.length} sub={critical ? `${critical} critical` : null} />
              <p className="muted">Analyzed {r.frames_analyzed} {r.input_type === "video" ? "video frame(s)" : "image"}.</p>
            </div>
          </div>
          <h4>Checklist</h4>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Indicator</th><th>Status</th><th>Severity</th><th>Observation</th></tr></thead>
              <tbody>
                {r.rows.map((row) => (
                  <tr key={row.Indicator}>
                    <td>{row.Indicator}</td>
                    <td><Badge color={STATUS_COLOR[row.Status]}>{row.Status}</Badge></td>
                    <td>{row.Severity}</td>
                    <td>{row.Observation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {r.violations.length > 0 ? (
            <>
              <h4>🚨 Violation log</h4>
              {r.violations.map((v) => (
                <div className="notice err" key={v.Indicator}>
                  <Badge color={v.Severity === "Critical" ? "red" : "amber"}>{v.Severity}</Badge> <b>{v.Indicator}</b>: {v.Observation}
                  <br /><i>➡️ {v["Corrective action"]}</i>
                </div>
              ))}
            </>
          ) : <div className="notice ok">No violations detected in the visible area. 🎉</div>}
          <p className="muted">AI audit of visible evidence only. It doesn't replace an official health inspection.</p>
        </div>
      )}
    </section>
  );
}
