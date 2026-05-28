"""
bulk_seed.py — the "scan way more" upgrade.

This is a large curated list of companies known to post on the ATS platforms we
support (Greenhouse, Lever, Ashby). It feeds them through the SAME validation as
seed.py — each candidate is checked against its live board, and only the ones that
actually return jobs are added to the registry.

WHY THIS IS THE RIGHT LEVER:
- Coverage is the one real ceiling on match quality. More companies in the funnel
  = more chances at a 90+ match.
- It reuses existing connectors, so there is no new fragile code path.
- It costs $0 in API (plain HTTP, no LLM) and runs in parallel, so even hundreds
  of companies validate in well under a minute.
- The expensive LLM step is still capped by TOP_N, so adding companies does NOT
  raise your ranking cost or make runs slow. Pull time grows a little; ranking
  cost and speed stay flat.

USAGE:
    python3 bulk_seed.py --dry-run     # validate + preview, change nothing
    python3 bulk_seed.py               # validate + add the live ones

After running, the next `python3 main.py my_profile.json` automatically pulls from
every newly added company.

NOTE: ATS tokens drift over time (companies move platforms / change slugs), so
expect a chunk to be skipped as "no live board". That is the validation doing its
job — only confirmed-live boards are trusted. Re-run anytime; already-known and
dead tokens are skipped automatically.
"""
import sys

import seed
import registry

# ---------------------------------------------------------------------------
# Large curated candidate list. Format: (ats, token, "Display Name").
# These are well-known companies that hire SWE new grads / interns. Tokens are
# validated at runtime, so stale ones are simply skipped, never trusted.
# ---------------------------------------------------------------------------
CANDIDATES = [
    # ===================== GREENHOUSE =====================
    ("greenhouse", "stripe", "Stripe"),
    ("greenhouse", "databricks", "Databricks"),
    ("greenhouse", "airbnb", "Airbnb"),
    ("greenhouse", "robinhood", "Robinhood"),
    ("greenhouse", "instacart", "Instacart"),
    ("greenhouse", "dropbox", "Dropbox"),
    ("greenhouse", "cloudflare", "Cloudflare"),
    ("greenhouse", "lyft", "Lyft"),
    ("greenhouse", "pinterest", "Pinterest"),
    ("greenhouse", "reddit", "Reddit"),
    ("greenhouse", "twitch", "Twitch"),
    ("greenhouse", "samsara", "Samsara"),
    ("greenhouse", "affirm", "Affirm"),
    ("greenhouse", "gusto", "Gusto"),
    ("greenhouse", "asana", "Asana"),
    ("greenhouse", "figma", "Figma"),
    ("greenhouse", "datadog", "Datadog"),
    ("greenhouse", "mongodb", "MongoDB"),
    ("greenhouse", "okta", "Okta"),
    ("greenhouse", "twilio", "Twilio"),
    ("greenhouse", "brex", "Brex"),
    ("greenhouse", "discord", "Discord"),
    ("greenhouse", "anthropic", "Anthropic"),
    ("greenhouse", "scaleai", "Scale AI"),
    ("greenhouse", "gitlab", "GitLab"),
    ("greenhouse", "applovin", "AppLovin"),
    ("greenhouse", "flexport", "Flexport"),
    ("greenhouse", "chime", "Chime"),
    ("greenhouse", "sofi", "SoFi"),
    ("greenhouse", "wealthsimple", "Wealthsimple"),
    ("greenhouse", "doordashusa", "DoorDash"),
    ("greenhouse", "airtable", "Airtable"),
    ("greenhouse", "amplitude", "Amplitude"),
    ("greenhouse", "benchling", "Benchling"),
    ("greenhouse", "blend", "Blend"),
    ("greenhouse", "bolt", "Bolt"),
    ("greenhouse", "calendly", "Calendly"),
    ("greenhouse", "carta", "Carta"),
    ("greenhouse", "checkr", "Checkr"),
    ("greenhouse", "clari", "Clari"),
    ("greenhouse", "cohere", "Cohere"),
    ("greenhouse", "color", "Color"),
    ("greenhouse", "confluent", "Confluent"),
    ("greenhouse", "convoy", "Convoy"),
    ("greenhouse", "coursera", "Coursera"),
    ("greenhouse", "creditkarma", "Credit Karma"),
    ("greenhouse", "discordapp", "Discord"),
    ("greenhouse", "doximity", "Doximity"),
    ("greenhouse", "duolingo", "Duolingo"),
    ("greenhouse", "elastic", "Elastic"),
    ("greenhouse", "faire", "Faire"),
    ("greenhouse", "fivetran", "Fivetran"),
    ("greenhouse", "gemini", "Gemini"),
    ("greenhouse", "grammarly", "Grammarly"),
    ("greenhouse", "hims", "Hims & Hers"),
    ("greenhouse", "hopin", "Hopin"),
    ("greenhouse", "instabase", "Instabase"),
    ("greenhouse", "intercom", "Intercom"),
    ("greenhouse", "lattice", "Lattice"),
    ("greenhouse", "launchdarkly", "LaunchDarkly"),
    ("greenhouse", "lyra", "Lyra Health"),
    ("greenhouse", "mixpanel", "Mixpanel"),
    ("greenhouse", "notion", "Notion"),
    ("greenhouse", "nuro", "Nuro"),
    ("greenhouse", "opendoor", "Opendoor"),
    ("greenhouse", "outreach", "Outreach"),
    ("greenhouse", "patreon", "Patreon"),
    ("greenhouse", "plaidinc", "Plaid"),
    ("greenhouse", "postman", "Postman"),
    ("greenhouse", "quora", "Quora"),
    ("greenhouse", "rampbusiness", "Ramp"),
    ("greenhouse", "retool", "Retool"),
    ("greenhouse", "roblox", "Roblox"),
    ("greenhouse", "rubrik", "Rubrik"),
    ("greenhouse", "sentry", "Sentry"),
    ("greenhouse", "sigopt", "SigOpt"),
    ("greenhouse", "snyk", "Snyk"),
    ("greenhouse", "sourcegraph", "Sourcegraph"),
    ("greenhouse", "squarespace", "Squarespace"),
    ("greenhouse", "stockx", "StockX"),
    ("greenhouse", "thumbtack", "Thumbtack"),
    ("greenhouse", "tinder", "Tinder"),
    ("greenhouse", "toast", "Toast"),
    ("greenhouse", "udemy", "Udemy"),
    ("greenhouse", "unqork", "Unqork"),
    ("greenhouse", "verkada", "Verkada"),
    ("greenhouse", "vimeo", "Vimeo"),
    ("greenhouse", "wandb", "Weights & Biases"),
    ("greenhouse", "warbyparker", "Warby Parker"),
    ("greenhouse", "webflow", "Webflow"),
    ("greenhouse", "whatnot", "Whatnot"),
    ("greenhouse", "wise", "Wise"),
    ("greenhouse", "zapier", "Zapier"),
    ("greenhouse", "zocdoc", "Zocdoc"),
    ("greenhouse", "coinbase", "Coinbase"),
    ("greenhouse", "snowflakecomputing", "Snowflake"),
    ("greenhouse", "niantic", "Niantic"),
    ("greenhouse", "peloton", "Peloton"),
    ("greenhouse", "rippling", "Rippling"),
    ("greenhouse", "ironclad", "Ironclad"),
    ("greenhouse", "vanta", "Vanta"),
    ("greenhouse", "deel", "Deel"),
    ("greenhouse", "gong", "Gong"),
    ("greenhouse", "loom", "Loom"),
    ("greenhouse", "miro", "Miro"),
    ("greenhouse", "monzo", "Monzo"),
    ("greenhouse", "razorpay", "Razorpay"),
    ("greenhouse", "starburst", "Starburst"),
    ("greenhouse", "tecton", "Tecton"),
    ("greenhouse", "temporal", "Temporal"),
    ("greenhouse", "anduril", "Anduril"),
    ("greenhouse", "applied", "Applied Intuition"),
    ("greenhouse", "cruise", "Cruise"),
    ("greenhouse", "zoox", "Zoox"),
    ("greenhouse", "waymo", "Waymo"),
    ("greenhouse", " roblox", "Roblox"),
    # ===================== LEVER =====================
    ("lever", "palantir", "Palantir"),
    ("lever", "spotify", "Spotify"),
    ("lever", "netflix", "Netflix"),
    ("lever", "plaid", "Plaid"),
    ("lever", "brex", "Brex"),
    ("lever", "ramp", "Ramp"),
    ("lever", "attentive", "Attentive"),
    ("lever", "fanatics", "Fanatics"),
    ("lever", "kayak", "KAYAK"),
    ("lever", "github", "GitHub"),
    ("lever", "epicgames", "Epic Games"),
    ("lever", "nubank", "Nubank"),
    ("lever", "leetcode", "LeetCode"),
    ("lever", "wealthfront", "Wealthfront"),
    ("lever", "twitch", "Twitch"),
    ("lever", "voleon", "Voleon"),
    ("lever", "yelp", "Yelp"),
    ("lever", "kodiak", "Kodiak Robotics"),
    ("lever", "matchgroup", "Match Group"),
    ("lever", "upgrade", "Upgrade"),
    # ===================== ASHBY =====================
    ("ashby", "ramp", "Ramp"),
    ("ashby", "notion", "Notion"),
    ("ashby", "linear", "Linear"),
    ("ashby", "vercel", "Vercel"),
    ("ashby", "mercury", "Mercury"),
    ("ashby", "openstore", "OpenStore"),
    ("ashby", "clipboardhealth", "Clipboard Health"),
    ("ashby", "cresta", "Cresta"),
    ("ashby", "watershed", "Watershed"),
    ("ashby", "hex", "Hex"),
    ("ashby", "modal", "Modal"),
    ("ashby", "baseten", "Baseten"),
    ("ashby", "perplexity", "Perplexity"),
    ("ashby", "together", "Together AI"),
    ("ashby", "runwayml", "Runway"),
    ("ashby", "elevenlabs", "ElevenLabs"),
    ("ashby", "harvey", "Harvey"),
    ("ashby", "sierra", "Sierra"),
    ("ashby", "decagon", "Decagon"),
    ("ashby", "glean", "Glean"),
    ("ashby", "ramp-2", "Ramp"),
    ("ashby", "writer", "Writer"),
    ("ashby", "abridge", "Abridge"),
    ("ashby", "anysphere", "Anysphere (Cursor)"),
    ("ashby", "openai", "OpenAI"),
    ("ashby", "anthropic", "Anthropic"),
    ("ashby", "scale", "Scale AI"),
    ("ashby", "mistral", "Mistral AI"),
    ("ashby", "supabase", "Supabase"),
    ("ashby", "replit", "Replit"),
    ("ashby", "wander", "Wander"),
    ("ashby", "ramp-eng", "Ramp Eng"),
    ("ashby", "fireworks", "Fireworks AI"),
    ("ashby", "lambdalabs", "Lambda Labs"),
    ("ashby", "huggingface", "Hugging Face"),
    ("ashby", "labelbox", "Labelbox"),
    ("ashby", "pika", "Pika"),
    ("ashby", "suno", "Suno"),
    ("ashby", "cartesia", "Cartesia"),
    ("ashby", "browserbase", "Browserbase"),
]


def main():
    dry = "--dry-run" in sys.argv

    # de-dupe and drop accidental whitespace in tokens
    seen, uniq = set(), []
    for ats, token, name in CANDIDATES:
        token = token.strip()
        ats = ats.strip()
        if not token or (ats, token) in seen:
            continue
        seen.add((ats, token))
        uniq.append((ats, token, name))

    reg = registry.load()
    before = len(reg)
    todo = [c for c in uniq if f"{c[0]}:{c[1]}" not in reg]
    print(f"Registry has {before} companies. Bulk-validating {len(todo)} candidates "
          f"(parallel, $0 API cost)...\n")

    from concurrent.futures import ThreadPoolExecutor, as_completed
    added = failed = 0
    with ThreadPoolExecutor(max_workers=20) as ex:
        futs = {ex.submit(seed.validate, c): c for c in todo}
        for fut in as_completed(futs):
            res = fut.result()
            c = futs[fut]
            if res:
                ats, token, name, n = res
                if not dry:
                    reg[f"{ats}:{token}"] = {"name": name, "ats": ats, "token": token}
                added += 1
                print(f"  \u2713 {name:<24} {ats}:{token}  ({n} jobs live)")
            else:
                failed += 1
                print(f"  \u2717 {c[2]:<24} {c[0]}:{c[1]}  (no live board, skipped)")

    if not dry:
        registry.save(reg)
    print(f"\n{'DRY RUN - nothing saved. ' if dry else ''}"
          f"Added {added}, skipped {failed}. "
          f"Registry now {before + (0 if dry else added)} companies.")
    if not dry and added:
        print("Next run of main.py pulls from all of them automatically.")


if __name__ == "__main__":
    main()
