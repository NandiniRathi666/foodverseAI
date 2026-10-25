// Thin API client. AI settings live in localStorage and are sent as headers on every call.
const BASE = import.meta.env.VITE_API_URL || "";
const KEY = "fv_settings";

export const defaultSettings = { provider: "Gemini", apiKey: "", model: "", demo: false };

export function loadSettings() {
  try {
    return { ...defaultSettings, ...JSON.parse(localStorage.getItem(KEY) || "{}") };
  } catch {
    return { ...defaultSettings };
  }
}
export function saveSettings(s) {
  localStorage.setItem(KEY, JSON.stringify(s));
}

function headers() {
  const s = loadSettings();
  const h = { "X-Provider": s.provider };
  if (s.apiKey) h["X-API-Key"] = s.apiKey;
  if (s.model) h["X-Model"] = s.model;
  if (s.demo) h["X-Demo-Mode"] = "1";
  return h;
}

async function handle(res) {
  if (!res.ok) {
    let msg = res.statusText || `HTTP ${res.status}`;
    try {
      const j = await res.json();
      msg = typeof j.detail === "string" ? j.detail : JSON.stringify(j.detail);
    } catch {
      /* ignore */
    }
    throw new Error(msg);
  }
  return res.json();
}

export const getJson = (p) => fetch(BASE + p, { headers: headers() }).then(handle);
export const del = (p) => fetch(BASE + p, { method: "DELETE", headers: headers() }).then(handle);
export const postJson = (p, body) =>
  fetch(BASE + p, { method: "POST", headers: { ...headers(), "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(handle);
export const postFile = (p, file) => {
  const f = new FormData();
  f.append("file", file);
  return fetch(BASE + p, { method: "POST", headers: headers(), body: f }).then(handle);
};
