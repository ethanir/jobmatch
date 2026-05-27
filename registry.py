"""
The company registry — the compounding asset.

Every apply URL contains the company's ATS token. So every batch of jobs we pull
teaches us new companies to pull from next time. The registry literally grows
itself. Persisted to registry.json.

    boards.greenhouse.io/TOKEN            -> greenhouse
    jobs.lever.co/TOKEN                   -> lever
    jobs.ashbyhq.com/TOKEN  (or api...)   -> ashby
    TOKEN.recruitee.com                   -> recruitee
    apply.workable.com/TOKEN              -> workable
    jobs.smartrecruiters.com/TOKEN        -> smartrecruiters
"""
import json
import os
import re

REGISTRY_PATH = "registry.json"

# (regex over a URL) -> ats name; capture group 1 is the token
PATTERNS = [
    (re.compile(r"boards\.greenhouse\.io/([^/?#]+)", re.I), "greenhouse"),
    (re.compile(r"job-boards\.greenhouse\.io/([^/?#]+)", re.I), "greenhouse"),
    (re.compile(r"jobs\.lever\.co/([^/?#]+)", re.I), "lever"),
    (re.compile(r"jobs\.ashbyhq\.com/([^/?#]+)", re.I), "ashby"),
    (re.compile(r"([a-z0-9-]+)\.recruitee\.com", re.I), "recruitee"),
    (re.compile(r"apply\.workable\.com/([^/?#]+)", re.I), "workable"),
    (re.compile(r"jobs\.smartrecruiters\.com/([^/?#]+)", re.I), "smartrecruiters"),
]


def load():
    if os.path.exists(REGISTRY_PATH):
        with open(REGISTRY_PATH) as f:
            return json.load(f)
    return {}  # key: f"{ats}:{token}" -> {"name","ats","token"}


def save(reg):
    with open(REGISTRY_PATH, "w") as f:
        json.dump(reg, f, indent=2, sort_keys=True)


def token_from_url(url):
    """Return (ats, token) if the URL matches a known ATS pattern, else None."""
    if not url:
        return None
    for rx, ats in PATTERNS:
        m = rx.search(url)
        if m:
            token = m.group(1).strip("/").lower()
            if token and token not in ("www", "api"):
                return ats, token
    return None


def discover_from_jobs(jobs, reg=None):
    """Scan job URLs, add any newly-seen companies to the registry. Returns (reg, n_new)."""
    reg = reg if reg is not None else load()
    new = 0
    for j in jobs:
        hit = token_from_url(j.get("url", ""))
        if not hit:
            continue
        ats, token = hit
        key = f"{ats}:{token}"
        if key not in reg:
            reg[key] = {"name": j.get("company") or token, "ats": ats, "token": token}
            new += 1
    return reg, new


def as_company_list(reg=None):
    """Registry -> the list shape pull_all() expects."""
    reg = reg if reg is not None else load()
    return [{"name": v["name"], "ats": v["ats"], "token": v["token"]} for v in reg.values()]
