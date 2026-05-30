# How Jobrolu Works (matching, refresh, and cost)

A plain-language reference for how a user's feed is built, how it updates, and
what each part costs. This is the single place to understand the moving parts so
nothing gets lost as we keep adding jobs and fields.

## The pipeline, one pass
Every scan runs the same pipeline once and produces the shared pool that every
user's feed is drawn from:

1. Source: pull open roles from every connected job system (Greenhouse, Lever,
   Ashby, SmartRecruiters, Recruitee, Workable, Workday, USAJOBS) plus the
   curated repo. Full descriptions are captured so each role can be read in full.
2. Prefilter: drop obvious non-roles and duplicates.
3. Free score: the heuristic engine scores every role against the shared profile
   (title fit, skills overlap, field, seniority, location, recency). This is
   free; it runs on plain compute, no API.
4. Persist: save the scored pool to Postgres so it survives restarts.

A per-user step then narrows each person's feed: when a user opens their feed,
the engine re-scores the pool against THEIR profile and keeps their top matches.
One pool serves a nurse, a teacher, an accountant, and a software engineer alike.

## The free first-feed match works across every field
The first feed a new user sees, right after their resume is parsed, is built
entirely by the free engine. It is field-agnostic: it classifies a title into the
candidate's own field and ranks within it. This was verified by running the real
engine on a mixed pool: a nurse profile surfaces nursing roles first, a teacher
surfaces teaching roles, an accountant surfaces accounting roles, and a software
engineer surfaces engineering roles, with cross-field roles falling down the list.

This matters because the free ranking is what selects the top ~150 a user later
sends to the AI. If it were weak, the AI step would inherit a weak shortlist. So
the free engine is the foundation, and it is held to working for all fields.

## What a refresh does, and what it costs
There are two ways the pool refreshes:

- Daily auto-scan (automatic): runs the pipeline with the AI rank OFF (top_n=0,
  no drafts). It pulls and free-scores new roles, then persists. Cost: zero API.
  This keeps every feed current for free, every day.
- Manual Refresh (owner only, enforced on the server): runs the full pipeline
  including the AI fit-rank and outreach drafts on the owner's top ~100 matches.
  Cost: roughly one dollar of API, bounded by top_n and independent of pool size.
  Only the owner can trigger this; a regular user who calls it gets a 401.

New account cost: parsing a resume into a profile costs a fraction of a cent, and
is capped at 10 parses per user per day. The first feed is the free engine (zero
API). "Rank my matches" uses the user's OWN ChatGPT or Claude, not the owner's,
so it costs the owner nothing.

| Action | Who | API cost to owner |
|---|---|---|
| New account + resume parse | any user | a fraction of a cent (capped 10/user/day) |
| First live feed (free ranking) | any user | zero |
| Daily auto-scan | automatic | zero |
| Rank my matches | any user | zero (uses the user's own AI) |
| Manual Refresh | owner only | about one dollar (bounded, not tied to pool size) |

## What an existing user gets after a refresh
Every scan (including the free daily one) changes the pool version, which
invalidates every user's cached feed. So on their next load, every existing
account re-scores against the new, larger pool and sees the new better-matching
roles. This is NOT limited to new accounts: an account that has never run "Rank
my matches" still gets the new roles in its free feed.

A user who already ran their AI ranking keeps those verified rankings on the
roles they ranked; newly added roles arrive on free estimates until they run Rank
again, which sends a fresh batch of new top candidates to verify.

## Application status is saved per user and survives refreshes
When a user marks a role Applied, Interviewing, and so on, that status is stored
per user, keyed by a stable job id, in its own table separate from the pool. So
it persists across every refresh: the same role keeps its status, and a refresh
never wipes what a user is tracking.

## The NEW tag needs a persistent cache
A role is flagged NEW when the scan has not seen its job id before. That "seen"
memory lives in CACHE_FILE. On an ephemeral host the disk is wiped on every
redeploy, so the cache must point at a persistent volume, for example
CACHE_FILE=/data/ranked_cache.json on a mounted Railway volume. Without it, the
first scan after each deploy over-flags roles as NEW and re-pays to rank roles
already ranked. With it, the NEW tag is accurate and paid rankings compound
across runs.

## Honesty rules (do not break)
- Never publish a "percent of the job market" figure. The true total is
  unknowable; a fabricated number would destroy the trust that is the edge.
- Only show numbers measured from the real pool (roles, companies, systems,
  fields).
- Keep the "what we do not cover" note honest.
