"""
Orchestrator. Runs the whole pipeline:

  profile -> pull jobs (registry + seeds) -> discover new companies
          -> prefilter (free) -> LLM rank (paid) -> ranked feed + contacts

Output: ranked_jobs.csv / ranked_jobs.json + a growing registry.json

Run:
    pip install -r requirements.txt
    python main.py                  # profile.example.json, dry run
    export ANTHROPIC_API_KEY=sk-...
    python main.py my_profile.json

Deliberately does NOT auto-apply or auto-send email. It surfaces the best-fit
roles + (later) the recruiter to contact; the user acts via a guided flow.
"""
import csv
import datetime
import json
import sys

import os

import sources
import registry
import prefilter
import rank
import enrich

# Seed companies (the registry grows itself from here). Edit / expand freely.
SEED_COMPANIES = [
    {"name": "Stripe",     "ats": "greenhouse", "token": "stripe"},
    {"name": "Databricks", "ats": "greenhouse", "token": "databricks"},
    {"name": "Ramp",       "ats": "ashby",      "token": "ramp"},
    {"name": "Notion",     "ats": "ashby",      "token": "notion"},
]


def load_profile(path):
    with open(path) as f:
        return json.load(f)


def enrich_contacts(jobs, limit=15):
    """Find recruiter/EM contacts for strong-tier jobs only (cost control).
    Degrades gracefully: with no APOLLO_API_KEY, leaves contacts empty."""
    for j in jobs:
        j["contacts"] = []
    if not os.environ.get("APOLLO_API_KEY"):
        print("  [no APOLLO_API_KEY] skipping contact enrichment.")
        return jobs
    strong = [j for j in jobs if (j.get("fit") or {}).get("tier") == "strong"][:limit]
    print(f"  enriching {len(strong)} strong-tier jobs...")
    for j in strong:
        j["contacts"] = enrich.find_contacts(j)
    return jobs


def fmt_date(ts):
    return datetime.date.fromtimestamp(ts).isoformat() if ts else ""


def main():
    profile_path = sys.argv[1] if len(sys.argv) > 1 else "profile.example.json"
    profile = load_profile(profile_path)
    print(f"Profile: {profile.get('name')} | targets: {', '.join(profile.get('target_titles', []))}\n")

    # Companies = seeds + everything the registry has learned so far
    reg = registry.load()
    companies = {f"{c['ats']}:{c['token']}": c for c in SEED_COMPANIES}
    companies.update({k: v for k, v in reg.items()})
    company_list = list(companies.values())
    print(f"Pulling jobs from {len(company_list)} known companies + curated repo...")
    jobs = sources.pull_all(company_list, include_repo=True)
    print(f"  total pulled: {len(jobs)}\n")

    # Learn new companies from the URLs we just saw
    reg, n_new = registry.discover_from_jobs(jobs, reg)
    registry.save(reg)
    print(f"Registry: +{n_new} new companies discovered -> {len(reg)} total known\n")

    print("Prefiltering...")
    jobs = prefilter.prefilter(jobs, profile)
    print(f"  survived prefilter: {len(jobs)}\n")

    print("Ranking (LLM)...")
    jobs = rank.run(jobs, profile)
    jobs = enrich_contacts(jobs)

    with open("ranked_jobs.json", "w") as f:
        json.dump(jobs, f, indent=2)
    with open("ranked_jobs.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["tier", "score", "company", "title", "location", "posted", "url", "reasons"])
        for j in jobs:
            fit = j.get("fit") or {}
            w.writerow([fit.get("tier", ""), fit.get("score", ""), j["company"], j["title"],
                        j["location"], fmt_date(j.get("date_posted")), j["url"],
                        " | ".join(fit.get("reasons", []))])
    print(f"\nDone. {len(jobs)} ranked roles -> ranked_jobs.csv / ranked_jobs.json")


if __name__ == "__main__":
    main()
