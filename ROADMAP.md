<div align="center">

# 🗺️ Roadmap & Launch Plan

**Where the project stands, what's left, and how it ships.**

![v1](https://img.shields.io/badge/v1%20engine-complete-brightgreen) ![v2](https://img.shields.io/badge/v2%20coverage-next-orange) ![v3](https://img.shields.io/badge/v3%20launch-planned-blue)

</div>

---

## TL;DR

The engine is **done**. It sources, ranks, drafts outreach, and runs cheap. It found real strong-fit roles and was used to apply to them.

The **only** meaningful work left is **coverage**: the ranking is smart, but it can only rank jobs that make it into the funnel, and right now the funnel sees ~400 companies on 6 ATS types. Widen that, then ship it as a named product with a domain and a landing page.

That's the whole remaining plan. Everything else is polish.

---

## The two-stage funnel (why coverage is the lever)

```
   ALL pulled roles  ~40,000
          |
          |   stage 1 — FREE heuristic score (fast, crude keyword/title match)
          v
   top N by free score  (default 100)
          |
          |   stage 2 — LLM fit-rank (smart, reads the role, the only paid step)
          v
   Strong / Possible / Skip  + reasons + draft email
```

- **Stage 1 is cheap but dumb.** It can underrate a genuinely great role (odd title wording, etc.).
- **Stage 2 is smart but only sees what stage 1 forwards.** A hidden gem ranked #150 by the free scorer never reaches the LLM.
- `TOP_N` controls how deep the smart ranker digs. Higher = catches more buried matches, costs a little more. **It does not change what's at the top** — output is always best-first.

**Implication:** the quality ceiling is set by *what enters the funnel at all*. That's company/ATS coverage. Hence v2.

---

## v1 — the engine ✅ (complete)

| Done | Capability |
|---|---|
| ✅ | Multi-ATS sourcing — Greenhouse, Lever, Ashby, SmartRecruiters, Recruitee, Workable (parallel, ~40k roles in <1 min) |
| ✅ | Self-growing company registry (~400 companies) |
| ✅ | Free prefilter + cost-correct LLM funnel (~$1 first run, near-free after) |
| ✅ | Seen-job cache — re-runs only pay for genuinely new jobs |
| ✅ | Honest fit ranking — Strong / Possible / Skip, with reasons and gaps |
| ✅ | AI outreach drafts — subject + body, led by best project, em-dash-free |
| ✅ | Recruiter workflow — LinkedIn discovery + live name personalization |
| ✅ | Standalone viewer — Why-you-fit / Worth-knowing split, per-part copy buttons |
| ✅ | Scan-any-role — paste a JD/URL for a one-off fit-rank + draft |

**Honest note on Apollo:** contact lookup is wired in, but Apollo's people-search API is gated behind their paid Organization tier (confirmed: free/trial keys return `API_INACCESSIBLE`). The tool detects this and falls back to the free LinkedIn flow automatically. **Do not pay for Apollo for this** — the volume need (a few recruiters) doesn't justify it; LinkedIn covers it free.

---

## v2 — coverage 🟧 (the only real work left)

In strict order of impact-per-effort:

### 1. Expand the company registry — *biggest win, least work*
Go from ~400 to several thousand companies by seeding the registry from large public sources:
- YC company directory
- Public Greenhouse / Lever / Ashby board listings
- levels.fyi company list

**Why first:** every company added is more real roles entering the funnel, with zero new code paths — it reuses the existing connectors. This alone meaningfully widens the net.
**Interview value:** "scans N thousand companies" is a far stronger line than "~400."

### 2. Add a Workday connector — *biggest missing platform*
A large share of mid-to-large employers post **only** on Workday, so they're currently invisible. Workday isn't a clean JSON API like the existing six, so this is more work — but it's the single largest coverage gap among ATS platforms.

### 3. Pull from a job-aggregator feed — *path to "everything"*
Invert the model: instead of enumerating every company, query one large pre-built index, then dedupe against the ATS pulls. This is the real route to "scan everywhere," and a different enough architecture that it comes last.

> **Scope honesty:** v1 already produces results. v2 is genuine improvement *and* a strong portfolio story, but it is optimization of a channel that already works. It is not a prerequisite for job-searching — direct LinkedIn/Handshake applications and referrals (e.g. the Amazon referral) remain higher-yield channels and should run in parallel, not be replaced by this tool.

---

## v3 — launch 🔵 (after coverage)

| Step | What | Notes |
|---|---|---|
| 4 | **Pick a final name** | `JobMatch` is taken. Shortlist below. |
| 5 | **Buy the domain** | Check `.com` + trademark before committing. |
| 6 | **Landing page + hosted version** | Marketing page; serve the viewer from the web (accounts) instead of a local `viewer.html`. |

### Name shortlist
`JobMatch` is taken, so the working candidates (verify domain + trademark before buying):

| Name | Why it works |
|---|---|
| **Shortlist** | Says exactly what it does; sounds like a real product. |
| **Rolescout** | Clear, brandable, likely available. |
| **Fitscore** | Names the core feature (it scores fit). |
| **Reqd** | Short, recruiter-flavored ("req"), domain likely open. |
| **Beacon** | Clean; "surfaces what's hidden" feel. |

**Leaning:** `Shortlist` or `Rolescout` for a real-product feel; `Reqd` or `Rolio` for a short, easy-to-register handle.

> **Product-vs-portfolio honesty:** as a hosted *business*, unit economics are tough — third-party data (contacts) is expensive, the market is crowded (Simplify, Jobright, Teal), and the target user (new grads) is price-sensitive. Its highest current value is as a **portfolio project and interview story**: a real, cost-engineered, multi-stage AI system that was actually used to land applications. Launch it because it's a great showcase, not because it's a sure revenue play.

---

## Definition of done

- [ ] Registry expanded to several thousand companies (v2.1)
- [ ] Workday connector live (v2.2)
- [ ] Aggregator feed integrated + deduped (v2.3)
- [ ] Final name chosen
- [ ] Domain purchased
- [ ] Landing page live
- [ ] Hosted viewer with accounts

---

<div align="center">

**Engine: done. Next: widen the net. Then: name it, buy it, ship it.**

MIT © Ethan Irimiciuc

</div>
