import { useState } from "react";
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { postFile } from "../api.js";
import { AnalyzeButton, Badge, ErrorBox, FilePicker, MACRO_COLORS, Metric, Ring, SourceBadge, useRun } from "./ui.jsx";

export default function FoodTab() {
  const [file, setFile] = useState(null);
  const { loading, error, result: r, run } = useRun();

  const macros = r && [
    { name: "Protein", g: r.protein_g, kcal: r.protein_g * 4 },
    { name: "Carbs", g: r.carbs_g, kcal: r.carbs_g * 4 },
    { name: "Fats", g: r.fat_g, kcal: r.fat_g * 9 },
    { name: "Fiber", g: r.fiber_g, kcal: 0 },
  ];
  const color = r ? (r.health_score >= 75 ? "green" : r.health_score >= 50 ? "amber" : "red") : "grey";

  return (
    <section>
      <h2>Food Recognition & Nutrition Audit</h2>
      <FilePicker accept="image/*" file={file} onChange={setFile} label="Upload a meal or dish photo" />
      <AnalyzeButton loading={loading} disabled={!file} onClick={() => run(() => postFile("/api/food/analyze", file))}>
        🔍 Analyze meal
      </AnalyzeButton>
      <ErrorBox error={error} />
      {r && (
        <div className="card">
          <SourceBadge res={r} />
          <h3>{r.dish_name}</h3>
          <div>
            <Badge color="blue">🌍 {r.cuisine}</Badge>
            <Badge color="purple">⚖️ {r.portion_size}</Badge>
            <Badge color={color}>❤️ Health Score {r.health_score}/100</Badge>
            {r.allergens.length === 0 && <Badge color="green">✅ No major allergens</Badge>}
            {r.allergens.map((a) => <Badge key={a} color="red">⚠️ {a}</Badge>)}
          </div>
          <div className="grid5">
            <Metric label="Calories" value={`${Math.round(r.calories)} kcal`} />
            <Metric label="Protein" value={`${Math.round(r.protein_g)} g`} />
            <Metric label="Carbs" value={`${Math.round(r.carbs_g)} g`} />
            <Metric label="Fats" value={`${Math.round(r.fat_g)} g`} />
            <Metric label="Fiber" value={`${Math.round(r.fiber_g)} g`} />
          </div>
          <div className="grid3">
            <div className="chart">
              <h4>Calories by macro</h4>
              <ResponsiveContainer width="100%" height={220}>
                <PieChart>
                  <Pie data={macros.filter((m) => m.kcal > 0)} dataKey="kcal" nameKey="name" innerRadius={50} outerRadius={85}>
                    {macros.filter((m) => m.kcal > 0).map((m) => <Cell key={m.name} fill={MACRO_COLORS[m.name]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="chart">
              <h4>Macros (grams)</h4>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={macros}>
                  <XAxis dataKey="name" /><YAxis /><Tooltip />
                  <Bar dataKey="g">{macros.map((m) => <Cell key={m.name} fill={MACRO_COLORS[m.name]} />)}</Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="chart center"><Ring value={r.health_score} label="Health Score" /></div>
          </div>
          <p><b>Why this score:</b> {r.health_rationale}</p>
          <p><b>Detected ingredients:</b> {r.ingredients.join(", ")}</p>
          {r.tips.length > 0 && <><b>Tips</b><ul>{r.tips.map((t, i) => <li key={i}>{t}</li>)}</ul></>}
          <p className="muted">Model confidence: {Math.round((r.confidence || 0) * 100)}% · Estimates are approximate.</p>
        </div>
      )}
    </section>
  );
}
