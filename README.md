# 🥗 Food Verse AI: Multimodal Food Intelligence Agent

Full-stack project (Skill Wallet Capstone Project 3): **React frontend + FastAPI backend + SQL database**.

| Module | What it does |
|---|---|
| Food Recognition | Photo → dish, cuisine, ingredients, portion, macros, fiber, allergens, Health Score |
| Freshness | Photo → Fresh / Moderately Fresh / Spoiled, safety advice, storage tips, OpenCV signal check |
| Kitchen Hygiene | Photo or video → compliance % with itemized violation log |
| Recipe Assistant | Pantry list → recipes with steps, difficulty, substitutions |
| Meal Planner | BMR/TDEE → 7-day plan + grocery list |
| History | Every result is saved to the database and can be reopened or deleted |

Works **without any API key** in demo mode. Add a Gemini or Groq key in the sidebar for real AI analysis.

## 📁 Structure

```
foodverse-ai/
├── backend/                 FastAPI + SQLAlchemy
│   ├── app/
│   │   ├── main.py          app entrypoint, CORS, /api/health
│   │   ├── core.py          prompts, scoring, OpenCV, TDEE planner, demo data
│   │   ├── llm.py           Gemini / Groq client + demo fallback
│   │   ├── database.py      engine + session (SQLite or PostgreSQL)
│   │   ├── models.py        `records` table
│   │   └── routers/         food, freshness, hygiene, recipes, planner, history
│   ├── tests/               pytest suites
│   ├── requirements.txt
│   ├── .env.example
│   └── Dockerfile
├── frontend/                React + Vite
│   ├── src/ (App.jsx, api.js, components/…)
│   ├── package.json
│   └── .env.example
├── streamlit_app/           OPTIONAL single-file Streamlit version (no database)
├── docker-compose.yml       backend + local PostgreSQL
├── render.yaml              Render blueprint (API + Postgres)
└── .vscode/                 debug config + recommended extensions
```

---

## 1) Run it in VS Code

### Prerequisites
- **Python 3.10+** (3.11 recommended), **Node.js 18+**, **VS Code**
- VS Code extensions: *Python*, *Python Debugger* (the project suggests more when you open it)

### Steps
1. Unzip, then in VS Code: **File → Open Folder…** → select the `foodverse-ai` folder.
2. Open **two terminals** (`Terminal → New Terminal`, then the `+` button).

**Terminal 1: backend**
```bash
cd backend
python -m venv .venv

# activate the virtual environment
#   Windows (PowerShell):  .venv\Scripts\Activate.ps1
#   Windows (cmd):         .venv\Scripts\activate.bat
#   macOS / Linux:         source .venv/bin/activate

pip install -r requirements.txt
cp .env.example .env          # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```
- Check it: open <http://localhost:8000/api/health>. You should see `"status": "ok"`.
- Interactive API docs: <http://localhost:8000/docs>.
- If PowerShell blocks activation: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- Tell VS Code to use the venv: `Ctrl/Cmd+Shift+P` → **Python: Select Interpreter** → `backend/.venv`.

**Terminal 2: frontend**
```bash
cd frontend
npm install
npm run dev
```
Open <http://localhost:5173>. The dev server proxies `/api` to port 8000, so no extra config is needed.

### Debugging the backend in VS Code
Press **F5** → choose **Backend: FastAPI (debug)** (stop any `uvicorn` you started in the terminal first). Breakpoints in `routers/*.py` and `core.py` work.

### Try it
1. Sidebar shows *Backend online*, `DB: sqlite`, `AI: demo`.
2. Upload any food photo in **Food Recognition** → demo result appears and is saved.
3. Open **History** to see it stored in the database.
4. For real analysis, paste a Gemini key (<https://aistudio.google.com/apikey>) or Groq key (<https://console.groq.com/keys>) in the sidebar.
   If the provider has renamed the model, type the new name in the *Vision model* field.

### Run the tests
```bash
cd backend
pip install -r requirements-dev.txt
pytest
```

---

## 2) Connect a database

Tables are created **automatically on first start** (`records`: id, kind, title, created_at, payload JSON). You only choose the connection string in `backend/.env`.

### Option A: SQLite (default, zero setup)
```env
DATABASE_URL=sqlite:///./foodverse.db
```
Creates `backend/foodverse.db`. Inspect it with the VS Code **SQLite Viewer** extension. Great for local development, but **don't use it on hosts with ephemeral disks** (Render/Vercel free tiers wipe it).

### Option B: Local PostgreSQL with Docker
```bash
docker compose up --build          # starts Postgres + backend on :8000
```
Or Postgres only, with the backend running from VS Code:
```bash
docker compose up db -d
```
then in `backend/.env`:
```env
DATABASE_URL=postgresql://foodverse:foodverse@localhost:5432/foodverse
```

### Option C: Free hosted PostgreSQL (recommended for deployment)
Pick one:
- **Neon** (<https://neon.tech>): create project → copy the connection string.
- **Supabase** (<https://supabase.com>): Project Settings → Database → connection string (use the *pooler* URI if direct connect fails).
- **Render Postgres**: created automatically by `render.yaml`.

Put it in `.env` (locally) or in your host's environment variables:
```env
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DBNAME?sslmode=require
```
Notes: special characters in the password must be URL-encoded (`@` → `%40`). `postgres://` URLs are auto-converted. Restart the backend, then check `/api/health` → `"database_type": "postgresql"`.

To inspect Postgres from VS Code use the *PostgreSQL* extension, `psql`, or pgAdmin.

> **Changing the schema later?** `create_all` only creates missing tables. For schema changes in production add [Alembic](https://alembic.sqlalchemy.org) migrations.

---

## 3) Deploy

Deploy **backend first**, then frontend, then wire CORS.

### Step 0: push to GitHub
```bash
git init && git add . && git commit -m "Food Verse AI"
git branch -M main
git remote add origin https://github.com/<you>/foodverse-ai.git
git push -u origin main
```
(`.gitignore` already excludes `.env`, `*.db`, `node_modules`.)

### Step 1: backend + database on Render
**Easiest:** Render dashboard → **New → Blueprint** → pick your repo. It reads `render.yaml`, creating the API and a Postgres database and linking `DATABASE_URL` for you.

**Manual alternative:** New → **Web Service** → repo → settings:
- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Env vars: `PYTHON_VERSION=3.11.9`, `DATABASE_URL=<Neon/Supabase/Render Postgres URL>`, `CORS_ORIGINS=<set in step 3>`

When it's live, open `https://<your-api>.onrender.com/api/health`. Note the URL.
*Free-tier services may sleep when idle (first request is slow). Check Render's current free-plan limits for web services and databases.*

### Step 2: frontend on Vercel
1. Vercel → **Add New Project** → import the repo.
2. **Root Directory:** `frontend` (framework auto-detected as Vite).
3. **Environment Variable:** `VITE_API_URL` = `https://<your-api>.onrender.com` (no trailing slash).
4. Deploy. Netlify works the same way (build `npm run build`, publish `dist`).

### Step 3: allow the frontend in CORS
In Render → your API → Environment, set:
```
CORS_ORIGINS=https://<your-app>.vercel.app
```
(comma-separate multiple origins, e.g. add a custom domain) and redeploy. Reload the site; the sidebar should show *DB: postgresql*.

### Alternative: Docker anywhere (Railway, Fly.io, VPS…)
`backend/Dockerfile` runs the API on `$PORT` (default 8000):
```bash
docker build -t foodverse-api ./backend
docker run -p 8000:8000 -e DATABASE_URL=... -e CORS_ORIGINS=... foodverse-api
```

### Alternative: Streamlit Community Cloud (no database, 1-click)
`streamlit_app/` is a self-contained single-file version. Push the repo → <https://share.streamlit.io> → New app → main file `streamlit_app/app.py`. Optionally add `GEMINI_API_KEY` under *Secrets*.

---

## 🔌 API reference

| Method | Path | Body |
|---|---|---|
| GET | `/api/health` | none |
| POST | `/api/food/analyze` | multipart `file` (image) |
| POST | `/api/freshness/analyze` | multipart `file` (image) |
| POST | `/api/hygiene/analyze` | multipart `file` (image **or** video) |
| POST | `/api/recipes/generate` | `{pantry:[...], diet, max_time, servings}` |
| GET | `/api/planner/options` | none |
| POST | `/api/planner/generate` | `{age, gender, weight, height, activity, goal, constraints}` |
| GET | `/api/history?kind=&limit=` | none |
| GET / DELETE | `/api/history/{id}` | none |

AI settings are sent as headers: `X-Provider`, `X-API-Key`, `X-Model`, `X-Demo-Mode: 1`. Alternatively set `GEMINI_API_KEY` / `GROQ_API_KEY` on the server.

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| Sidebar says **Backend offline** | Backend not running or wrong `VITE_API_URL`. Check `/api/health`. |
| Browser **CORS error** after deploy | `CORS_ORIGINS` must exactly match the frontend origin (no trailing `/`). |
| `ModuleNotFoundError` | Venv not activated or `pip install -r requirements.txt` not run. |
| `cv2` import / `libGL` error on Linux | Use `opencv-python-headless` (already pinned); in Docker `libglib2.0-0` is installed. |
| Postgres `SSL required` | Append `?sslmode=require` to `DATABASE_URL`. |
| Banner "AI provider error (HTTP 4xx)" | Wrong key, or model name retired. Change the *Vision model* field. App falls back to demo output. |
| Video upload fails | Use `.mp4` (H.264). Max upload is `MAX_UPLOAD_MB` (default 25). |

## 🔒 Security notes
- API keys typed in the UI live in the browser's `localStorage` and are forwarded per request; the server never stores them. For a public deployment, prefer server-side env keys and add authentication and rate limiting.
- Never commit `.env`. Rotate any key you accidentally expose.
- Results are informational estimates, not medical or regulatory advice.
