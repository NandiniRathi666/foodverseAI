import { useEffect, useState } from "react";
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getJson, postJson } from "../api.js";
import { AnalyzeButton, Badge, ErrorBox, MACRO_COLORS, Metric, SourceBadge, useRun } from "./ui.jsx";

const SLOT_COLORS = { Breakfast: "#f4a261", Lunch: "#2a9d8f", Dinner: "#3b7ddd", Snack: "#8a5cd6" };

function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: "text/csv" }));
  const a = Object.assign(document.createElement("a"), { href: url, download: name });
  a.click();
  URL.revokeObjectURL(url);
}

export default function PlannerTab() {
  const [opts, setOpts] = useState(null);
  const [optErr, setOptErr] = useState("");
  const [f, setF] = useState({ age: 28, gender: "Male", weight: 70, height: 170, activity: "", goal: "Fat Loss", constraints: [] });
  const { loading, error, result: r, run } = useRun();

  useEffect(() => {
    getJson("/api/planner/options")
      .then((o) => { setOpts(o); setF((p) => ({ ...p, activity: o.activity[2] || o.activity[0] })); })
      .catch((e) => setOptErr(e.message));
  }, []);

  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const toggle = (c) => set("constraints", f.constraints.includes(c) ? f.constraints.filter((x) => x !== c) : [...f.constraints, c]);

  if (optErr) return <ErrorBox error={`Could not reach the backend: ${optErr}`} />;
  if (!opts) return <p>Loading…</p>;

  const macroData = r && Object.entries(r.macros).map(([name, g]) => ({ name, kcal: g * (name === "Fats" ? 9 : 4) }));
  const slotData = r && r.days.map((d) => ({ day: d.day.slice(0, 3), ...Object.fromEntries(d.meals.map((m) => [m.slot, m.kcal])) }));
  const groups = r ? r.grocery.reduce((a, g) => ((a[g.category] ||= []).push(g), a), {}) : {};

  return (
    <section>
      <h2>Personalized Meal Planner</h2>
      <div className="card">
        <div className="grid4">
          <div><label>Age</label><input type="number" min="14" max="90" value={f.age} onChange={(e) => set("age", +e.target.value)} /></div>
          <div><label>Gender</label><select value={f.gender} onChange={(e) => set("gender", e.target.value)}>{opts.genders.map((g) => <option key={g}>{g}</option>)}</select></div>
          <div><label>Weight (kg)</label><input type="number" min="35" max="250" step="0.5" value={f.weight} onChange={(e) => set("weight", +e.target.value)} /></div>
          <div><label>Height (cm)</label><input type="number" min="120" max="230" step="0.5" value={f.height} onChange={(e) => set("height", +e.target.value)} /></div>
        </div>
        <div className="grid2">
          <div><label>Activity level</label><select value={f.activity} onChange={(e) => set("activity", e.target.value)}>{opts.activity.map((a) => <option key={a}>{a}</option>)}</select></div>
          <div><label>Fitness goal</label><select value={f.goal} onChange={(e) => set("goal", e.target.value)}>{opts.goals.map((g) => <option key={g}>{g}</option>)}</select></div>
        </div>
        <label>Dietary constraints</label>
        <div>{opts.constraints.map((c) => (
          <label key={c} className="check pill"><input type="checkbox" checked={f.constraints.includes(c)} onChange={() => toggle(c)} /> {c}</label>
        ))}</div>
      </div>
      <AnalyzeButton loading={loading} onClick={() => run(() => postJson("/api/planner/generate", f))}>📅 Generate my 7-day plan</AnalyzeButton>
      <ErrorBox error={error} />

      {r && (
        <div className="card">
          <SourceBadge res={r} />
          <div className="grid3">
            <Metric label="BMR (Mifflin-St Jeor)" value={`${r.bmr} kcal`} />
            <Metric label="TDEE (maintenance)" value={`${r.tdee} kcal`} />
            <Metric label={`Daily target · ${r.goal}`} value={`${r.target} kcal`} sub={`${r.target - r.tdee >= 0 ? "+" : ""}${r.target - r.tdee} vs TDEE`} />
          </div>
          {r.floor_applied && <div className="notice warn">Target held at a safe minimum of {r.floor} kcal/day. Consult a professional for aggressive deficits.</div>}
          {r.notes.map((n, i) => <div className="notice" key={i}>{n}</div>)}
          <div className="grid2">
            <div className="chart">
              <h4>Daily macro split (by calories)</h4>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart><Pie data={macroData} dataKey="kcal" nameKey="name" innerRadius={50} outerRadius={85}>
                  {macroData.map((m) => <Cell key={m.name} fill={MACRO_COLORS[m.name]} />)}
                </Pie><Tooltip /><Legend /></PieChart>
              </ResponsiveContainer>
              <p className="muted center">Protein {r.macros.Protein} g · Carbs {r.macros.Carbs} g · Fats {r.macros.Fats} g</p>
            </div>
            <div className="chart">
              <h4>Calories per meal slot</h4>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={slotData}><XAxis dataKey="day" /><YAxis /><Tooltip /><Legend />
                  {Object.keys(SLOT_COLORS).map((s) => <Bar key={s} dataKey={s} stackId="a" fill={SLOT_COLORS[s]} />)}
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
          {r.coach?.length > 0 && <><h4>🤖 AI coaching tips</h4><ul>{r.coach.map((t, i) => <li key={i}>{t}</li>)}</ul></>}

          <h3>🗓️ 7-Day Schedule</h3>
          {r.days.map((d) => (
            <details key={d.day}>
              <summary>{d.day} · {d.total_kcal} kcal</summary>
              {d.meals.map((m) => (
                <p key={m.slot}><b>{m.slot}</b> ({m.kcal} kcal): {m.meal}<br />
                  <span className="muted">{Object.entries(m.ingredients).map(([k, v]) => `${k} ${v} g`).join(", ")}</span></p>
              ))}
            </details>
          ))}

          <h3>🛒 Weekly Grocery List</h3>
          <div className="grid2">
            {Object.entries(groups).map(([cat, items]) => (
              <div key={cat}><h4>{cat}</h4>
                <ul>{items.map((g) => <li key={g.item}>{g.item} <Badge color="grey">{g.quantity}</Badge></li>)}</ul></div>
            ))}
          </div>
          <button className="btn secondary" onClick={() => download("grocery_list.csv", "Category,Item,Quantity\n" + r.grocery.map((g) => `"${g.category}","${g.item}","${g.quantity}"`).join("\n"))}>⬇️ Grocery list (CSV)</button>{" "}
          <button className="btn secondary" onClick={() => download("meal_plan.csv", "Day,Slot,Meal,kcal\n" + r.days.flatMap((d) => d.meals.map((m) => `"${d.day}","${m.slot}","${m.meal}",${m.kcal}`)).join("\n"))}>⬇️ Meal plan (CSV)</button>
          <p className="muted">Estimates from the Mifflin-St Jeor equation. Not medical advice; consult a dietitian for medical conditions.</p>
        </div>
      )}
    </section>
  );
}
