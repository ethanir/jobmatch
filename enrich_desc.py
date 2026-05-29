"""
On-demand full-description backfill for job boards that omit the description in
their list feed.

Why this exists: most ATS feeds (Greenhouse, Lever, Ashby, Recruitee, Workable)
return the full posting text in the list response, so we already have everything.
But SmartRecruiters and Workday return little or nothing in their list endpoints;
the full text lives behind a per-posting detail endpoint. Without it, the AI ranking
has nothing to read for ~20% of companies, so it can only judge those jobs by their
title. This module fetches the full text for exactly the jobs that need it (and only
when we are about to rank them), so the AI compares against the complete posting,
the way a person reading the listing would.

Design:
  * Pure best-effort. Every fetch is wrapped; any failure (network, shape change,
    timeout) leaves the job exactly as it was. It can never break a scan or a rank.
  * Only fills EMPTY/thin descriptions. It never overwrites text we already have.
  * Bounded. backfill() fetches in parallel with a hard cap and a short timeout, so
    it adds predictable, small latency only to the handful of jobs being ranked.
"""
import re
import html as _html

try:
    import requests
except Exception:                      # requests should always be present
    requests = None

TIMEOUT = 5
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; Jobrolu/1.0)"}

# A description shorter than this is treated as missing and is a backfill target.
THIN = 160


def _clean(text, limit=12000):
    """HTML -> plain text, same shape as sources._clean."""
    if not text:
        return ""
    text = _html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


# --------------------------------------------------------------------------- parse
def parse_smartrecruiters(detail):
    """Pull the full posting text out of a SmartRecruiters posting-detail object.
    The text lives in jobAd.sections.<section>.text (HTML). We concatenate every
    section (company description, responsibilities, qualifications, etc.)."""
    if not isinstance(detail, dict):
        return ""
    sections = (((detail.get("jobAd") or {}).get("sections")) or {})
    parts = []
    # sections is a dict of {key: {"title":..., "text": "<html>"}}; order is not
    # guaranteed, so sort by key for stable output.
    if isinstance(sections, dict):
        for _, sec in sorted(sections.items()):
            if isinstance(sec, dict):
                parts.append(sec.get("text", "") or "")
    elif isinstance(sections, list):
        for sec in sections:
            if isinstance(sec, dict):
                parts.append(sec.get("text", "") or "")
    return _clean(" ".join(p for p in parts if p))


def parse_workday(detail):
    """Pull the full posting text out of a Workday CXS job-detail object. The body
    is jobPostingInfo.jobDescription (HTML)."""
    if not isinstance(detail, dict):
        return ""
    info = detail.get("jobPostingInfo") or {}
    body = info.get("jobDescription", "") or ""
    return _clean(body)


# --------------------------------------------------------------------------- fetch
def _sr_detail_url(job):
    """SmartRecruiters stores the posting's API ref as the job url, which is exactly
    the detail endpoint. Only treat it as fetchable if it is that API URL."""
    url = job.get("url", "") or ""
    if "api.smartrecruiters.com" in url and "/postings/" in url:
        return url
    return None


def _wd_detail_url(job):
    """Reconstruct a Workday CXS detail URL from the stored human posting URL
    https://{tenant}.{srv}.myworkdayjobs.com/en-US/{site}{externalPath}
    -> https://{tenant}.{srv}.myworkdayjobs.com/wday/cxs/{tenant}/{site}{externalPath}"""
    url = job.get("url", "") or ""
    m = re.match(r"(https://([^.]+)\.[^/]+\.myworkdayjobs\.com)/[^/]+/([^/]+)(/.+)", url)
    if not m:
        return None
    base, tenant, site, ext = m.group(1), m.group(2), m.group(3), m.group(4)
    return f"{base}/wday/cxs/{tenant}/{site}{ext}"


def fetch_smartrecruiters(job, timeout=TIMEOUT):
    if requests is None:
        return ""
    u = _sr_detail_url(job)
    if not u:
        return ""
    r = requests.get(u, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    return parse_smartrecruiters(r.json())


def fetch_workday(job, timeout=TIMEOUT):
    if requests is None:
        return ""
    u = _wd_detail_url(job)
    if not u:
        return ""
    r = requests.get(u, headers={**HEADERS, "Accept": "application/json"}, timeout=timeout)
    r.raise_for_status()
    return parse_workday(r.json())


_FETCHERS = {"smartrecruiters": fetch_smartrecruiters, "workday": fetch_workday}


def full_description(job, timeout=TIMEOUT):
    """Best-effort full description for one job. Returns "" if we can't get it
    (unknown source, no detail URL, network/parse failure)."""
    src = (job.get("source") or job.get("ats") or "").lower()
    fn = _FETCHERS.get(src)
    if not fn:
        return ""
    try:
        return fn(job, timeout=timeout) or ""
    except Exception:
        return ""


def needs_backfill(job):
    src = (job.get("source") or job.get("ats") or "").lower()
    if src not in _FETCHERS:
        return False
    return len((job.get("description") or "").strip()) < THIN


def backfill(jobs, cap=60, timeout=TIMEOUT, workers=12):
    """Fill in missing descriptions for up to `cap` of the given jobs, in parallel.
    Mutates the job dicts in place (only when a non-empty description comes back).
    Returns the number of jobs enriched. Never raises."""
    targets = [j for j in jobs if needs_backfill(j)][:cap]
    if not targets:
        return 0
    filled = [0]

    def _one(j):
        text = full_description(j, timeout=timeout)
        if text and len(text) > len((j.get("description") or "").strip()):
            j["description"] = text
            filled[0] += 1

    try:
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=workers) as ex:
            list(ex.map(_one, targets))
    except Exception:
        for j in targets:                  # serial fallback, still guarded per job
            try:
                _one(j)
            except Exception:
                pass
    return filled[0]
