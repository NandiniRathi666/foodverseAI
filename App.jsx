import { useState } from "react";
import FoodTab from "./components/FoodTab.jsx";
import FreshnessTab from "./components/FreshnessTab.jsx";
import HistoryTab from "./components/HistoryTab.jsx";
import HygieneTab from "./components/HygieneTab.jsx";
import PlannerTab from "./components/PlannerTab.jsx";
import RecipesTab from "./components/RecipesTab.jsx";
import Settings from "./components/Settings.jsx";

const TABS = [
  ["food", "🍽️ Food Recognition", FoodTab],
  ["fresh", "🧪 Freshness", FreshnessTab],
  ["hygiene", "🧼 Kitchen Hygiene", HygieneTab],
  ["recipes", "👩‍🍳 Recipe Assistant", RecipesTab],
  ["planner", "📅 Meal Planner", PlannerTab],
  ["history", "🗂️ History", HistoryTab],
];

export default function App() {
  const [tab, setTab] = useState("food");
  return (
    <div className="layout">
      <Settings />
      <main>
        <header className="hero">
          <h1>🥗 Food Verse AI</h1>
          <p>Multimodal Food Intelligence Agent: recognize dishes, audit nutrition, check freshness, inspect kitchen hygiene, cook from your pantry and plan your week.</p>
        </header>
        <nav className="tabs">
          {TABS.map(([id, label]) => (
            <button key={id} className={tab === id ? "tab active" : "tab"} onClick={() => setTab(id)}>{label}</button>
          ))}
        </nav>
        {TABS.map(([id, , Comp]) =>
          id === "history" ? (
            tab === "history" && <Comp key={id} /> /* remount so it reloads from the DB each time */
          ) : (
            <div key={id} hidden={tab !== id}><Comp /></div>
          )
        )}
      </main>
    </div>
  );
}
