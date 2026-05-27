"""
Scheduled worker — keeps the job data fresh.

Runs the sourcing pull on an interval. Each cycle:
    1. pull from registry + seeds + curated lists
    2. grow the registry from newly-seen URLs
    3. sync to Postgres (upsert live jobs, mark vanished ones dead)  -- freshness
    4. (re)rank against stored profiles is left to the ranking job / API

This is the anti-staleness engine: the moment a role disappears from its ATS,
the next cycle marks it dead, so the feed never shows expired listings.

Run once (good for cron):
    python worker.py --once
Run as a loop (every N minutes, default 60):
    python worker.py --interval 60

Without DATABASE_URL it still pulls + writes ranked_jobs.json so the API has data.
"""
import argparse
import json
import time

import sources
import registry
import db

SEED_COMPANIES = [
    {"name": "Stripe",     "ats": "greenhouse", "token": "stripe"},
    {"name": "Databricks", "ats": "greenhouse", "token": "databricks"},
    {"name": "Ramp",       "ats": "ashby",      "token": "ramp"},
    {"name": "Notion",     "ats": "ashby",      "token": "notion"},
]


def cycle():
    """One full refresh cycle. Returns a small stats dict."""
    started = time.time()

    reg = registry.load()
    companies = {f"{c['ats']}:{c['token']}": c for c in SEED_COMPANIES}
    companies.update(reg)
    company_list = list(companies.values())

    print(f"[pull] {len(company_list)} companies + curated repo")
    jobs = sources.pull_all(company_list, include_repo=True)

    reg, n_new = registry.discover_from_jobs(jobs, reg)
    registry.save(reg)
    print(f"[registry] +{n_new} new -> {len(reg)} total")

    conn = db.connect()
    if conn:
        try:
            db.init_db(conn)
            upserted, dead = db.sync_jobs(conn, jobs)
            print(f"[db] upserted {upserted}, marked {dead} dead (freshness)")
        finally:
            conn.close()
    else:
        # no DB: still hand the API something to serve
        with open("ranked_jobs.json", "w") as f:
            json.dump(jobs, f, indent=2)
        print(f"[file] wrote {len(jobs)} jobs to ranked_jobs.json (no DATABASE_URL)")

    elapsed = round(time.time() - started, 1)
    print(f"[done] cycle in {elapsed}s\n")
    return {"pulled": len(jobs), "registry": len(reg), "seconds": elapsed}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="run a single cycle and exit")
    ap.add_argument("--interval", type=int, default=60, help="minutes between cycles")
    args = ap.parse_args()

    if args.once:
        cycle()
        return

    print(f"worker loop: every {args.interval} min (Ctrl-C to stop)\n")
    while True:
        try:
            cycle()
        except Exception as e:  # never let one bad cycle kill the loop
            print(f"[error] cycle failed: {e}")
        time.sleep(args.interval * 60)


if __name__ == "__main__":
    main()
