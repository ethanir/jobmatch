"""
export_rank.py — rank for $0 using your own free web AI (no API key needed).

THE IDEA (your "bring your own AI" cost-saver):
  1. Run this. It writes `rank_me.txt` containing your top jobs plus a ready-to-use
     prompt.
  2. Open Claude.ai or ChatGPT (the free web chat), paste the whole file, send.
  3. The AI returns a JSON block. Copy it into `ai_response.json`.
  4. Run `python3 import_rank.py` to merge those rankings into your feed + viewer.

WHY THIS WORKS (and its honest limit):
  The free heuristic scorer (score.py) already narrows ~50k jobs down to the best
  few dozen for $0. This exports just that cream — small enough for a web chat to
  handle well. It is NOT a way to rank all 50k for free (a chat window can't take
  that much), but it removes the paid API step for your top batch entirely.

USAGE:
  python3 export_rank.py                 # export top 30 (default)
  python3 export_rank.py 40              # export top 40
Run main.py first so ranked_jobs.json / the free scores exist.
"""
import json
import sys

import prompts

TOP = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 30
PROFILE = "my_profile.json"


def load(path, default=None):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def main():
    jobs = load("ranked_jobs.json", [])
    if not jobs:
        print("No ranked_jobs.json found. Run: python3 main.py my_profile.json")
        return
    profile = load(PROFILE, {})

    # take the top N by free score that aren't already strong-tier from the LLM
    top = jobs[:TOP]

    # compact the profile to the parts that matter for ranking
    slim = {
        "target_titles": profile.get("target_titles"),
        "years_experience": profile.get("years_experience"),
        "work_authorization": profile.get("work_authorization"),
        "requires_sponsorship": profile.get("requires_sponsorship"),
        "skills": profile.get("skills"),
        "preferences": profile.get("preferences"),
        "projects": [p.get("name") for p in (profile.get("projects") or [])],
    }

    lines = []
    lines.append("You are an expert technical recruiter. Score how well THIS candidate "
                 "fits EACH job below. Be honest and strict: correctly rejecting a bad "
                 "fit is more useful than inflating a score. New grad applying to a 5+ "
                 "year role = skip. Senior/staff/lead titles = skip for an early-career "
                 "candidate.\n")
    lines.append("Return ONLY a JSON array, one object per job, in this exact shape, "
                 "and nothing else:\n")
    lines.append('[{"id": "<the id shown>", "score": 0-100, '
                 '"tier": "strong|possible|skip", "reasons": ["short","short"], '
                 '"matched_skills": ["..."], "missing_skills": ["..."]}]\n')
    lines.append("Do not use em dashes anywhere in your output.\n")
    lines.append("CANDIDATE PROFILE:")
    lines.append(json.dumps(slim, indent=2))
    lines.append("\nJOBS TO SCORE:\n")

    for j in top:
        jid = j.get("_id") or j.get("id") or ""
        desc = (j.get("description", "") or "")[:1200]
        lines.append(f"--- id: {jid}")
        lines.append(f"Title: {j.get('title','')}")
        lines.append(f"Company: {j.get('company','')}")
        lines.append(f"Location: {j.get('location','')}")
        lines.append(f"Description: {desc}")
        lines.append("")

    with open("rank_me.txt", "w") as f:
        f.write("\n".join(lines))

    print(f"Wrote rank_me.txt with your top {len(top)} jobs.")
    print("Next:")
    print("  1. Open Claude.ai or ChatGPT (free web chat)")
    print("  2. Paste the entire contents of rank_me.txt and send")
    print("  3. Copy the JSON array it returns into a file named ai_response.json")
    print("  4. Run: python3 import_rank.py")


if __name__ == "__main__":
    main()
