"""
seed.py — widen the company registry (the v2 "coverage" lever).

The ranking engine is only as good as the set of companies that enter the funnel.
This script grows that set: it takes candidate companies (a built-in starter list,
or a file you provide), VALIDATES each one by actually hitting its ATS board, and
adds only the ones that really return jobs to registry.json.

Why validation matters: a guessed token like "greenhouse:strpe" (typo) or a company
that has since moved off Greenhouse would otherwise pollute the registry and waste
pull time. We confirm each board is live before trusting it.

COST: $0 in API. This only makes plain HTTP calls to public ATS endpoints — the
same calls the normal pull makes. No LLM is involved. It does not touch your
Anthropic or Apollo keys.

SPEED: validation runs in parallel (default 20 workers), so even a few hundred
candidates check in well under a minute.

Usage:
    python3 seed.py                  # validate + add the built-in starter list
    python3 seed.py companies.txt    # also validate + add entries from a file
    python3 seed.py --dry-run        # show what WOULD be added, change nothing

File format (one per line, ATS and token, optional name after a comma):
    greenhouse  stripe              Stripe
    lever       netflix
    ashby       ramp                Ramp
    # lines starting with # are ignored
"""
import os
import sys
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

import registry
import sources

# ---------------------------------------------------------------- starter list
# A curated set of well-known companies (many hire new grads / interns) across the
# six supported ATS platforms. Tokens are validated at runtime, so a stale one is
# simply skipped rather than trusted. Extend this freely, or pass your own file.
STARTER = [
    # --- greenhouse ---
    ("greenhouse", "stripe", "Stripe"),
    ("greenhouse", "databricks", "Databricks"),
    ("greenhouse", "airbnb", "Airbnb"),
    ("greenhouse", "robinhood", "Robinhood"),
    ("greenhouse", "coinbase", "Coinbase"),
    ("greenhouse", "instacart", "Instacart"),
    ("greenhouse", "dropbox", "Dropbox"),
    ("greenhouse", "cloudflare", "Cloudflare"),
    ("greenhouse", "doordash", "DoorDash"),
    ("greenhouse", "lyft", "Lyft"),
    ("greenhouse", "pinterest", "Pinterest"),
    ("greenhouse", "reddit", "Reddit"),
    ("greenhouse", "twitch", "Twitch"),
    ("greenhouse", "samsara", "Samsara"),
    ("greenhouse", "affirm", "Affirm"),
    ("greenhouse", "gusto", "Gusto"),
    ("greenhouse", "asana", "Asana"),
    ("greenhouse", "figma", "Figma"),
    ("greenhouse", "snowflake", "Snowflake"),
    ("greenhouse", "datadog", "Datadog"),
    ("greenhouse", "hashicorp", "HashiCorp"),
    ("greenhouse", "mongodb", "MongoDB"),
    ("greenhouse", "okta", "Okta"),
    ("greenhouse", "twilio", "Twilio"),
    ("greenhouse", "plaid", "Plaid"),
    ("greenhouse", "brex", "Brex"),
    ("greenhouse", "discord", "Discord"),
    ("greenhouse", "anthropic", "Anthropic"),
    ("greenhouse", "openai", "OpenAI"),
    ("greenhouse", "scaleai", "Scale AI"),
    ("greenhouse", "benchling", "Benchling"),
    ("greenhouse", "gitlab", "GitLab"),
    ("greenhouse", "applovin", "AppLovin"),
    ("greenhouse", "niantic", "Niantic"),
    ("greenhouse", "flexport", "Flexport"),
    ("greenhouse", "chime", "Chime"),
    ("greenhouse", "sofi", "SoFi"),
    ("greenhouse", "nerdwallet", "NerdWallet"),
    ("greenhouse", "wealthfront", "Wealthfront"),
    ("greenhouse", "rippling", "Rippling"),
    # --- lever ---
    ("lever", "netflix", "Netflix"),
    ("lever", "spotify", "Spotify"),
    ("lever", "palantir", "Palantir"),
    ("lever", "kayak", "KAYAK"),
    ("lever", "plaid", "Plaid"),
    ("lever", "ramp", "Ramp"),
    ("lever", "attentive", "Attentive"),
    ("lever", "fanatics", "Fanatics"),
    # --- ashby ---
    ("ashby", "ramp", "Ramp"),
    ("ashby", "notion", "Notion"),
    ("ashby", "linear", "Linear"),
    ("ashby", "vercel", "Vercel"),
    ("ashby", "openstore", "OpenStore"),
    ("ashby", "mercury", "Mercury"),
    ("ashby", "clipboardhealth", "Clipboard Health"),
    ("ashby", "cresta", "Cresta"),
    ("ashby", "watershed", "Watershed"),
    ("ashby", "hex", "Hex"),
    ("ashby", "modal", "Modal"),
    ("ashby", "baseten", "Baseten"),
    ("ashby", "perplexity", "Perplexity"),
    ("ashby", "together", "Together AI"),
    ("ashby", "runway", "Runway"),
    # --- smartrecruiters ---
    ("smartrecruiters", "Square", "Square"),
    ("smartrecruiters", "Visa", "Visa"),
    ("smartrecruiters", "Bosch", "Bosch"),
    # --- workable ---
    ("workable", "remote", "Remote"),
]


def parse_file(path):
    out = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # name may be given after a comma, OR as the words after ats+token
            head, _, after_comma = line.partition(",")
            parts = head.split()
            if len(parts) < 2:
                continue
            ats = parts[0].lower()
            # SmartRecruiters tokens are case-sensitive; others normalize to lower.
            token = parts[1] if ats == "smartrecruiters" else parts[1].lower()
            if after_comma.strip():
                name = after_comma.strip()
            elif len(parts) > 2:
                name = " ".join(parts[2:])
            else:
                name = parts[1]
            if ats in sources.ATS:
                out.append((ats, token, name))
    return out


def validate(candidate):
    """Hit the real ATS board. Return (ats, token, name, n_jobs) if it works, else None."""
    ats, token, name = candidate
    fn = sources.ATS.get(ats)
    if not fn:
        return None
    try:
        jobs = fn(token, name)
        if jobs:                       # only trust boards that actually return roles
            return (ats, token, name, len(jobs))
    except Exception:
        return None
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    dry = "--dry-run" in sys.argv

    candidates = list(STARTER)
    for path in args:
        if not os.path.exists(path):
            print(f"  (skipping '{path}' — not a file)")
            continue
        candidates += parse_file(path)

    # de-dupe candidates by (ats, token)
    seen = set()
    uniq = []
    for c in candidates:
        k = (c[0], c[1])
        if k not in seen:
            seen.add(k)
            uniq.append(c)

    reg = registry.load()
    before = len(reg)
    # skip ones already known
    todo = [c for c in uniq if f"{c[0]}:{c[1]}" not in reg]
    print(f"Registry has {before} companies. Validating {len(todo)} new candidates "
          f"(in parallel, $0 API cost)...\n")

    added, failed = 0, 0
    with ThreadPoolExecutor(max_workers=20) as ex:
        futures = {ex.submit(validate, c): c for c in todo}
        for fut in as_completed(futures):
            res = fut.result()
            c = futures[fut]
            if res:
                ats, token, name, n = res
                if not dry:
                    reg[f"{ats}:{token}"] = {"name": name, "ats": ats, "token": token}
                added += 1
                print(f"  ✓ {name:<22} {ats}:{token}  ({n} jobs live)")
            else:
                failed += 1
                print(f"  ✗ {c[2]:<22} {c[0]}:{c[1]}  (no live board, skipped)")

    if not dry:
        registry.save(reg)
    print(f"\n{'DRY RUN — nothing saved. ' if dry else ''}"
          f"Added {added}, skipped {failed}. "
          f"Registry now {before + (0 if dry else added)} companies.")
    if not dry and added:
        print("Next run of main.py will pull from all of them automatically.")


if __name__ == "__main__":
    main()
