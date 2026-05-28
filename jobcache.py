"""
jobcache.py - persistent, compounding scan cache.

The whole point: never pay the LLM twice for the same posting. A job_id is a
stable hash of company|title|location, so the same posting keeps the same id
across runs even as the source list shuffles. Once a job is LLM-ranked, its
result lives here, and future runs reuse it for free.

Persisted in CACHE_FILE (default ranked_cache.json):
  - seen:    {job_id: first_seen_date}   -> lets us flag brand-new postings
  - ranked:  {job_id: fit_dict}          -> lets us SKIP paying to re-rank
  - drafts:  {job_id: draft_dict}        -> lets us skip paying to re-draft

PERSISTENCE (this is the fix for the live site):
  On an ephemeral host like Railway, the container disk is wiped on every
  redeploy/restart, so a cache written to the local disk is lost and the next
  refresh re-pays from scratch. Point CACHE_FILE at a mounted persistent volume
  so the cache survives and keeps compounding:
      CACHE_FILE=/data/ranked_cache.json

BOOTSTRAP (belt and suspenders):
  If the cache file is missing (fresh container or brand-new volume), we rebuild
  the 'ranked' and 'drafts' memory from the committed ranked_jobs.json feed. That
  file IS in your repo, so even a cold start with no volume already "knows" every
  job that was previously LLM-ranked, and the first refresh does not re-pay for
  them. We only trust real LLM rankings here, never the free heuristic ones, so a
  heuristic 'possible' can still be promoted to a verified 'strong' later.

NOTE for the future per-user build:
  Today there is one shared profile, so keying the cache by job_id alone is
  correct. When you add per-user profiles, the key must become
  (profile_id, job_id), because the same job scores differently per person.
"""
import datetime
import hashlib
import json
import os
import tempfile

CACHE_FILE = os.environ.get("CACHE_FILE", "ranked_cache.json")
# The committed feed used to bootstrap a cold cache. Stays at the repo path.
BOOTSTRAP_FEED = os.environ.get("BOOTSTRAP_FEED", "ranked_jobs.json")


def job_id(job):
    raw = f"{job.get('company','')}|{job.get('title','')}|{job.get('location','')}".lower()
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def today():
    return datetime.date.today().isoformat()


def _empty():
    return {"seen": {}, "ranked": {}, "drafts": {}}


def _is_llm_fit(fit):
    """True only for a real AI ranking, not the free heuristic placeholder.

    heuristic_fit() always tags its reasons with 'Keyword pre-match' /
    'Not yet verified by the AI', and never awards 'strong'. We must not cache
    those as if they were paid rankings, or a job could get stuck at 'possible'
    and never be verified once it rises into the top-N.
    """
    if not fit:
        return False
    blob = " ".join(fit.get("reasons") or []).lower()
    if "keyword pre-match" in blob or "not yet verified" in blob:
        return False
    return True


def _bootstrap_from_feed():
    """Seed a cold cache from the committed ranked_jobs.json so a fresh
    container/volume does not re-pay for jobs already ranked in the repo."""
    cache = _empty()
    if not os.path.exists(BOOTSTRAP_FEED):
        return cache
    try:
        with open(BOOTSTRAP_FEED) as f:
            jobs = json.load(f)
    except Exception:
        return cache
    day = today()
    for j in jobs:
        jid = j.get("_id") or job_id(j)
        cache["seen"].setdefault(jid, day)
        fit = j.get("fit")
        if _is_llm_fit(fit):
            cache["ranked"][jid] = fit
        d = j.get("draft")
        if d:                       # real draft dict, or non-empty string
            cache["drafts"][jid] = d
    return cache


def load():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                data = json.load(f)
            data.setdefault("seen", {})
            data.setdefault("ranked", {})
            data.setdefault("drafts", {})
            return data
        except Exception:
            pass
    # No cache file: fresh container or new volume. Seed from the committed feed.
    return _bootstrap_from_feed()


def save(cache):
    """Atomic write: serialize to a temp file then rename, so a crash or a second
    visitor triggering a refresh mid-write can never corrupt the cache."""
    cache.setdefault("seen", {})
    cache.setdefault("ranked", {})
    cache.setdefault("drafts", {})
    directory = os.path.dirname(CACHE_FILE) or "."
    os.makedirs(directory, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".cache-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(cache, f)
        os.replace(tmp, CACHE_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
