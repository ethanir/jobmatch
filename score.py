"""
Free heuristic scorer — ranks every job with ZERO API cost.
"""
import re
import time

SENIOR_RX = re.compile(
    r"\bsenior\b|\bstaff\b|\bprincipal\b|\blead\b|\bmanager\b|\bdirector\b|"
    r"\bvp\b|\bhead of\b|\bsr\.?\b|\b(iii|iv|v)\b", re.I)
NEWGRAD_RX = re.compile(
    r"new.?grad|early career|entry.?level|\bassociate\b|\bgraduate\b|"
    r"\bjunior\b|university grad|\b(i|1)\b", re.I)


def _flat_skills(profile):
    s = profile.get("skills", {}) or {}
    out = []
    for k in ("languages", "frameworks", "tools", "databases"):
        out += [str(x).lower() for x in (s.get(k) or []) if x]
    return out


def heuristic_score(job, skills, titles, locs):
    title = job.get("title", "") or ""
    tl = title.lower()
    blob = (title + " " + (job.get("description", "") or ""))[:6000].lower()

    score = 0
    matched = [s for s in skills if s and s in blob]
    score += min(len(matched), 12) * 4

    if any(t in tl for t in titles):
        score += 20
    if NEWGRAD_RX.search(title):
        score += 18
    if SENIOR_RX.search(title):
        score -= 45

    loc = (job.get("location", "") or "").lower()
    if "remote" in loc or any(l in loc for l in locs):
        score += 12

    dp = job.get("date_posted")
    if dp:
        days = (time.time() - dp) / 86400
        if days < 14:
            score += 10
        elif days < 45:
            score += 5

    return score, matched


def rank_free(jobs, profile):
    skills = _flat_skills(profile)
    titles = [t.lower() for t in (profile.get("target_titles") or [])] or \
             ["software engineer", "developer", "full stack", "backend"]
    pref = profile.get("preferences") or {}
    locs = [l.lower() for l in (pref.get("locations") or [])]

    for j in jobs:
        s, m = heuristic_score(j, skills, titles, locs)
        j["_score"] = s
        j["_matched"] = m
    jobs.sort(key=lambda j: j["_score"], reverse=True)
    return jobs


def heuristic_fit(job):
    s = job.get("_score", 0)
    tier = "strong" if s >= 55 else "possible" if s >= 30 else "skip"
    matched = job.get("_matched", [])
    return {
        "score": max(0, min(100, s)),
        "tier": tier,
        "reasons": [f"Heuristic match: {len(matched)} of your skills appear in this role"
                    + (f" ({', '.join(matched[:5])})" if matched else "")],
        "hard_disqualifiers": [],
        "matched_skills": matched,
        "missing_skills": [],
    }
