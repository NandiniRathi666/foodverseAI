import { useState } from "react";
import { postJson } from "../api.js";
import { AnalyzeButton, Badge, ErrorBox, SourceBadge, useRun } from "./ui.jsx";

const DIETS = ["No restriction", "Vegetarian", "Vegan", "Keto", "Diabetic-Friendly"];

export default function RecipesTab() {
  const [pantry, setPantry] = useState("");
  const [diet, setDiet] = useState(DIETS[0]);
  const [maxTime, setMaxTime] = useState(30);
  const [servings, setServings] = useState(2);
  const { loading, error, result: r, run } = useRun();
  const items = pantry.split(/[,\n]/).map((x) => x.trim()).filter(Boolean);

  return (
    <section>
      <h2>Smart Kitchen Recipe Assistant</h2>
      <div className="card">
        <label>What's in your pantry? (comma or line separated)</label>
        <textarea rows={4} value={pantry} onChange={(e) => setPantry(e.target.value)} placeholder="rice, eggs, onion, tomato, garlic, lentils, spinach…" />
        <div className="grid3">
          <div><label>Diet</label><select value={diet} onChange={(e) => setDiet(e.target.value)}>{DIETS.map((d) => <option key={d}>{d}</option>)}</select></div>
          <div><label>Max cooking time: {maxTime} min</label><input type="range" min="10" max="90" step="5" value={maxTime} onChange={(e) => setMaxTime(+e.target.value)} /></div>
          <div><label>Servings</label><input type="number" min="1" max="10" value={servings} onChange={(e) => setServings(+e.target.value || 1)} /></div>
        </div>
      </div>
      <AnalyzeButton loading={loading} disabled={items.length === 0}
        onClick={() => run(() => postJson("/api/recipes/generate", { pantry: items, diet, max_time: maxTime, servings }))}>
        👩‍🍳 Generate recipes
      </AnalyzeButton>
      <ErrorBox error={error} />
      {r && <SourceBadge res={r} />}
      {r?.recipes?.map((rec, i) => {
        const d = String(rec.difficulty || "Easy");
        const dc = d.toLowerCase().startsWith("e") ? "green" : d.toLowerCase().startsWith("m") ? "amber" : "red";
        return (
          <div className="card" key={i}>
            <h3>🍳 {rec.name}</h3>
            <Badge color="blue">⏱ {Math.round(rec.cook_time_min)} min</Badge>
            <Badge color={dc}>{d}</Badge>
            <Badge color="purple">🍽 {rec.servings} servings</Badge>
            <Badge color="grey">🔥 {Math.round(rec.calories_per_serving)} kcal/serving</Badge>
            <div className="grid2">
              <p><b>✅ From your pantry</b><br />{(rec.ingredients_used || []).join(", ") || "n/a"}</p>
              <p><b>🛒 Still needed</b><br />{(rec.missing_ingredients || []).join(", ") || "Nothing, you have it all!"}</p>
            </div>
            <b>Instructions</b>
            <ol>{(rec.steps || []).map((s, k) => <li key={k}>{s}</li>)}</ol>
            {rec.substitutions?.length > 0 && (
              <><b>🔄 Substitutions</b><ul>{rec.substitutions.map((s, k) => <li key={k}>{s.ingredient} → {s.substitute}</li>)}</ul></>
            )}
            {rec.nutrition_note && <div className="notice ok">{rec.nutrition_note}</div>}
          </div>
        );
      })}
    </section>
  );
}
