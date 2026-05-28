"""
import_rank.py — merge your free web-AI rankings back into the feed ($0).

Pair with export_rank.py. After you paste the AI's JSON array into
`ai_response.json`, this merges those scores/tiers/reasons into ranked_jobs.json
and the ranking cache, then you rebuild the viewer.

It is forgiving about format: it will find the JSON array even if you accidentally
pasted the AI's surrounding chatter or ```json fences around it.

USAGE:
  python3 import_rank.py                 # reads ai_response.json
  python3 import_rank.py myfile.json     # or a file you name
  python3 make_ui.py && open viewer.html # then refresh the viewer
"""
import json
import re
import sys

import jobcache


def extract_json_array(text):
    """Pull the first JSON array out of arbitrary pasted text."""
    text = text.strip()
    # strip code fences if present
    text = re.sub(r"^```(?:json)?", "", text).strip()
    text = re.sub(r"```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        pass
    # fall back: grab from first '[' to last ']'
    i, j = text.find("["), text.rfind("]")
    if i != -1 and j != -1 and j > i:
        return json.loads(text[i:j + 1])
    raise ValueError("Could not find a JSON array in the response.")


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else "ai_response.json"
    try:
        with open(src) as f:
            raw = f.read()
    except FileNotFoundError:
        print(f"'{src}' not found. Paste the AI's JSON array into that file first.")
        return

    try:
        rankings = extract_json_array(raw)
    except Exception as e:
        print(f"Couldn't parse rankings: {e}")
        print("Make sure ai_response.json contains the JSON array the AI returned.")
        return

    by_id = {r.get("id"): r for r in rankings if r.get("id")}
    if not by_id:
        print("No usable rankings found (each item needs an 'id').")
        return

    with open("ranked_jobs.json") as f:
        jobs = json.load(f)

    cache = jobcache.load()
    updated = 0
    for j in jobs:
        jid = j.get("_id") or j.get("id")
        r = by_id.get(jid)
        if not r:
            continue
        fit = {
            "score": max(0, min(100, int(r.get("score", 0)))),
            "tier": r.get("tier", "possible"),
            "reasons": r.get("reasons", []),
            "hard_disqualifiers": r.get("hard_disqualifiers", []),
            "matched_skills": r.get("matched_skills", []),
            "missing_skills": r.get("missing_skills", []),
        }
        j["fit"] = fit
        if jid:
            cache["ranked"][jid] = fit          # so it persists like a paid rank
        updated += 1

    # re-sort best-first using the new tiers
    tier_rank = {"strong": 0, "possible": 1, "skip": 2, "unknown": 3}
    jobs.sort(key=lambda j: (
        not j.get("is_new"),
        tier_rank.get((j.get("fit") or {}).get("tier", "unknown"), 3),
        -((j.get("fit") or {}).get("score") or 0),
    ))

    with open("ranked_jobs.json", "w") as f:
        json.dump(jobs, f, indent=2)
    jobcache.save(cache)

    strong = sum(1 for j in jobs if (j.get("fit") or {}).get("tier") == "strong")
    print(f"Merged {updated} web-AI rankings ({strong} now strong). $0 API cost.")
    print("Now run:  python3 make_ui.py && open viewer.html")


if __name__ == "__main__":
    main()
