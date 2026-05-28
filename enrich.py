"""
Enrichment engine — the differentiator.

For a strong-fit job, find the right humans to contact (recruiter + an engineering
manager) and a VERIFIED email, then draft a personalized outreach email. The user
reviews and sends from their own inbox. Nothing is auto-sent.

Providers (set keys via env; all optional, the module degrades gracefully):
  APOLLO_API_KEY   -> people search + emails (apollo.io)
  HUNTER_API_KEY   -> domain email pattern + verification (hunter.io)

Cost control: only call this on strong-tier jobs (see main.py), never the full list.
Deliverability: emails are verified before they're considered sendable, so the
user's sender reputation is protected and bounces stay near zero.
"""
import os
import re
import requests

TIMEOUT = 20
HEADERS = {"User-Agent": "Mozilla/5.0 (job-finder)", "Content-Type": "application/json"}

# Titles we want to reach, best-first. Recruiter gets you in the door; an EM/engineer
# is the higher-signal contact for a technical referral.
TARGET_TITLES = [
    "Technical Recruiter", "Recruiter", "Talent Acquisition",
    "Engineering Manager", "Software Engineer", "Head of Engineering",
]


def _domain_from_company(company, fallback_jobs_url=""):
    """Best-effort company domain. In production, store the verified domain per company."""
    m = re.search(r"https?://([^/]+)", fallback_jobs_url or "")
    if m:
        host = m.group(1).lower()
        # strip known ATS hosts so we don't return greenhouse.io etc.
        if not any(a in host for a in ("greenhouse", "lever", "ashby", "recruitee",
                                       "workable", "smartrecruiters", "myworkday")):
            return host.replace("www.", "")
    slug = re.sub(r"[^a-z0-9]", "", (company or "").lower())
    return f"{slug}.com" if slug else ""


# --------------------------------------------------------------- providers
_apollo_disabled = False


def apollo_people(company, domain):
    global _apollo_disabled
    key = os.environ.get("APOLLO_API_KEY")
    if not key or _apollo_disabled:
        return []
    url = "https://api.apollo.io/api/v1/mixed_people/search"
    headers = {"Content-Type": "application/json", "Cache-Control": "no-cache",
               "accept": "application/json", "X-Api-Key": key}
    payload = {
        "person_titles": TARGET_TITLES,
        "q_organization_names": [company] if company else [],
        "page": 1, "per_page": 5,
    }
    if domain:
        payload["q_organization_domains_list"] = [domain]
    try:
        r = requests.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        if r.status_code == 403 and "API_INACCESSIBLE" in r.text:
            _apollo_disabled = True
            print("    Apollo people-search needs a paid API plan — skipping contacts, "
                  "using LinkedIn fallback (free).")
            return []
        r.raise_for_status()
        out = []
        for p in r.json().get("people", []):
            org = p.get("organization") or {}
            out.append({
                "name": f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
                "title": p.get("title", ""),
                "email": p.get("email", "") or "",
                "email_status": p.get("email_status", "unknown"),
                "linkedin": p.get("linkedin_url", ""),
                "company": org.get("name", company),
                "source": "apollo",
            })
        return out
    except Exception as e:
        print(f"    apollo error for {company}: {e}")
        return []


def hunter_verify(email):
    """Confirm an email is deliverable before we let it be sent."""
    key = os.environ.get("HUNTER_API_KEY")
    if not key or not email:
        return "unverified"
    try:
        r = requests.get("https://api.hunter.io/v2/email-verifier",
                         params={"email": email, "api_key": key}, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json().get("data", {}).get("status", "unknown")  # valid|invalid|risky...
    except Exception:
        return "unknown"


def find_contacts(job, max_contacts=3):
    """Return verified-where-possible contacts for a job. Empty list if no providers."""
    company = job.get("company", "")
    domain = _domain_from_company(company, job.get("url", ""))
    people = apollo_people(company, domain)[:max_contacts]
    for p in people:
        if p["email"] and p["email_status"] not in ("verified",):
            p["email_status"] = hunter_verify(p["email"])
    # sort: people with a usable email first, then by how senior/relevant the title is
    people.sort(key=lambda p: (p["email"] == "", TARGET_TITLES.index(p["title"])
                               if p["title"] in TARGET_TITLES else 99))
    return people


# --------------------------------------------------------------- outreach draft
COLD_EMAIL_PROMPT = """Write a short cold outreach email from a job candidate to a
recruiter/hiring contact at a company the candidate just applied to.

Output EXACTLY this format and nothing else:
Subject: <specific, compelling subject line, under 8 words>

Hi {{{{NAME}}}},

<email body, under 110 words. Warm, professional, specific, no fluff, no clichés.
Lead with the candidate's single strongest, most relevant project. End with a soft
ask (open to a quick chat / who's the right person to talk to).>

Use the literal token {{{{NAME}}}} for the greeting — do NOT invent a name.
Do NOT use em dashes or en dashes (— or –) anywhere. Use periods, commas, or "to" instead. This is a hard rule.

CANDIDATE PROFILE:
{profile_json}

ROLE: {title} at {company}
JOB DESCRIPTION (for relevance):
{description}"""


def draft_email(client, profile_json, job, contact=None):
    """LLM-draft a personalized outreach email. Returns {"subject","body"}.
    The body greeting uses a {{NAME}} token the UI fills with the recruiter's name."""
    prompt = COLD_EMAIL_PROMPT.format(
        profile_json=profile_json, title=job.get("title", ""), company=job.get("company", ""),
        description=(job.get("description", "") or "")[:1500],
    )
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=400,
                                 messages=[{"role": "user", "content": prompt}])
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()

    subject, body = "", text
    if text.lower().startswith("subject:"):
        first, _, rest = text.partition("\n")
        subject = first.split(":", 1)[1].strip()
        body = rest.strip()
    # if a real contact name is known (e.g. Apollo), bake it in now
    if contact and contact.get("name") and contact["name"].lower() != "there":
        first_name = contact["name"].split()[0]
        body = body.replace("{{NAME}}", first_name)
        subject = subject.replace("{{NAME}}", first_name)

    # safety net: never let em/en dashes through (they read as AI-written)
    def _nodash(s):
        return s.replace(" — ", ", ").replace("—", ", ").replace(" – ", ", ").replace("–", ", ")
    return {"subject": _nodash(subject), "body": _nodash(body)}
