<div align="center">

# 🎯 JobMatch

### Stop spraying applications. Find the roles that actually fit — and the human to email.

![status](https://img.shields.io/badge/status-live-brightgreen) ![field](https://img.shields.io/badge/field-Software%20Engineering-blue) ![python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white) ![fastapi](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white) ![postgres](https://img.shields.io/badge/PostgreSQL-data-4169E1?logo=postgresql&logoColor=white) ![license](https://img.shields.io/badge/license-MIT-black)

![sources](https://img.shields.io/badge/sources-6%20ATS%20%2B%20curated-success) ![registry](https://img.shields.io/badge/company%20registry-self--growing-orange) ![ranking](https://img.shields.io/badge/ranking-LLM%20fit%20engine-ff5c5c) ![outreach](https://img.shields.io/badge/outreach-verified%20contacts-9b59b6) ![auto--apply](https://img.shields.io/badge/auto--apply-never-lightgrey)

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
  resume / profile
         |
         v
  +----------------------------------------------+
  |  SOURCING   6 ATS connectors + self-growing   |
  |             company registry + curated lists  | --> shared, deduped, fresh job DB
  +----------------------------------------------+
         |
         v   free, rule-based
   PREFILTER  (title - seniority - location)
         |
         v   LLM, strict recruiter rubric
   FIT-RANK   score - tier - reasons - disqualifiers
         |
         v   strong matches only
   ENRICH     recruiter + EM contacts, email-verified
         |
         v
   RANKED FEED + personalized outreach draft  ->  you review & send
```

---

## 🚀 Features

| | Feature | What it does |
|---|---|---|
| 🔎 | **Multi-source sourcing** | Pulls live roles from **6 ATS platforms** (Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable) plus curated new-grad lists. |
| 🌱 | **Self-growing registry** | Every job URL teaches it a new company token, so coverage **compounds automatically** — no manual company list to maintain. |
| 🎯 | **Honest fit ranking** | An LLM scores each role against your profile with reasons and hard disqualifiers. It will tell you to **skip** a bad fit. |
| 🕒 | **Freshness first** | Scheduled re-pulls + dead-listing detection. Roles that vanish from the ATS are marked dead immediately — no stale postings. |
| 📇 | **Verified contacts** | For strong matches, finds the recruiter + an engineering manager and **verifies the email** before it's ever shown as sendable. |
| ✍️ | **Outreach drafts** | Generates a short, personalized email led by your most relevant project. You review and send from your own inbox. |
| 🔎 | **Scan any role** | Paste a JD or URL from LinkedIn / Handshake / anywhere → instant fit-rank, recruiter contacts, and a personalized draft. The full pipeline on a single role you found. |
| 🛑 | **No auto-apply** | Deliberately. It protects your accounts, your sender reputation, and the quality of every application. |

---

## 🏗️ Tech stack

**Backend** Python · FastAPI · PostgreSQL · scheduled workers
**Intelligence** LLM fit-ranking + outreach drafting (Anthropic)
**Enrichment** Apollo.io (contacts) · Hunter.io (email verification)
**Sources** Greenhouse · Lever · Ashby · SmartRecruiters · Recruitee · Workable
**Frontend** Next.js · React *(filterable job feed + per-role action view)*

---

## ⚡ Quickstart

```bash
git clone https://github.com/ethanir/jobmatch.git
cd jobmatch
pip install -r requirements.txt

# 1) build your profile (from your resume) or use the example
python main.py                         # dry run on profile.example.json

# 2) turn on the intelligence + enrichment
export ANTHROPIC_API_KEY=sk-...        # LLM fit-ranking + drafts
export APOLLO_API_KEY=...              # recruiter contact lookup
export HUNTER_API_KEY=...              # email verification

python main.py my_profile.json         # -> ranked_jobs.csv / ranked_jobs.json
```

Point it at more companies by editing `SEED_COMPANIES` in `main.py` — but you barely need to. The registry discovers the rest on its own as it runs.

---

## 📁 Project structure

```
jobmatch/
├── main.py                 # orchestrator: profile -> source -> filter -> rank -> enrich -> output
├── sources.py              # 6 ATS connectors + curated-list pull
├── registry.py             # self-growing company->token registry
├── prefilter.py            # free rule-based cut before any LLM call
├── rank.py                 # LLM fit-ranking engine
├── enrich.py               # recruiter contacts + email verify + outreach draft
├── prompts.py              # profile schema + all LLM prompts (the heart)
├── profile.example.json    # sample candidate profile
└── BUILD_SPEC.md           # full spec — anyone can rebuild the product from it
```

---

## 🗺️ Roadmap

- [x] Multi-ATS sourcing across 6 platforms
- [x] Self-growing company registry
- [x] Free prefilter + LLM fit-ranking
- [x] Recruiter enrichment + email verification
- [x] Personalized outreach drafts
- [ ] Web UI — filterable feed + one-click guided apply/email
- [ ] Postgres persistence + scheduled freshness workers
- [ ] Capture-on-view browser extension (LinkedIn/Handshake, ban-safe)
- [ ] Tailored resume per role + follow-up reminders
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
