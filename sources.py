"""
Job sources — multi-ATS backbone + self-growing company registry.

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
import re
import time
import requests

TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (job-finder)"}


def _clean(text, limit=4000):
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
        out.append(_norm("smartrecruiters", company or token, j.get("name", ""),
                         f"{loc.get('city','')}, {loc.get('country','')}".strip(", "),
                         j.get("ref", "") or j.get("applyUrl", ""), "",
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


ATS = {"greenhouse": from_greenhouse, "lever": from_lever, "ashby": from_ashby,
       "smartrecruiters": from_smartrecruiters, "recruitee": from_recruitee,
       "workable": from_workable}


def pull_all(companies, include_repo=True):
    jobs = []
    for c in companies:
        fn = ATS.get(c["ats"])
        if not fn:
            print(f"  ! unknown ats '{c['ats']}' for {c['name']}"); continue
        try:
            got = fn(c["token"], c["name"]); jobs.extend(got)
            print(f"  {c['name']:<18} {len(got):>4} ({c['ats']})")
        except Exception as e:
            print(f"  ! {c['name']} failed: {e}")
        time.sleep(0.3)
    if include_repo:
        try:
            got = from_simplify_repo(); jobs.extend(got)
            print(f"  {'SimplifyRepo':<18} {len(got):>4} (new-grad list)")
        except Exception as e:
            print(f"  ! simplify repo failed: {e}")
    return jobs
