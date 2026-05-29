<div align="center">

# 🎯 Jobrolu

### Stop spraying applications. Find the roles that actually fit, and the human to email.

[![Live](https://img.shields.io/badge/live-jobrolu.com-4fe39b?style=for-the-badge)](https://www.jobrolu.com)

![status](https://img.shields.io/badge/status-live%20v1-brightgreen) ![field](https://img.shields.io/badge/field-Software%20Engineering-blue) ![python](https://img.shields.io/badge/Python-3.9+-3776AB?logo=python&logoColor=white) ![fastapi](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white) ![railway](https://img.shields.io/badge/deployed%20on-Railway-0B0D0E?logo=railway&logoColor=white) ![license](https://img.shields.io/badge/license-MIT-black)

**One profile. Thousands of live roles. Ranked honestly, with the recruiter's email attached.**

**🌐 Live at [www.jobrolu.com](https://www.jobrolu.com)**

</div>

---

## ✨ What it is

Most job tools either autofill the same form a hundred times, or dump a feed of loosely-matched listings on you. Neither tells you which roles are actually worth your time, or who to talk to.

Jobrolu runs the search the way it actually works: **aggregate** from clean sources, **rank** every role honestly against a real profile, and **hand you the recruiter** to email with a personalized draft. You always do the final send. No spammy auto-apply, no hallucinated matches.

**You make an account first.** Jobrolu ranks against *you*, so you sign up, build a profile (a quick form, a resume, or your own AI), and a feed of the live job pool ranked for you unlocks. Everyone has an equal account; each person gets their own profile and their own ranked feed.

---

## 🧠 How it works (the funnel)

The whole design exists to keep cost near zero while still using AI where it matters. Jobs flow through stages, and **only one stage costs money**.

```
  resume / profile            (onboard.py: PDF/DOCX, even scanned -> structured JSON via one cheap LLM call)
        |
        v
  SOURCING                    7 ATS APIs + Adzuna aggregator + curated lists, self-growing
        |                     company registry. ~8k-50k live roles pulled in parallel.   $0
        v
  PREFILTER                   free, rule-based. Drops non-SWE titles, senior roles,
        |                     wrong locations.                                            $0
        v
  FREE HEURISTIC SCORE        score.py rates EVERY surviving job by keyword/title/
        |                     new-grad/seniority/location. Ranks them best-first.         $0
        v
  AI FIT-RANK (top N only)    rank.py sends only the top N to the LLM, which reads the
        |                     full posting and scores the real fit. N is set live by the
        |                     in-app scan-depth slider (default 100).               ~$1+ per run
        v
  CACHE                       jobcache.py remembers every AI ranking, so re-runs only
        |                     pay for genuinely new jobs.                          near $0 after
        v
  ENRICH + DRAFT              strong matches get a one-click LinkedIn recruiter search
        |                     and a personalized outreach email (cached).
        v
  FEED                        app.html: sign in, then browse YOUR ranked feed,
                              filter, search, verify with your own AI, copy the draft.
```

---

## 🏷️ How ranking works, and what the scores mean

**This is the most important thing to understand, because two different systems produce the numbers you see.**

There are two scorers, and they are NOT on the same scale:

1. **The free heuristic scorer** (`score.py`) reads keywords, the job title, seniority words, and location. It is fast and free, and it runs on *every* job. It is a rough guess. It can give a high number to a job just because the title looks right ("Graduate Software Engineer" scores high on the new-grad and SWE-title signals even if zero of your skills appear in the text).

2. **The AI fit-ranker** (`rank.py`) reads the *full job description* against your profile and produces a careful, considered score with real reasons, gaps, and disqualifiers. Only the top N jobs (default 100) ever reach this step, because it is the only paid step.

### The three tiers

| Tier | Who decided it | What it means |
|---|---|---|
| 🟢 **Strong** | The AI only | The AI read the full posting and confirmed a strong fit. Trustworthy. The heuristic can **never** award Strong. |
| 🟡 **Possible** | AI *or* heuristic | Either the AI judged it a moderate fit, or it only passed the free keyword pre-filter and the AI has not read it yet. |
| ⚪ **Skip** | AI *or* heuristic | Clear non-fit (seniority, clearance, wrong role), or a low heuristic score. |

### Why a "Possible" can show a higher number than a "Strong" (and why that is correct)

You will sometimes see a Possible job at, say, **78** sitting above a Strong job at **72**. That is expected, not a bug:

- The **78** is the *free heuristic's* unverified estimate. The AI never read that job.
- The **72** is the *AI's* verified verdict after reading the full posting.

A verified 72 is worth more than an unverified 78. They measure different things. To make this obvious, the UI marks the difference:

- **AI-verified** scores show in solid color with an **"AI verified"** tag and a `FIT` ring.
- **Estimated** (heuristic, not yet read by the AI) scores show muted, prefixed with a `~`, with an **"Estimate only"** tag and an `EST` ring.

So a green `88` with "AI verified" is a real judgment. A grey `~78` with "Estimate only" is a hunch to be confirmed.

### Turning estimates into verified scores

Only the top N jobs get AI-read, and at free-scoring time most jobs are ranked on their **title** alone, since full descriptions are only fetched for the jobs about to be AI-read. So a genuinely good role with a plain or unusual title can sit just outside the cutoff and stay an estimate. Three ways to verify deeper:

- **The scan-depth slider** (in the app). A slider sets how many top roles the AI reads on the next refresh, and shows a live estimate of the cost, time, and likely strong matches before you run. Running a refresh needs the access code, but the slider and estimate are visible to everyone. This is the main lever, and it is exactly what reaches the good roles a title-only score under-rated.
- **`TOP_N`** for command-line runs (see the cost model below).
- **Bring-your-own-AI, right in the app.** On a personalized feed, "Rank with my AI" hands you a ready-made prompt to paste into your own ChatGPT or Claude; paste the JSON back and your top matches become verified fits, stored as yours, for **$0**. It works through your top *unverified* roles in batches, so you save one batch and run it again for the next. (The `export_rank.py` / `import_rank.py` CLI does the same from the command line.)

---

## 💸 Cost model

Only the AI fit-rank step costs money. Everything else (sourcing, prefilter, heuristic scoring, hydration, the LinkedIn recruiter search) is plain HTTP and free.

| Scan depth | Jobs the AI reads | First run | Re-run (cache) |
|---|---|---|---|
| 100 (default) | top 100 | ~$1 | ~$0 |
| 300 | top 300 | ~$2-3 | ~$0 |
| 800 (deep sweep) | top 800 | ~$8 | ~$0 |
| 0 + web-AI export | top 25-50, free web chat | **$0** | $0 |

In the app, the **scan-depth slider** sets this per run and shows a live, cache-aware estimate of cost, time, and likely matches before you commit. Because already-scanned jobs are cached and free, the estimate counts only depth beyond what has already been read, so a repeat at the same depth reads as **~$0**. You pay only when you drag the slider deeper than you have scanned before. The server hard-caps any single run at 2000 jobs as a backstop, and an Anthropic spend cap is the final ceiling.

The **cache** (`jobcache.py`) is what keeps it cheap: each posting has a stable id, and once the AI ranks it, the result is reused forever. Re-runs only pay for jobs that are genuinely new since last time.

Resume parsing on profile upload is one small LLM call (cents). It reads even scanned/image-only PDFs, and infers your likely target roles and location from your experience, which you review and edit before saving. Outreach drafts for strong matches are cents and are also cached.

---

## 🔐 Accounts and budget protection

Everyone has an equal account; there is no special owner tier. The model is simple:

- **Create an account, then build a profile.** Sign up with an email and password, then build your profile (a quick form, a resume upload, or letting your own AI describe you). The feed is gated: you must be signed in, and you need a profile, so nobody lands on a wall of unranked jobs or sees someone else's scores.
- **Sign in and sign out.** Passwords are hashed (PBKDF2-HMAC-SHA256, stdlib, no extra dependency) with a per-user salt and verified in constant time; the session is a signed, HttpOnly cookie. Building a profile before signing up is preserved, since an account reuses the browser's id.
- **Your feed is yours.** Once you have a profile, you see the shared job pool ranked for *you* by the free heuristic, plus any roles you have personally verified. New jobs show as estimates until you verify them.
- **Verifying is free for everyone.** "Rank with my AI" turns your top matches into verified fits using your own ChatGPT or Claude, at no cost, with a slider for how many to send. Those verified rankings are stored against your profile and overlay your feed. Resume upload is open to every signed-in account.
- **Refresh is the one budget-spending action.** The Refresh button is visible to everyone, but re-running the full pipeline spends the deployment's API budget, so it stays behind the access code: click Refresh, enter the code once, and it runs. The single-role scan is gated the same way. A spend cap in the Anthropic console is the hard ceiling.
- **The shared pool is durable.** Each Refresh writes the resulting pool to Postgres, not just the host's disk, so a redeploy never reverts it. The feed reads the pool from Postgres (falling back to the committed file when the database is empty or off) and caches it in memory, so it is not re-parsed on every request.

Configure on the host (Railway) with env vars:

| Variable | Purpose |
|---|---|
| `ANTHROPIC_API_KEY` | Required, powers ranking and drafts |
| `ACCESS_CODE` | The code required to run a Refresh (and scan); the Refresh button is visible to all, but only runs with this. Refresh is open to anyone if unset |
| `COOKIE_SECRET` | Fixed random string so sessions and the refresh unlock survive redeploys |
| `DATABASE_URL` | Postgres for accounts, per-user profiles, per-user rankings, and the durable shared job pool (with no database set, the site serves the committed file feed and skips accounts, for local dev) |
| `DB_POOL_MAX` | Optional. Max pooled DB connections (default 10) |

API keys live only in the host's private environment, never in this repo.

---

## 📡 Sources and coverage

Live roles are pulled in parallel from **7 ATS platforms** (Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable, Workday) plus the **Adzuna** keyword aggregator and curated new-grad lists.

The **self-growing registry** (`registry.py`) reads the ATS token out of every job URL it ingests, so the company list compounds automatically. Widen coverage on demand with `seed.py`, `bulk_seed.py`, or `seed_workday.py` (all $0 API, validated against live boards).

Out of scope by design: LinkedIn and Indeed forbid scraping. The right way to use those is applying directly, by hand.

---

## ⚡ Run it locally

```bash
pip install --user -r requirements.txt

export ANTHROPIC_API_KEY=sk-...
python3 onboard.py my_resume.pdf my_profile.json
python3 main.py my_profile.json
python3 make_ui.py
open viewer.html
```

Or run the hosted site (landing, onboarding, live feed):

```bash
uvicorn server:app --port 8000
```

Knobs: `TOP_N=0` for a fully free run, `TOP_N=300` to rank deeper. See `RUNNING.md` for everything.

---

## 📁 Project structure

```
jobrolu/
├── main.py          orchestrator: source -> prefilter -> free score -> AI rank -> cache -> enrich
├── sources.py       7 ATS connectors + Adzuna + curated lists (parallel)
├── registry.py      self-growing company -> token registry
├── seed*.py         widen the registry ($0 API, validated)
├── prefilter.py     free rule-based cut before any AI call
├── score.py         free heuristic scorer (gives the "estimate" numbers)
├── hydrate.py       fetch full job descriptions before AI ranking ($0)
├── rank.py          AI fit-ranking (gives the "AI verified" numbers, the only paid step)
├── jobcache.py      seen-job + ranking cache, so re-runs only pay for new jobs
├── enrich.py        recruiter contacts (optional Apollo) + outreach draft
├── onboard.py       resume -> structured profile via LLM
├── scan.py          paste one JD/URL -> full pipeline on a single role
├── make_ui.py       bake ranked_jobs.json -> standalone viewer.html
├── db.py            Postgres per-user layer: users, profiles, rankings, usage, durable job pool (pooled, self-healing)
├── landing.html     marketing landing page (served at /)
├── signin.html      create account / sign in
├── start.html       Profile tab: build or edit your profile (form, resume, or bring-your-own-AI)
├── app.html         Live Feed tab (sign-in + profile gated): your ranked feed, search, verify, refresh, outreach
├── server.py        FastAPI: pages + /api/* (accounts, per-user profiles + feeds, code-gated refresh)
├── prompts.py       profile schema + all LLM prompts (the heart)
└── BUILD_SPEC.md    full spec, anyone can rebuild the product from it
```

---

## 🔒 Principles

- **Honest over hopeful.** A correct "skip" beats an inflated match, and an estimate is labeled as an estimate.
- **Verified means verified.** Only the AI, after reading the full posting, can mark a job Strong.
- **Human in the loop.** We draft, you send. Always.
- **Cost-correct.** Free where possible, AI only where it earns its keep.

---

<div align="center">

**Built for people who'd rather send 20 great applications than 200 blind ones.**

MIT © Ethan Irimiciuc

</div>
