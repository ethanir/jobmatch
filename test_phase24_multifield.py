"""
Phase 24 - multi-field expansion.

Verifies the backward-compatible multi-field work:
  * the profile schema gained field / skills_general / certifications (additive)
  * the heuristic scorer is field-agnostic (folds skills_general + certifications)
  * non-tech disciplines classify, so cross-field roles are down-weighted and
    same-field roles are kept
  * the MULTIFIELD switch admits professional resume-driven roles and drops hourly
    ones, while the OFF path stays tech-only (no regression)
  * the new USAJOBS source is safe (returns [] without keys) and the broad query set
    spans fields

Run: python3 test_phase24_multifield.py
"""
import json
import os

import prompts
import score
import prefilter
import sources

n = 0


def ok(msg):
    global n
    n += 1
    print(f"{n} ok: {msg}")


# --- schema -----------------------------------------------------------------
sch = json.loads(prompts.PROFILE_SCHEMA)
assert "field" in sch and "skills_general" in sch and "certifications" in sch
ok("schema gained field / skills_general / certifications")
assert sch["skills"] == {"languages": [], "frameworks": [], "tools": [], "databases": []}
assert sch["skills_general"] == [] and sch["certifications"] == [] and sch["field"] is None
ok("tech skills dict is unchanged and new fields default empty")

# start.html embeds a copy of the schema; keep them in sync.
_here = os.path.dirname(os.path.abspath(__file__))
_candidates = [os.path.join(_here, "_live", "start.html"), os.path.join(_here, "start.html")]
_sh = next((p for p in _candidates if os.path.exists(p)), None)
start_html = open(_sh, encoding="utf-8").read() if _sh else ""
if start_html:
    assert '"field": null' in start_html and '"skills_general": []' in start_html \
        and '"certifications": []' in start_html
    ok("start.html embedded schema stays in sync")


# --- field-agnostic skills --------------------------------------------------
prof = {"skills": {"languages": ["Python"]},
        "skills_general": ["Patient Assessment", "ACLS", "python"],
        "certifications": ["RN License"]}
fs = score._flat_skills(prof)
for want in ("python", "patient assessment", "acls", "rn license"):
    assert want in fs, (want, fs)
assert fs.count("python") == 1
ok("skills_general + certifications fold into the skill list (de-duped, lowercased)")

# the dict-only invariant for `skills` is preserved (a list still raises)
try:
    score._flat_skills({"skills": ["python", "java"]})
    raise SystemExit("FAIL: malformed skills list should have raised")
except AttributeError:
    ok("a malformed skills list still raises (fail-loud invariant kept)")


# --- disciplines ------------------------------------------------------------
assert score.role_disciplines("Registered Nurse") == {"healthcare"}
assert score.role_disciplines("Senior Financial Analyst") == {"finance"}
assert score.role_disciplines("Marketing Manager") == {"marketing"}
assert score.role_disciplines("Account Executive") == {"sales"}
assert score.role_disciplines("Technical Recruiter") == {"hr"}
assert score.role_disciplines("Litigation Attorney") == {"legal"}
assert score.role_disciplines("High School Teacher") == {"education"}
assert "eng" in score.role_disciplines("Backend Software Engineer")
assert score.role_disciplines("Office Coordinator") == set()
ok("disciplines classify finance/healthcare/marketing/sales/hr/legal/education + tech, neutral stays empty")


# --- cross-field down-weight + same-field kept ------------------------------
finance_prof = {"target_titles": ["Financial Analyst", "Accountant"],
                "skills_general": ["financial modeling", "excel", "gaap"], "skills": {}}
acct = {"title": "Staff Accountant", "description": "Prepare financial statements, GAAP, Excel, reconciliations."}
mkt = {"title": "Marketing Manager", "description": "Own brand campaigns, SEO and social media."}
ranked = {j["title"]: j["_score"] for j in score.rank_free([dict(acct), dict(mkt)], finance_prof)}
assert ranked["Staff Accountant"] > ranked["Marketing Manager"], ranked
ok(f"finance candidate ranks same-field above off-field {ranked}")


# --- gated same-discipline bonus --------------------------------------------
single = {"target_titles": ["Financial Analyst"],
          "skills_general": ["financial modeling", "excel", "gaap"], "skills": {}}
score.MULTIFIELD = False
off_score = next(j["_score"] for j in score.rank_free([dict(acct)], single))
score.MULTIFIELD = True
on_score = next(j["_score"] for j in score.rank_free([dict(acct)], single))
score.MULTIFIELD = False
assert on_score > off_score, (off_score, on_score)
ok(f"same-discipline title bonus lifts a same-field role only when MULTIFIELD is on ({off_score} -> {on_score})")


# --- prefilter gate ---------------------------------------------------------
pool = [
    {"company": "A", "title": "Software Engineer"},
    {"company": "B", "title": "Registered Nurse"},
    {"company": "C", "title": "Staff Accountant"},
    {"company": "D", "title": "Marketing Manager"},
    {"company": "E", "title": "Litigation Attorney"},
    {"company": "F", "title": "Retail Sales Associate"},
    {"company": "G", "title": "Warehouse Associate"},
    {"company": "H", "title": "Delivery Driver"},
    {"company": "I", "title": "Line Cook"},
]
prefilter.MULTIFIELD = False
off_titles = {j["title"] for j in prefilter.prefilter_generic([dict(x) for x in pool])}
assert off_titles == {"Software Engineer"}, off_titles
ok("MULTIFIELD off keeps the pool tech-only (no regression)")

prefilter.MULTIFIELD = True
on_titles = {j["title"] for j in prefilter.prefilter_generic([dict(x) for x in pool])}
prefilter.MULTIFIELD = False
for keep in ("Software Engineer", "Registered Nurse", "Staff Accountant", "Marketing Manager", "Litigation Attorney"):
    assert keep in on_titles, (keep, on_titles)
for drop in ("Retail Sales Associate", "Warehouse Associate", "Delivery Driver", "Line Cook"):
    assert drop not in on_titles, (drop, on_titles)
ok(f"MULTIFIELD on admits professional roles and drops hourly/manual ones {sorted(on_titles)}")


# --- sources ----------------------------------------------------------------
os.environ.pop("USAJOBS_API_KEY", None)
os.environ.pop("USAJOBS_EMAIL", None)
assert sources.from_usajobs() == []
ok("USAJOBS returns [] without keys (pipeline-safe)")

assert "software engineer" in sources._TECH_QUERIES
assert "registered nurse" in sources._BROAD_QUERIES and "accountant" in sources._BROAD_QUERIES
assert set(sources._TECH_QUERIES).issubset(set(sources._BROAD_QUERIES))
ok("broad query set spans many fields and is a superset of the tech set")


print(f"\nALL PHASE 24 MULTIFIELD TESTS PASSED ({n})")
