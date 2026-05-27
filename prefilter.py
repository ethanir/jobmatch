"""
Cheap, fast, FREE prefilter. Runs before the LLM so we never pay to rank
thousands of obviously-wrong jobs. Rule-based only: title sanity + light
location/keyword checks against the profile.

The LLM (rank.py) does the nuanced scoring on whatever survives here.
"""
import re

SWE_RX = re.compile(
    r"software|engineer|developer|backend|back.?end|front.?end|full.?stack|swe|"
    r"web|platform|infrastructure|programmer",
    re.I,
)
SENIOR_RX = re.compile(
    r"\bsenior\b|\bstaff\b|\bprincipal\b|\blead\b|\bmanager\b|\bdirector\b|"
    r"\bvp\b|\bhead of\b|\barchitect\b|\bsr\.?\b|\b(ii|iii|iv|v)\b|\b[2-9]\+?\b\s*years",
    re.I,
)


def prefilter(jobs, profile, max_years_for_entry=2):
    """Return only jobs worth sending to the LLM."""
    years = profile.get("years_experience") or 0
    pref = profile.get("preferences") or {}
    pref_locs = [l.lower() for l in (pref.get("locations") or [])]
    remote_ok = pref.get("remote_ok", True)

    kept = []
    for j in jobs:
        title = j.get("title", "")
        if not SWE_RX.search(title):
            continue
        # if candidate is early-career, drop senior-coded titles
        if years <= max_years_for_entry and SENIOR_RX.search(title):
            continue
        # light location gate (only if the candidate specified locations and isn't remote-open)
        loc = (j.get("location") or "").lower()
        if pref_locs and not remote_ok:
            if not (any(p in loc for p in pref_locs) or "remote" in loc):
                continue
        kept.append(j)

    # de-dupe by (company, title)
    seen, deduped = set(), []
    for j in kept:
        key = (j["company"].lower().strip(), j["title"].lower().strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    return deduped
