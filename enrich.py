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
def apollo_people(company, domain):
    key = os.environ.get("APOLLO_API_KEY")
    if not key:
        return []
    url = "https://api.apollo.io/v1/mixed_people/search"
    payload = {
        "api_key": key,
        "q_organization_domains": domain,
        "person_titles": TARGET_TITLES,
        "page": 1, "per_page": 5,
    }
    try:
        r = requests.post(url, json=payload, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        out = []
        for p in r.json().get("people", []):
            out.append({
                "name": f"{p.get('first_name','')} {p.get('last_name','')}".strip(),
                "title": p.get("title", ""),
                "email": p.get("email", ""),
                "email_status": p.get("email_status", "unknown"),
                "linkedin": p.get("linkedin_url", ""),
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
COLD_EMAIL_PROMPT = """Write a short, specific cold email from a job candidate to a
person at a company they just applied to. Under 120 words. Warm but professional, no
fluff, no clichés. Lead with the candidate's single strongest, most relevant project.
End with a soft ask (open to a quick look / who to talk to). Output ONLY the email body.

CANDIDATE PROFILE:
{profile_json}

ROLE: {title} at {company}
CONTACT: {contact_name}, {contact_title}
JOB DESCRIPTION (for relevance):
{description}"""


def draft_email(client, profile_json, job, contact):
    """LLM-draft a personalized outreach email. client = anthropic.Anthropic()."""
    prompt = COLD_EMAIL_PROMPT.format(
        profile_json=profile_json, title=job.get("title", ""), company=job.get("company", ""),
        contact_name=contact.get("name", "there"), contact_title=contact.get("title", ""),
        description=(job.get("description", "") or "")[:1500],
    )
    msg = client.messages.create(model="claude-sonnet-4-6", max_tokens=400,
                                 messages=[{"role": "user", "content": prompt}])
    return "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
