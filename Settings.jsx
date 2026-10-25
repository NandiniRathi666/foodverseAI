import { useEffect, useState } from "react";
import { getJson, loadSettings, saveSettings } from "../api.js";
import { Badge } from "./ui.jsx";

const MODEL_HINT = { Gemini: "gemini-2.5-flash", Groq: "meta-llama/llama-4-scout-17b-16e-instruct" };

export default function Settings() {
  const [s, setS] = useState(loadSettings());
  const [health, setHealth] = useState(null);
  const [offline, setOffline] = useState(false);

  const update = (patch) => {
    const next = { ...s, ...patch };
    setS(next);
    saveSettings(next);
  };

  useEffect(() => {
    getJson("/api/health").then((h) => { setHealth(h); setOffline(false); }).catch(() => setOffline(true));
  }, [s.apiKey, s.provider, s.demo]);

  return (
    <aside className="sidebar">
      <h3>⚙️ Configuration</h3>
      <label>AI provider</label>
      <select value={s.provider} onChange={(e) => update({ provider: e.target.value, model: "" })}>
        <option>Gemini</option>
        <option>Groq</option>
      </select>
      <label>API key</label>
      <input type="password" value={s.apiKey} placeholder="Paste key (optional)" autoComplete="off"
        onChange={(e) => update({ apiKey: e.target.value })} />
      <label>Vision model</label>
      <input value={s.model} placeholder={MODEL_HINT[s.provider]} onChange={(e) => update({ model: e.target.value })} />
      <label className="check">
        <input type="checkbox" checked={s.demo} onChange={(e) => update({ demo: e.target.checked })} /> Force demo mode
      </label>
      <p className="muted">Your key is kept in this browser only and sent with each request. No key = demo mode.</p>
      <hr />
      <h4>System status</h4>
      {offline && <Badge color="red">Backend offline</Badge>}
      {health && (
        <>
          <Badge color={health.database ? "green" : "red"}>DB: {health.database_type}</Badge>
          <Badge color={health.ai_mode === "live" ? "green" : "amber"}>AI: {health.ai_mode}</Badge>
          <Badge color={health.opencv ? "green" : "grey"}>OpenCV {health.opencv ? "on" : "off"}</Badge>
        </>
      )}
      <p className="muted" style={{ marginTop: 16 }}>
        ⚠️ Informational estimates only, not medical or regulatory advice. When in doubt about food safety, throw it out.
      </p>
    </aside>
  );
}
