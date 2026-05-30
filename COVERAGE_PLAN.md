# Jobrolu Coverage Plan

Goal: cover the maximum realistic share of open roles for our users, honestly,
and show that growth live on the `/coverage` page.

This is a working plan. It captures where we stand, what to build next in order of
value-per-effort, and the honesty rules for the public coverage page.

---

## Where we stand today (verified)

Sources we read now: Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee,
Workable (the ATS sources, driven by our company registry), plus Adzuna and
USAJOBS (keyword-search sources, both need API keys to be active).

The honest picture, backed by current market data:

- The systems we read are the **right ones for tech and startups**. Greenhouse
  is ranked the #1 ATS for both mid-market and enterprise on G2, and Ashby/Lever
  are core to modern startup hiring.
- We are **missing the enterprise giants**: Workday is used by ~39% of the
  Fortune 500 (Workday + SAP SuccessFactors together ~52%), and iCIMS is used by
  ~40% of the Fortune 100. These power most large-company, finance, healthcare,
  government, and other non-tech professional hiring. We read none of them.
- Biggest cheap gap: even within the systems we already support, our registry is
  only ~515 companies. Greenhouse alone has thousands of company boards (commonly
  cited at 4,000+, with trackers listing 11k-22k). So we are reaching a small
  single-digit fraction of the companies we could reach with the code we already
  have.

Rough, honest coverage estimates (not published as facts; the true denominator is
unknowable):

- Tech / new-grad today: ~10-20% of genuinely relevant open roles. Held down by
  the 515-company registry and the absence of Workday / big-tech portals.
- Tech after a full registry expansion (no new integrations): plausibly ~40-55%.
- Non-tech professional fields today: well under 10%, because those roles live on
  Workday / Taleo / iCIMS / USAJOBS, which we do not yet read.

---

## The plan, in priority order

### Phase 1 - Expand the registry on the systems we already have (highest value, lowest effort)
The ATS sources iterate over our company registry, so more companies in the
registry directly multiplies the roles we pull, with zero new integration work.

- Bulk-seed known company tokens for Greenhouse, Lever, Ashby, SmartRecruiters,
  Recruitee, Workable. Public aggregator lists (the kind that power new-grad and
  intern job-board repos) already map companies to their ATS tokens; harvest and
  add them to `registry.json` as `{ats, token, name}` entries.
- Deliberately seed **non-tech** employers that use these systems (for example
  Greenhouse and Workable are used well beyond tech), so finance, healthcare,
  marketing, and ops fields start filling in.
- Tune `registry.py` auto-discovery so new company tokens seen in results are
  retained and re-scanned.
- Watch `BASE_KEEP` (currently 2000) as the pool grows; raise it if good roles
  are being truncated out of the scored base.

Target: go from ~515 to a few thousand well-chosen companies. This alone should
roughly double or triple a tech user's pool.

### Phase 2 - Add Workday (biggest coverage gap, unlocks non-tech)
Workday is the single most impactful new source, especially for the "every field"
promise on the landing page.

- Each company runs its own Workday tenant at a URL like
  `https://<tenant>.wdN.myworkdayjobs.com/<site>`, with a JSON jobs API at
  `.../wday/cxs/<tenant>/<site>/jobs` (POST, paginated).
- Build a `from_workday(tenant, site)` source that posts to the cxs endpoint,
  paginates, and captures the full description (fetch the per-posting detail for
  the body, like the other full-description sources).
- Maintain a Workday tenant list the same way as the ATS registry. Public lists
  of Workday tenants exist; seed banks, hospitals, universities, and large
  enterprises first, since that is exactly the non-tech supply we lack.
- Effort is higher than an ATS (per-tenant URLs, the POST API, pagination), but
  the payoff is the largest of any single source.

### Phase 3 - Turn on the keyword sources and seed government (quick wins)
- Set `USAJOBS_API_KEY` + `USAJOBS_EMAIL` (free at developer.usajobs.gov) to make
  the existing USAJOBS source live. Instant federal-government coverage across
  many fields.
- Confirm Adzuna keys are set and broaden its keyword sets across non-tech fields
  so the aggregator adds breadth (note: Adzuna descriptions are snippets, so these
  roles read thinner than ATS roles).

### Phase 4 - Other enterprise systems and aggregators (later, evaluate first)
- iCIMS, Oracle/Taleo, SAP SuccessFactors: large reach but messier/less open APIs;
  evaluate feasibility and terms before investing.
- Always respect each source's terms of service. We do not scrape LinkedIn or
  Indeed.

---

## The public coverage page (`/coverage`)

Live now. It fetches `/api/coverage` and shows only real, self-measured numbers:

- Headline: live open-role count (animated), which climbs as we add jobs.
- Stat pills: companies tracked, companies hiring now, job systems read.
- Per-field bars: live roles by field, classified by our own ranking engine,
  shown as relative volume (a role can count toward more than one field).
- The systems we read, with counts.
- A straight-talk section: where we are deep, where we are growing, and what we
  do not do.

It updates on its own every time someone loads it, because it reads the live pool
and registry. As Phases 1-3 land, the headline number and the non-tech bars grow
without any change to the page.

### Honesty rules (do not break these)
- Never publish a "% of all jobs in field X" number. The total market size is
  unknowable, and a wrong public number destroys trust.
- Only show numbers we can measure from our own data (roles, companies, systems).
- Keep the "what we do not cover" note honest. Transparency is the trust feature.

---

## Immediate next actions
1. Phase 1: assemble and import a large batch of Greenhouse/Lever/Ashby company
   tokens into `registry.json`, including non-tech employers. (Biggest, cheapest
   win; do this first.)
2. Set the USAJOBS key for instant government coverage.
3. Scope `from_workday(...)` against the cxs JSON API on two or three real tenants
   (one bank, one hospital, one university) before building it out.
4. Re-check the `/coverage` numbers after each batch; the page will reflect the
   growth automatically.
