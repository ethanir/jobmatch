<div align="center">

# 🎯 JobMatch

### Stop spraying applications. Find the roles that actually fit — and the human to email.

![status](https://img.shields.io/badge/status-working%20prototype-brightgreen) ![field](https://img.shields.io/badge/field-Software%20Engineering-blue) ![python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white) ![fastapi](https://img.shields.io/badge/FastAPI-optional%20API-009688?logo=fastapi&logoColor=white) ![postgres](https://img.shields.io/badge/PostgreSQL-optional-4169E1?logo=postgresql&logoColor=white) ![license](https://img.shields.io/badge/license-MIT-black)

![sources](https://img.shields.io/badge/sources-6%20ATS%20%2B%20curated-success) ![registry](https://img.shields.io/badge/company%20registry-self--growing-orange) ![ranking](https://img.shields.io/badge/ranking-funnel%20%2B%20LLM-ff5c5c) ![cache](https://img.shields.io/badge/re--runs-near--free-9b59b6) ![auto--apply](https://img.shields.io/badge/auto--apply-never-lightgrey)

**One profile. Thousands of live roles. Ranked honestly. With the recruiter's email attached.**

</div>

---

## ✨ Overview

Most job tools do one of two things: **autofill** the same form a hundred times, or dump a feed of loosely-matched listings on you. Neither tells you *which roles are actually worth your time* or *who to talk to*. That's volume, not strategy.

**JobMatch is different.** It runs the job search the way it actually works:

> **Aggregate** from the cleanest sources → **rank** every role honestly against *your* real profile → **hand you the recruiter** to email, with a personalized draft.

You stay in control of the final send. No spammy auto-apply, no getting your LinkedIn banned, no hallucinated matches. Just the best-fit roles and a clear next move for each.

---

## 🧠 How it works

```
  resume / profile  (onboard.py: PDF/DOCX -> structured profile via LLM)
         |
         v
  +----------------------------------------------+
  |  SOURCING   6 ATS connectors + self-growing   |
  |             company registry + curated lists  | --> ~40k live roles, parallel pull
  +----------------------------------------------+
         |
         v   free, rule-based
   PREFILTER  (title - seniority - location)        ~40k -> ~7k
         |
         v   free heuristic scorer (score.py), $0
   FUNNEL     skill overlap + title + location + recency, ranks ALL
         |
         v   LLM rubric — TOP_N only (default 100), the only paid step
   FIT-RANK   score - tier - reasons - gaps        ~$1 first run
         |
         v   cache (jobcache.py): only NEW jobs ever hit the LLM
   CACHE      re-runs are near-free; new postings flagged "NEW"
         |
         v   strong matches only
   ENRICH     recruiter contacts (Apollo, optional) + AI outreach draft
         |
         v
   make_ui.py -> viewer.html   filterable feed, fit reasons, copy-ready email
```

---

## 🚀 Features

| | Feature | What it does |
|---|---|---|
| 🔎 | **Multi-source sourcing** | Pulls live roles from **6 ATS platforms** (Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable) plus curated new-grad lists. Pulls run in parallel — ~40k roles in under a minute. |
| 🌱 | **Self-growing registry** | Every job URL teaches it a new company token, so coverage **compounds automatically** — no manual company list to maintain. |
| 💸 | **Cost-correct funnel** | A free heuristic scores *every* role; only the top N (default 100) hit the LLM. A full run costs **~$1, not ~$70.** Set `TOP_N=0` for a fully free run. |
| 🧠 | **Honest fit ranking** | The LLM scores your top matches with reasons and gaps. It will tell you to **skip** a bad fit. |
| ♻️ | **Seen-job cache** | Remembers what it already ranked, so **re-runs only pay for genuinely new jobs.** New postings are flagged **NEW** and float to the top. |
| ✍️ | **AI outreach drafts** | Every strong match gets a short, personalized email led by your most relevant project — generated from your full profile, copy-ready. You review and send from your own inbox. |
| 📇 | **Contact lookup** | With an Apollo key, finds the recruiter for strong matches. Without one, a one-click **"Find recruiter on LinkedIn"** link is always there. |
| 🖥️ | **Standalone viewer** | `make_ui.py` bakes the feed into a single `viewer.html` — no server, no build step. Filterable by Strong / Possible / Skip. |
| 🔎 | **Scan any role** | Paste a JD or URL from LinkedIn / Handshake → instant fit-rank + draft for one role you found yourself. |
| 🛑 | **No auto-apply, no auto-send** | Deliberately. It protects your accounts, your sender reputation, and the quality of every application. |

---

## 🏗️ Tech stack

**Backend** Python · FastAPI (optional API) · PostgreSQL (optional persistence)
**Intelligence** LLM fit-ranking + outreach drafting (Anthropic, Sonnet)
**Enrichment** Apollo.io (contacts, optional) · Hunter.io (email verification, optional)
**Sources** Greenhouse · Lever · Ashby · SmartRecruiters · Recruitee · Workable
**Frontend** Standalone single-file React viewer (`make_ui.py` → `viewer.html`) — no build step

---

## ⚡ Quickstart

```bash
git clone https://github.com/ethanir/jobmatch.git
cd jobmatch
pip install --user -r requirements.txt

# 1) build your profile from your resume (needs ANTHROPIC_API_KEY)
export ANTHROPIC_API_KEY=sk-...
python3 onboard.py my_resume.pdf my_profile.json

# 2) rank (funnel + cache keep it cheap: ~$1 first run, near-free after)
export APOLLO_API_KEY=...               # optional: recruiter contacts
python3 main.py my_profile.json         # -> ranked_jobs.csv / ranked_jobs.json

# 3) view the feed (standalone, no server)
python3 make_ui.py                      # -> viewer.html
open viewer.html
```

**Free run** (no LLM cost at all): `TOP_N=0 python3 main.py my_profile.json`
**Rank more deeply** (costs more): `TOP_N=200 python3 main.py my_profile.json`
**Keep it fresh on a schedule:** `python3 worker.py --interval 60`

---

## 📁 Project structure

```
jobmatch/
├── main.py                 # orchestrator: source -> filter -> funnel -> rank -> cache -> enrich -> output
├── onboard.py              # resume (PDF/DOCX/TXT) -> structured profile via LLM
├── sources.py              # 6 ATS connectors + curated-list pull (parallel)
├── registry.py             # self-growing company->token registry
├── prefilter.py            # free rule-based cut before any LLM call
├── score.py                # free heuristic funnel scorer ($0) — picks what the LLM sees
├── rank.py                 # LLM fit-ranking engine (parallel)
├── jobcache.py             # seen-job + ranking cache — re-runs only pay for new jobs
├── enrich.py               # recruiter contacts (Apollo) + email verify + outreach draft
├── scan.py                 # paste-a-JD/URL -> full pipeline on one role
├── make_ui.py              # bakes ranked_jobs.json -> standalone viewer.html
├── server.py               # optional FastAPI: serves the feed + /api/scan
├── db.py                   # optional Postgres schema + freshness/death-detection
├── worker.py               # optional scheduled re-pull
├── prompts.py              # profile schema + all LLM prompts (the heart)
├── profile.example.json    # sample candidate profile
├── RUNNING.md              # full how-to for every piece
└── BUILD_SPEC.md           # full spec — anyone can rebuild the product from it
```

---

## 🗺️ Roadmap

- [x] Multi-ATS sourcing across 6 platforms (parallel)
- [x] Self-growing company registry
- [x] Free prefilter + cost-correct LLM funnel
- [x] Seen-job cache — re-runs only pay for new jobs
- [x] Personalized AI outreach drafts per strong match
- [x] Standalone single-file viewer (filterable feed, copy-ready email)
- [x] Scan-any-role (paste a JD/URL)
- [x] Contact lookup (Apollo) + LinkedIn fallback
- [~] Postgres persistence + scheduled freshness workers *(code present in db.py/worker.py; not wired into the default flow)*
- [ ] Capture-on-view browser extension (LinkedIn/Handshake, ban-safe)
- [ ] Tailored resume per role + follow-up reminders
- [ ] Hosted multi-user version (accounts, billing) — currently runs locally per user
- [ ] Expand beyond software engineering (the rubric is already field-adaptable)

---

## 🔒 Principles

- **Honest over hopeful** — a correct "skip" beats an inflated match.
- **Human in the loop** — we draft; you send. Always.
- **Respect the inbox** — verified emails only, sane volume, your own sender identity.
- **Fresh or nothing** — a stale listing is a broken promise.

---

<div align="center">

**Built for people who'd rather send 20 great applications than 200 blind ones.**

MIT © Ethan Irimiciuc

</div>
