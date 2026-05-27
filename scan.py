"""
Scan feature — "I found this job on LinkedIn, do the whole thing for me."

The user pastes a job description (or a URL we can fetch), and we run the same
pipeline as the main feed on that single role:

    paste/url -> parse  ->  fit-rank  ->  find contacts  ->  draft email

Returns one ranked job + contacts + draft, ready to display in the UI.

Reuses the engine — nothing here duplicates ranking or contact logic; we just
hand a single job to rank.run() and enrich.find_contacts() / enrich.draft_email().
"""
import json
import os
import re

import requests

import rank
import enrich

HEADERS = {"User-Agent": "Mozilla/5.0 (job-finder/scan)"}
URL_RX = re.compile(r"https?://\S+")


def _looks_like_url(text):
    t = text.strip()
    return t.startswith(("http://", "https://")) and " " not in t


def _fetch_url(url):
    """Best-effort fetch of a job page. Strips HTML to plain text."""
    r = requests.get(url, headers=HEADERS, timeout=15)
    r.raise_for_status()
    html = r.text
    # naive strip: tags + scripts/styles
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()[:8000]


def _parse_meta(text):
    """Extract title + company + location heuristically from pasted text.
    The LLM rank step doesn't strictly need these, but they make the UI nicer."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    title, company, location = "", "", ""
    for l in lines[:12]:
        low = l.lower()
        if not title and any(k in low for k in ("engineer", "developer", "software", "swe")):
            title = l[:120]
        if not company and any(k in low for k in ("at ", "@ ", "company:")):
            company = re.sub(r"^(at |@ |company:\s*)", "", l, flags=re.I)[:80]
        if not location and any(k in low for k in ("remote", "hybrid", ", ca", ", ny", ", il", ", tx")):
            location = l[:80]
    return title or "(role from scan)", company or "(company from scan)", location


def _make_anthropic_client():
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=key)


def scan(input_text, profile, include_contacts=True, include_draft=True):
    """Run the full pipeline on a single pasted JD or URL.

    Returns a dict shaped like the main feed's jobs entries, so the UI can
    render it with the same components.
    """
    raw = input_text.strip()
    if _looks_like_url(raw):
        description = _fetch_url(raw)
        url = raw
    else:
        description = raw
        url = ""

    title, company, location = _parse_meta(description)
    job = {"company": company, "title": title, "location": location, "url": url,
           "description": description, "source": "scan"}

    # 1. fit-rank (single job)
    ranked = rank.run([job], profile)
    j = ranked[0]
    fit = j.get("fit") or {}

    # 2. contacts (only if strong/possible -- never spend on skip)
    contacts = []
    if include_contacts and fit.get("tier") in ("strong", "possible"):
        contacts = enrich.find_contacts(j)
    j["contacts"] = contacts

    # 3. email draft (one per contact, for the best contact only to save tokens)
    draft = ""
    if include_draft and contacts and fit.get("tier") != "skip":
        client = _make_anthropic_client()
        if client:
            profile_json = json.dumps(profile, indent=2)
            try:
                draft = enrich.draft_email(client, profile_json, j, contacts[0])
            except Exception as e:
                print(f"  draft failed: {e}")
    j["draft"] = draft

    return j


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("usage: python scan.py <profile.json> <input.txt|url>")
        sys.exit(1)
    with open(sys.argv[1]) as f:
        prof = json.load(f)
    arg = sys.argv[2]
    if _looks_like_url(arg) or not os.path.exists(arg):
        text = arg
    else:
        with open(arg) as f:
            text = f.read()
    out = scan(text, prof)
    print(json.dumps(out, indent=2, default=str))
