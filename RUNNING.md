# Running the full stack

Three pieces: the **pipeline** (produces ranked jobs), the **API** (serves them), and the **UI** (displays them). Postgres is optional — without it the API reads `ranked_jobs.json`.

## 1. Onboard — build your profile from a resume
```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...      # needed to parse the resume into a profile
python onboard.py my_resume.pdf my_profile.json   # pdf, docx, txt, or md
```
Without an API key it writes an empty profile template you can fill manually.

## 2. Pipeline — produce the ranked data (one-shot)

## 2. API — serve the data
```bash
uvicorn server:app --reload --port 8000
# GET http://127.0.0.1:8000/api/health   → {"status":"ok","source":"file"|"db"}
# GET http://127.0.0.1:8000/api/jobs?tier=strong
# POST http://127.0.0.1:8000/api/scan     → {"text":"<JD or URL>","user_id":"me"}
```
With no `DATABASE_URL`, it serves `ranked_jobs.json`. With Postgres set, it serves from the DB.

## 3. UI — display the data
`ui/App.jsx` is a standalone React component. Drop it into any React app (Vite recommended) as the root:
```bash
npm create vite@latest jobmatch-ui -- --template react
# replace src/App.jsx with ui/App.jsx, then:
npm run dev
```
The UI fetches from `API_BASE` (default `http://127.0.0.1:8000`). If the API is down, it automatically renders the bundled sample data so it never shows a blank screen. The header dot shows green for **live** data, amber for **sample**.

## 4. Postgres (optional, for persistence + freshness)
```bash
createdb jobmatch
export DATABASE_URL=postgresql://localhost:5432/jobmatch
python -c "import db; c=db.connect(); db.init_db(c); print('schema created')"
```
Then on each scheduled pull, `db.sync_jobs()` upserts the batch and marks any job
that dropped out of the pull as dead — that's the freshness/death-detection.

## 5. Keep it fresh — the scheduled worker
```bash
python worker.py --once             # one refresh cycle (good for cron)
python worker.py --interval 60      # loop every 60 minutes
```
Each cycle pulls, grows the registry, and (with Postgres) marks any vanished job
dead. Pair `--once` with cron, or run the loop under a process manager.

## Data flow
```
main.py ──► ranked_jobs.json ─┐
                              ├──► server.py ──► /api/jobs ──► ui/App.jsx
Postgres (db.py) ─────────────┘
```
