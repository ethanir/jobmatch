# Build Spec — AI Job Finder (CS / Software Engineering)

**Purpose of this document:** a complete, self-contained specification. Anyone — a developer or another AI — should be able to build the entire product from this alone. It covers what we're building, who it's for, the competition, the architecture, every component, the data model, the prompts, the roadmap, and the honest risks.

---

## 1. What we're building (one paragraph)

A tool that finds the **best-fit software engineering jobs for a specific person**, ranks them by *honest* fit against that person's real profile, and hands them what they need to act: the role, *why* it fits, and the recruiter/hiring-manager to contact. It automates the proven manual method — aggregate from good sources, rank by fit, reach out to a human — while leaving the final apply/send in the user's hands. **Scope v1: CS / software-engineering roles only.**

## 2. Who it's for

Primary user: a software engineer or CS new grad job-hunting, who is overwhelmed by volume and tired of spraying generic applications. They want: "show me the roles actually worth my time, tell me why, and tell me who to email." Start with **new grads / early career** (highest pain, clearest niche, easiest to dogfood), expand to experienced SWEs later.

## 3. The problem & the insight

The losing strategy is mass-applying to generic listings (~2-4% response). The winning method is: pull from good sources → rank by real fit → apply to strong matches → **email a real human for each** (referrals/outreach convert far better than the ATS black hole). That method works but is tedious and manual. This product automates the tedious parts.

## 4. Competition (researched)

The category is real and funded — the idea alone is not a moat.
- **Simplify** — browser autofill + curated lists + tracker. Strong at high-volume autofill; weak on matching and outreach.
- **Jobright** — AI matching, auto-apply, an AI coach, "insider connection" hints. Known weaknesses: stale/expired listings ("database decay"), generative hallucinations, opaque pricing, US-only.
- **Teal** — resume builder + match score + tracker. Resume-centric; no auto-discovery.
- Others: LazyApply, Sonara, JobCopilot, LoopCV (auto-apply volume), Jobscan/Rezi (ATS resume optimization).

**Where they're weak — our wedge:**
1. **Fresh data** — stale listings are their #1 complaint. Aggressive expired-job detection = felt advantage.
2. **Honest ranking** — they over-surface junk and hallucinate. We score strictly and explain, including "skip."
3. **Outreach hand-off** — almost none do recruiter-contact + a great draft + follow-up well. This is the step that lands interviews.
4. **Niche focus** — own CS new grads first instead of "everyone."

> Reality check: winning is about execution on the four points above, not the architecture (which everyone has).

## 5. Architecture overview

```
                ┌─────────────┐
  resume / AI → │  PROFILE    │ normalized JSON
                └─────┬───────┘
                      │
   ┌──────────────────▼───────────────────┐
   │  SOURCING (shared, runs on schedule)  │
   │  multi-ATS connectors + self-growing  │
   │  company registry + curated lists     │ → shared jobs DB (dedup, freshness)
   └──────────────────┬───────────────────┘
                      │
              ┌────────▼────────┐   free, rule-based
              │   PREFILTER      │   (title/seniority/location)
              └────────┬────────┘
                      │
              ┌────────▼────────┐   paid, per surviving job
              │  FIT-RANK (LLM)  │   score + reasons + disqualifiers
              └────────┬────────┘
                      │
        ┌──────────────▼──────────────┐  strong-tier only
        │  ENRICH (recruiter contacts) │  Apollo/Hunter + email verify
        └──────────────┬──────────────┘
                      │
              ┌────────▼────────┐
              │  RANKED FEED +   │  user reviews, one-click guided
              │  OUTREACH DRAFTS │  apply + email (NO auto-send)
              └─────────────────┘
```

## 6. Components (current scaffold maps to these)

### 6.1 Profile (`prompts.py`, `profile.example.json`)
Normalized candidate JSON (schema in §8). Built from: uploaded resume (primary, via `RESUME_TO_PROFILE` prompt), a "paste-into-your-own-AI" prompt (`BRING_YOUR_OWN_AI`), or manual entry.

### 6.2 Sourcing (`sources.py`, `registry.py`) — the most important part
- **Multi-ATS connectors:** Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable (all clean public posting APIs). Later: Workday (per-tenant `cxs` endpoint), iCIMS/Taleo (light scraping).
- **Self-growing registry:** every apply URL contains the company's ATS token. `registry.discover_from_jobs()` extracts tokens from every ingested URL, so the company list compounds automatically. (Proven: one repo pull seeded 381 companies.)
- **Curated lists:** SimplifyJobs new-grad repo — free, fresh, high-precision; also a registry seed.
- **Capture-on-view extension (future):** for LinkedIn/Handshake roles, the user's own browser session grabs one JD at a time → no bans. NOT mass scraping.
- **Freshness:** scheduled re-pulls; track `first_seen`/`last_seen`; mark a job dead the moment it leaves the ATS pull. This is the anti-staleness edge.
- **Dedup:** by hash of (company + normalized title + location) or JD content hash.

### 6.3 Prefilter (`prefilter.py`)
Free, rule-based. Cuts non-SWE titles, seniority mismatches for early-career, and (optionally) location, before any paid LLM call. De-dupes.

### 6.4 Fit-rank (`rank.py` + `FIT_RANKING` prompt)
LLM scores each surviving job vs the profile: `score`, `tier` (strong/possible/skip), `reasons`, `hard_disqualifiers`, `matched_skills`, `missing_skills`. Sorted strong→skip. Cost control: prefilter first; batch jobs per prompt for big runs; cache on a shared jobs DB so you rank once per (job, profile-type), not per user.

### 6.5 Enrich (stub in `main.py`)
For strong-tier jobs only: find recruiter + an engineering manager via **Apollo.io** (and/or **Hunter.io**); **verify emails** before anything is sent (deliverability + sender reputation). Store in a `contacts` table.

### 6.6 Outreach + action (future UI)
LLM drafts a personalized email (profile + JD + best-matching project). User reviews → one-click opens prefilled in their mail client → tracker logs it + schedules a follow-up. **No auto-send.**

## 7. Tech stack
- **Backend:** Python + FastAPI.
- **Workers/scheduler:** cron or a task queue (e.g., Celery/RQ) for scheduled sourcing + enrichment.
- **DB:** PostgreSQL.
- **LLM:** Anthropic API (swap-able).
- **Frontend (later):** Next.js + React — job feed with filters (recency, location, remote), per-job detail with fit reasons + contacts + draft.
- **Extension (later):** Chrome (capture-on-view).
- **3rd-party:** Apollo.io / Hunter.io (contacts), an email-verification API.

## 8. Data model

**Profile JSON schema** (`prompts.PROFILE_SCHEMA`):
```json
{
  "name": null, "email": null, "phone": null, "location": null,
  "work_authorization": null, "requires_sponsorship": null,
  "target_titles": [], "years_experience": null,
  "education": [{"degree": null, "school": null, "dates": null}],
  "skills": {"languages": [], "frameworks": [], "tools": [], "databases": []},
  "projects": [{"name": null, "stack": [], "summary": null}],
  "preferences": {"remote_ok": null, "onsite_ok": null, "locations": [], "min_salary": null},
  "links": {"github": null, "linkedin": null, "portfolio": null}
}
```

**Postgres tables (target):**
- `companies` (registry): id, name, ats, token, last_validated, active
- `jobs`: id, company, title, location, url, description, ats, token, source, date_posted, first_seen, last_seen, active, content_hash
- `profiles`: id, user_id, json
- `rankings`: id, job_id, profile_id, score, tier, reasons[], disqualifiers[], matched[], missing[]
- `contacts`: id, company, job_id, name, title, email, email_status, source, linkedin
- `applications`: id, user_id, job_id, status, applied_at, emailed_at, followup_at

## 9. Prompts
All in `prompts.py`: `PROFILE_SCHEMA`, `RESUME_TO_PROFILE`, `BRING_YOUR_OWN_AI`, `FIT_RANKING`. The fit-ranking prompt is the core — it carries the strict recruiter rubric (experience/stack/seniority/location/sponsorship/new-grad-fit). A cold-email draft prompt gets added at the outreach stage.

## 10. Roadmap
- **Done (scaffold):** profile schema + prompts; 6 ATS connectors; self-growing registry; prefilter; LLM fit-rank; CSV/JSON output. Runs end to end.
- **Next:** persist to Postgres; freshness/death-detection; enrichment (Apollo + verify) into the `contacts` slot; cold-email draft prompt.
- **Then:** Next.js UI (filterable feed + per-job action view); capture-on-view extension; tracker + follow-up reminders.
- **Later:** Workday/iCIMS connectors; tailored resume per job; expand beyond CS (the fit rubric is already field-adaptable).

## 11. Honest risks
- **Data freshness/coverage** — the real moat and the real grind.
- **Unit economics** — LLM + Apollo cost per user; mitigate with shared jobs DB, aggressive prefilter, enrich-only-strong-tier.
- **Differentiation** — without freshness + honest ranking + outreach, it's a worse-funded clone.
- **Email deliverability / anti-spam** — verify before send, keep volume sane, user sends from their own inbox.
- **ATS drift** — tokens/endpoints change; the registry needs periodic re-validation.

## 12. How to run the current scaffold
```bash
pip install -r requirements.txt
python main.py                  # dry run on profile.example.json
export ANTHROPIC_API_KEY=sk-... # enable LLM ranking
python main.py my_profile.json
```
`main.py` pulls from seed companies + the growing `registry.json` + the curated repo, discovers new companies from every URL, prefilters, ranks, and writes `ranked_jobs.csv/.json`.
