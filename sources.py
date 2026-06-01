"""
Job sources - multi-ATS backbone + self-growing company registry.

Each connector returns NORMALIZED job dicts:
    {
      "source": str, "company": str, "title": str, "location": str,
      "url": str, "description": str, "date_posted": int|None,
      "ats": str, "token": str
    }

THE KEY IDEA: every apply URL contains the company's ATS token. So every job we
ingest teaches us new companies (see registry.discover_from_jobs). The registry
compounds over time -- that's the asset.

ToS-friendly sources only. No LinkedIn/Handshake mass scraping (bans users).
"""
import html
import os
import re
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (job-finder)"}

# Multi-field switch (mirrors prefilter.MULTIFIELD). ON by default: the keyword-search
# sources fetch across professional fields, not tech only, and USAJOBS is pulled in
# pull_all. Set MULTIFIELD=off to revert to the tech-only behavior.
MULTIFIELD = os.environ.get("MULTIFIELD", "on").strip().lower() in ("1", "true", "on", "yes")

# Keyword sets for the search-based sources (Adzuna, USAJOBS). The tech set is the default
# and reproduces prior behavior; the broad set adds professional, resume-driven non-tech
# fields so one query pass can serve many kinds of candidate.
_TECH_QUERIES = ["software engineer", "backend engineer", "full stack engineer",
                 "frontend engineer", "mobile engineer", "data engineer",
                 "data scientist", "machine learning engineer", "devops engineer",
                 "security engineer", "data analyst"]
_BROAD_QUERIES = _TECH_QUERIES + [
    "registered nurse", "nurse practitioner", "physical therapist", "pharmacist",
    "accountant", "financial analyst", "auditor", "controller",
    "marketing manager", "digital marketing", "content strategist",
    "sales representative", "account executive", "business development",
    "human resources", "recruiter", "operations manager", "supply chain analyst",
    "project manager", "program manager", "business analyst", "management consultant",
    "attorney", "paralegal", "teacher", "professor",
    "graphic designer", "executive assistant", "customer success manager"]


def _clean(text, limit=12000):
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def _norm(source, company, title, location, url, description, date_posted, ats, token):
    return {"source": source, "company": company, "title": title, "location": location,
            "url": url, "description": description, "date_posted": date_posted,
            "ats": ats, "token": token}


def from_greenhouse(token, company=None):
    url = f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
    return [_norm("greenhouse", company or token, j.get("title", ""),
                  (j.get("location") or {}).get("name", ""), j.get("absolute_url", ""),
                  _clean(j.get("content", "")), None, "greenhouse", token)
            for j in r.json().get("jobs", [])]


def from_lever(token, company=None):
    url = f"https://api.lever.co/v0/postings/{token}?mode=json"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
    out = []
    for j in r.json():
        cats = j.get("categories") or {}
        out.append(_norm("lever", company or token, j.get("text", ""),
                         cats.get("location", ""), j.get("hostedUrl", ""),
                         _clean(j.get("descriptionPlain") or j.get("description", "")),
                         int(j.get("createdAt", 0) / 1000) or None, "lever", token))
    return out


def from_ashby(token, company=None):
    url = f"https://api.ashbyhq.com/posting-api/job-board/{token}?includeCompensation=true"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
    return [_norm("ashby", company or token, j.get("title", ""), j.get("location", ""),
                  j.get("jobUrl", ""), _clean(j.get("descriptionPlain") or j.get("descriptionHtml", "")),
                  None, "ashby", token)
            for j in r.json().get("jobs", [])]


def from_smartrecruiters(token, company=None):
    url = f"https://api.smartrecruiters.com/v1/companies/{token}/postings?limit=100"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
    out = []
    for j in r.json().get("content", []):
        loc = j.get("location", {}) or {}
        pid = j.get("id", "") or ""
        # The posting 'ref' is the API self-link (returns JSON, not a page). Build the
        # public careers URL so "Open the posting" lands on the real listing.
        human = f"https://jobs.smartrecruiters.com/{token}/{pid}" if pid \
            else (j.get("applyUrl", "") or j.get("ref", ""))
        out.append(_norm("smartrecruiters", company or token, j.get("name", ""),
                         f"{loc.get('city','')}, {loc.get('country','')}".strip(", "),
                         human, "",
                         None, "smartrecruiters", token))
    return out


def from_recruitee(token, company=None):
    url = f"https://{token}.recruitee.com/api/offers/"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
    return [_norm("recruitee", company or token, j.get("title", ""),
                  j.get("location", "") or j.get("city", ""), j.get("careers_url", ""),
                  _clean(j.get("description", "")), None, "recruitee", token)
            for j in r.json().get("offers", [])]


def from_workable(token, company=None):
    url = f"https://apply.workable.com/api/v1/widget/accounts/{token}?details=true"
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
    out = []
    for j in r.json().get("jobs", []):
        loc = j.get("location", {})
        out.append(_norm("workable", company or token, j.get("title", ""),
                         loc.get("city", "") if isinstance(loc, dict) else "",
                         j.get("application_url", "") or j.get("url", ""),
                         _clean(j.get("description", "")), None, "workable", token))
    return out


def from_workday(token, company=None):
    """Workday CXS connector. Public job boards, no auth, POST + offset pagination.

    Workday needs three parts (tenant, site, data-center server), so the registry
    token is stored as 'tenant/site/wdN' (e.g. 'nvidia/NVIDIAExternalCareerSite/wd5').
    If the server part is omitted, we try the common ones.
    """
    parts = (token or "").split("/")
    if len(parts) < 2:
        return []
    tenant, site = parts[0], parts[1]
    servers = [parts[2]] if len(parts) > 2 and parts[2] else ["wd1", "wd3", "wd5", "wd2", "wd103"]

    def _try(server):
        base = f"https://{tenant}.{server}.myworkdayjobs.com"
        api = f"{base}/wday/cxs/{tenant}/{site}/jobs"
        hdr = {**HEADERS, "Accept": "application/json", "Content-Type": "application/json",
               "Referer": f"{base}/en-US/{site}"}
        out, offset = [], 0
        for _ in range(20):                       # cap pages so one company can't run away
            payload = {"appliedFacets": {}, "limit": 20, "offset": offset, "searchText": ""}
            r = requests.post(api, json=payload, headers=hdr, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()
            postings = data.get("jobPostings", [])
            if not postings:
                break
            for j in postings:
                ext = j.get("externalPath", "") or ""
                out.append(_norm(
                    "workday", company or tenant, j.get("title", ""),
                    j.get("locationsText", "") or "",
                    f"{base}/en-US/{site}{ext}",
                    _clean(j.get("bulletFields", [""])[0] if j.get("bulletFields") else ""),
                    None, "workday", token))
            total = data.get("total", 0)
            offset += 20
            if offset >= total:
                break
        return out

    last_err = None
    for server in servers:
        try:
            jobs = _try(server)
            if jobs:
                return jobs
        except Exception as e:
            last_err = e
            continue
    if last_err:
        raise last_err
    return []


def from_adzuna(queries=None, country="us", pages=5, per_page=50):
    """Adzuna aggregator. Keyword-search across many job boards at once.

    Different shape from the ATS connectors: instead of one company per call, it
    queries by keyword and returns jobs from across Adzuna's index. Needs free
    credentials in env: ADZUNA_APP_ID and ADZUNA_APP_KEY (register at
    developer.adzuna.com). Returns [] quietly if keys are absent, so the pipeline
    runs fine without it.
    """
    app_id = os.environ.get("ADZUNA_APP_ID")
    app_key = os.environ.get("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        return []

    queries = queries or (_BROAD_QUERIES if MULTIFIELD else _TECH_QUERIES)
    out = []
    for what in queries:
        for page in range(1, pages + 1):
            url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/{page}"
            params = {"app_id": app_id, "app_key": app_key,
                      "results_per_page": per_page, "what": what,
                      "content-type": "application/json"}
            try:
                r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
                r.raise_for_status()
                results = r.json().get("results", [])
            except Exception:
                break          # stop this query on error (rate limit etc), keep others
            if not results:
                break
            for j in results:
                created = j.get("created", "")
                ts = None
                if created:
                    try:
                        import datetime
                        ts = int(datetime.datetime.fromisoformat(
                            created.replace("Z", "+00:00")).timestamp())
                    except Exception:
                        ts = None
                out.append(_norm(
                    "adzuna", (j.get("company") or {}).get("display_name", "") or "Unknown",
                    j.get("title", ""), (j.get("location") or {}).get("display_name", ""),
                    j.get("redirect_url", ""), _clean(j.get("description", "")),
                    ts, "adzuna", ""))
    return out


def from_usajobs(queries=None, pages=2, per_page=250):
    """USAJOBS aggregator: open US federal jobs across ALL fields (nursing, law, finance,
    trades, science, admin, IT, and more). Keyword-search, like Adzuna. Needs a free key
    plus the email you registered with, in env: USAJOBS_API_KEY and USAJOBS_EMAIL (register
    at developer.usajobs.gov). Returns [] quietly if either is missing, so the pipeline runs
    fine without it."""
    key = os.environ.get("USAJOBS_API_KEY")
    email = os.environ.get("USAJOBS_EMAIL")
    if not (key and email):
        return []
    queries = queries or _BROAD_QUERIES
    hdr = {**HEADERS, "Host": "data.usajobs.gov", "User-Agent": email,
           "Authorization-Key": key, "Accept": "application/json"}
    out = []
    for what in queries:
        for page in range(1, pages + 1):
            params = {"Keyword": what, "ResultsPerPage": per_page, "Page": page}
            try:
                r = requests.get("https://data.usajobs.gov/api/search",
                                 params=params, headers=hdr, timeout=TIMEOUT)
                r.raise_for_status()
                items = r.json().get("SearchResult", {}).get("SearchResultItems", []) or []
            except Exception:
                break          # stop this query on error (rate limit etc), keep the rest
            if not items:
                break
            for it in items:
                d = it.get("MatchedObjectDescriptor", {}) or {}
                loc = d.get("PositionLocationDisplay", "") or ""
                summary = d.get("QualificationSummary", "") or \
                    ((d.get("UserArea") or {}).get("Details") or {}).get("JobSummary", "")
                pub = d.get("PublicationStartDate", "") or ""
                ts = None
                if pub:
                    try:
                        import datetime
                        ts = int(datetime.datetime.fromisoformat(
                            pub.replace("Z", "+00:00")).timestamp())
                    except Exception:
                        ts = None
                out.append(_norm(
                    "usajobs", d.get("OrganizationName", "") or "U.S. Government",
                    d.get("PositionTitle", ""), loc, d.get("PositionURI", ""),
                    _clean(summary), ts, "", ""))
            if len(items) < per_page:
                break
    return out


def from_simplify_repo():
    """Curated new-grad list. Also a great seed for the registry (URLs -> tokens)."""
    url = ("https://raw.githubusercontent.com/SimplifyJobs/"
           "New-Grad-Positions/dev/.github/scripts/listings.json")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
    out = []
    for j in r.json():
        if not (j.get("active") and j.get("is_visible")):
            continue
        out.append(_norm("simplify_repo", j.get("company_name", ""), j.get("title", ""),
                         "; ".join(j.get("locations", [])), j.get("url", ""), "",
                         j.get("date_posted"), "", ""))
    return out


def from_vansh_repo():
    """Second free, daily-updated new-grad list (vanshb03/New-Grad-2027). Same
    schema as the Simplify repo (company_name/title/locations/url/date_posted/
    active/is_visible), US + Canada + Remote, SWE/quant/PM. Pure additional
    coverage; pull_all dedupes it against everything else so overlaps are dropped."""
    url = ("https://raw.githubusercontent.com/vanshb03/"
           "New-Grad-2027/dev/.github/scripts/listings.json")
    r = requests.get(url, headers=HEADERS, timeout=TIMEOUT); r.raise_for_status()
    out = []
    for j in r.json():
        if not (j.get("active") and j.get("is_visible")):
            continue
        out.append(_norm("vansh_repo", j.get("company_name", ""), j.get("title", ""),
                         "; ".join(j.get("locations", [])), j.get("url", ""), "",
                         j.get("date_posted"), "", ""))
    return out


ATS = {"greenhouse": from_greenhouse, "lever": from_lever, "ashby": from_ashby,
       "smartrecruiters": from_smartrecruiters, "recruitee": from_recruitee,
       "workable": from_workable, "workday": from_workday}


def pull_all(companies, include_repo=True, max_workers=20):
    """Pull every company's jobs in parallel. ~20x faster than sequential."""
    jobs = []

    def _pull(c):
        fn = ATS.get(c["ats"])
        if not fn:
            return c, None, "unknown ats"
        try:
            return c, fn(c["token"], c["name"]), None
        except Exception as e:
            return c, None, str(e)

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_pull, c) for c in companies]
        done = 0
        for fut in as_completed(futures):
            c, got, err = fut.result()
            done += 1
            if err:
                continue  # quietly skip dead boards; they're common and noisy
            jobs.extend(got)
            if done % 25 == 0:
                print(f"  pulled {done}/{len(companies)} companies, {len(jobs)} jobs so far")

    if include_repo:
        try:
            got = from_simplify_repo(); jobs.extend(got)
            print(f"  {'SimplifyRepo':<18} {len(got):>4} (new-grad list)")
        except Exception as e:
            print(f"  ! simplify repo failed: {e}")

        # Second free new-grad list (vanshb03). Dedup against what we have by
        # (company+title) and url, so roles already pulled above aren't doubled.
        try:
            vg = from_vansh_repo()
            if vg:
                seen_ct = {((j.get("company") or "").lower().strip(),
                            (j.get("title") or "").lower().strip()) for j in jobs}
                seen_url = {j.get("url") for j in jobs if j.get("url")}
                fresh = [j for j in vg
                         if ((j.get("company") or "").lower().strip(),
                             (j.get("title") or "").lower().strip()) not in seen_ct
                         and j.get("url") not in seen_url]
                jobs.extend(fresh)
                print(f"  {'VanshRepo':<18} {len(fresh):>4} (new-grad list, after dedup)")
        except Exception as e:
            print(f"  ! vansh repo failed: {e}")

    # Adzuna aggregator (only runs if ADZUNA_APP_ID / ADZUNA_APP_KEY are set)
    try:
        ad = from_adzuna()
        if ad:
            # dedup against what we already have, by (company+title) and by url
            seen_ct = {((j.get("company") or "").lower().strip(),
                        (j.get("title") or "").lower().strip()) for j in jobs}
            seen_url = {j.get("url") for j in jobs if j.get("url")}
            fresh = [j for j in ad
                     if ((j.get("company") or "").lower().strip(),
                         (j.get("title") or "").lower().strip()) not in seen_ct
                     and j.get("url") not in seen_url]
            jobs.extend(fresh)
            print(f"  {'Adzuna':<18} {len(fresh):>4} (aggregator, after dedup)")
    except Exception as e:
        print(f"  ! adzuna failed: {e}")

    # USAJOBS (US federal, every field) - only in multi-field mode, only when keyed.
    if MULTIFIELD:
        try:
            uj = from_usajobs()
            if uj:
                seen_ct = {((j.get("company") or "").lower().strip(),
                            (j.get("title") or "").lower().strip()) for j in jobs}
                seen_url = {j.get("url") for j in jobs if j.get("url")}
                fresh = [j for j in uj
                         if ((j.get("company") or "").lower().strip(),
                             (j.get("title") or "").lower().strip()) not in seen_ct
                         and j.get("url") not in seen_url]
                jobs.extend(fresh)
                print(f"  {'USAJOBS':<18} {len(fresh):>4} (federal, after dedup)")
        except Exception as e:
            print(f"  ! usajobs failed: {e}")

    return jobs


# ===================================================================================
# Manual JSON upload (hiring.cafe export) -> canonical job dicts
# -----------------------------------------------------------------------------------
# The owner can upload a batch of jobs (e.g. a hiring.cafe export) and have them
# ingested through the SAME prefilter + free scoring as every live source, so an
# uploaded role is scored byte-for-byte like a polled one. This module only does the
# shape conversion; merging/dedup/scoring lives in the pipeline and the server.
# ===================================================================================

# hiring.cafe abbreviates the underlying ATS; normalize to the same source keys our
# live connectors use so cards and the coverage page read naturally and consistently.
_HC_SOURCE_MAP = {
    "grnhse": "greenhouse", "greenhouse": "greenhouse",
    "lever": "lever",
    "ashby": "ashby",
    "smartrecruiters": "smartrecruiters", "smartr": "smartrecruiters",
    "recruitee": "recruitee",
    "workable": "workable",
    "workday": "workday", "wd": "workday",
    "icims": "icims", "icims2": "icims",
    "successfactors": "successfactors", "sf": "successfactors",
    "adp": "adp",
    "paylocity": "paylocity",
    "ultipro": "ultipro", "ukg": "ultipro",
    "oraclecloud": "oraclecloud", "oracle": "oraclecloud",
    "jazzhr": "jazzhr",
    "paycor": "paycor",
    "dayforce": "dayforce",
    "jobvite": "jobvite",
    "bamboohr": "bamboohr", "bamboo": "bamboohr",
    "breezy": "breezy",
    "ashbyhq": "ashby",
}


def _hc_clean(v):
    """Treat empty/missing/whitespace as unknown (None). Never invents data."""
    if v is None:
        return None
    s = str(v).strip()
    return s or None


def _hc_iso_to_epoch(s):
    """ISO date/datetime (e.g. 2026-06-01T01:58:35Z) -> epoch seconds, or None.
    Feeds the same date_posted -> posted_ts freshness label every source uses."""
    s = _hc_clean(s)
    if not s:
        return None
    try:
        import datetime
        t = s.replace("Z", "+00:00")
        return int(datetime.datetime.fromisoformat(t).timestamp())
    except Exception:
        pass
    try:
        import datetime
        d = datetime.datetime.strptime(s[:10], "%Y-%m-%d")
        return int(d.replace(tzinfo=datetime.timezone.utc).timestamp())
    except Exception:
        return None


def _hc_build_description(rec):
    """Compose one readable description from the structured fields, because the
    free scorer AND the AI ranker both read job['description']. We fold in the
    requirement summary, what you'd do, the skills, and the key constraints, so an
    uploaded role carries as much signal to the scorer as a live posting's text.
    Only includes fields that are actually present; never fabricates."""
    parts = []
    rs = _hc_clean(rec.get("requirements_summary"))
    if rs:
        parts.append("Requirements: " + rs)
    ra = _hc_clean(rec.get("role_activities"))
    if ra:
        parts.append("Responsibilities: " + ra)
    sk = _hc_clean(rec.get("skills"))
    if sk:
        parts.append("Skills: " + sk.replace(";", ", "))
    bits = []
    sen = _hc_clean(rec.get("seniority"))
    if sen:
        bits.append("Seniority: " + sen)
    yoe = rec.get("min_yoe")
    if yoe not in (None, "", "unknown"):
        try:
            bits.append("Minimum experience: %d years" % int(float(yoe)))
        except Exception:
            pass
    deg = _hc_clean(rec.get("bachelors_required"))
    if deg:
        df = _hc_clean(rec.get("degree_fields"))
        bits.append("Degree: %s%s" % (deg, (" (" + df + ")") if df else ""))
    wt = _hc_clean(rec.get("workplace_type"))
    if wt:
        bits.append("Workplace: " + wt)
    com = _hc_clean(rec.get("commitment"))
    if com:
        bits.append("Commitment: " + com)
    vs = rec.get("visa_sponsorship")
    if vs not in (None, "", "unknown"):
        bits.append("Visa sponsorship: " + ("yes" if str(vs).strip().lower() in ("true", "yes", "1") else "no"))
    sc = _hc_clean(rec.get("security_clearance"))
    if sc and sc.lower() not in ("none", "no"):
        bits.append("Security clearance: " + sc)
    if bits:
        parts.append(" | ".join(bits))
    return "\n\n".join(parts)


def _hc_salary(rec):
    """Structured salary from the export as a salary dict, or None. Stored on the
    job (round-trips in the pool JSON) but NOT rendered today; bounds-checked."""
    lo, hi = rec.get("salary_min"), rec.get("salary_max")
    try:
        lo = float(lo) if lo not in (None, "", "unknown") else None
        hi = float(hi) if hi not in (None, "", "unknown") else None
    except Exception:
        return None
    if not lo and not hi:
        return None
    lo = lo or hi
    hi = hi or lo
    if lo <= 0 or hi <= 0 or hi < lo:
        return None
    freq = str(rec.get("salary_frequency") or "yearly").lower()
    period = "hour" if "hour" in freq or freq in ("hourly", "hr") else "year"
    cur = (_hc_clean(rec.get("salary_currency")) or "USD").upper()
    return {"min": lo, "max": hi, "currency": cur, "period": period, "estimated": False}


def from_hiring_cafe(records):
    """Convert a hiring.cafe-style export (list of dicts) into canonical job dicts.

    - Skips ad rows (source == 'hiring_cafe_pin').
    - Skips rows with no title, company, or apply_url (nothing to rank or apply to).
    - De-dupes WITHIN the batch by our standard company|title|location identity and
      by apply_url, so a messy file with repeats yields each role once.
    Returns (jobs, stats) where stats explains what was kept/dropped, for the UI."""
    if not isinstance(records, list):
        raise ValueError("uploaded JSON must be a list of job objects")
    out = []
    seen_id, seen_url = set(), set()
    n_total = len(records)
    n_pin = n_missing = n_dupe = 0
    for rec in records:
        if not isinstance(rec, dict):
            continue
        src_raw = (str(rec.get("source") or "").strip().lower())
        if src_raw == "hiring_cafe_pin":
            n_pin += 1
            continue
        title = _hc_clean(rec.get("title"))
        company = _hc_clean(rec.get("company"))
        url = _hc_clean(rec.get("apply_url"))
        if not title or not company or not url:
            n_missing += 1
            continue
        location = _hc_clean(rec.get("location")) or ""
        ident = "|".join(x.lower().strip() for x in (company, title, location))
        if ident in seen_id or url in seen_url:
            n_dupe += 1
            continue
        seen_id.add(ident)
        seen_url.add(url)

        source = _HC_SOURCE_MAP.get(src_raw, src_raw or "upload")
        token = _hc_clean(rec.get("board_token")) or _hc_clean(rec.get("company_website")) or company
        job = _norm(
            source=source, company=company, title=title, location=location,
            url=url, description=_hc_build_description(rec),
            date_posted=_hc_iso_to_epoch(rec.get("estimated_post_date")),
            ats=source, token=token,
        )
        sal = _hc_salary(rec)
        if sal:
            job["salary"] = sal          # carried in the pool; not shown on cards today
        job["_uploaded"] = True          # provenance marker, harmless to scoring/UI
        out.append(job)
    stats = {"received": n_total, "ads_skipped": n_pin, "missing_fields": n_missing,
             "batch_duplicates": n_dupe, "converted": len(out)}
    return out, stats
