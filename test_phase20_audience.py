"""Phase 20: audience expansion. One broad pool can serve all of CS, because the
shared prefilter keeps every software/CS/tech role (all seniorities, all
locations, decoupled from any profile) and the per-user scorer narrows each
person's feed by discipline. A role in a different discipline is pushed to skip
even when its description name-drops the user's skills."""
import os
os.environ.pop("DATABASE_URL", None)
os.environ["ACCESS_CODE"] = "testcode"
os.environ["COOKIE_SECURE"] = "0"
import prefilter as pf
import score
# This suite validates the tech-only default behavior (the shared pool before
# multi-field is enabled), so pin the switch off regardless of the environment.
pf.MULTIFIELD = False
score.MULTIFIELD = False

PASS = 0
def ok(cond, label):
    global PASS
    assert cond, "FAIL: " + label
    PASS += 1
    print(" ok -", label)

def J(title, company="Acme", loc="Remote"):
    return {"title": title, "company": company, "location": loc}

# ---------- role_disciplines ----------
ok(sorted(score.role_disciplines("Software Engineer")) == ["eng"], "software engineer -> eng")
ok(sorted(score.role_disciplines("Machine Learning Engineer")) == ["eng", "ml_ds"], "ML engineer -> eng + ml_ds")
ok(sorted(score.role_disciplines("Data Scientist")) == ["ml_ds"], "data scientist -> ml_ds")
ok(sorted(score.role_disciplines("Data Analyst")) == ["analytics"], "data analyst -> analytics")
ok(sorted(score.role_disciplines("Product Manager")) == ["product"], "product manager -> product")
ok(sorted(score.role_disciplines("UX Designer")) == ["design"], "ux designer -> design")
ok(sorted(score.role_disciplines("FPGA Engineer")) == ["hardware"], "fpga -> hardware")
ok(score.role_disciplines("Mechanical Engineer") == set(), "mechanical engineer -> unclassified (neutral)")
ok(score.role_disciplines("Member of Technical Staff") == set(), "ambiguous title -> unclassified")

# ---------- prefilter_generic: breadth, non-tech drop, no seniority/location filter ----------
keep = ["Associate Software Engineer", "Senior Staff Software Engineer", "Data Scientist",
        "Machine Learning Engineer", "Data Engineer", "Security Software Engineer",
        "DevOps Engineer", "iOS Engineer", "Data Analyst", "Product Manager", "UX Designer",
        "Hardware Engineer", "Compiler Engineer", "Research Scientist", "Cloud Engineer",
        "Software Engineer, Marketing Platform"]
kept = {j["title"] for j in pf.prefilter_generic([J(t) for t in keep])}
ok(kept == set(keep), "every software/CS/tech role is kept, all disciplines + seniorities")

drop = ["Sales Development Representative", "Technical Recruiter", "Registered Nurse",
        "Mechanical Engineer", "Civil Engineer", "Account Executive", "Warehouse Associate",
        "Customer Success Manager", "Staff Accountant", "Truck Driver", "Barista"]
ok(all(not pf.prefilter_generic([J(t)]) for t in drop), "non-tech roles are dropped")

ok(bool(pf.prefilter_generic([J("Senior Staff Software Engineer")])), "no seniority filtering (senior kept)")
ok(bool(pf.prefilter_generic([J("Software Engineer", loc="Tokyo, Japan")])), "no location filtering (faraway kept)")
ok(len(pf.prefilter_generic([J("Software Engineer"), J("Software Engineer")])) == 1, "dedupes by company+title")

# ---------- per-user discipline filtering (the safety net for a broad pool) ----------
def rank_one(profile, title, desc, loc="Remote"):
    j = J(title, loc=loc); j["description"] = desc
    score.rank_free([j], profile)
    f = score.heuristic_fit(j)
    return j["_score"], f["tier"], " ".join(f["reasons"]).lower()

SKILLY = "Build models and services in Python and SQL across the team. " * 8  # name-drops python + sql

ng = {"target_titles": ["Software Engineer", "New Grad Software Engineer"], "years_experience": 0,
      "skills": {"languages": ["Python", "SQL", "JavaScript", "React"]},
      "preferences": {"locations": ["Chicago, IL"], "remote_ok": True, "onsite_ok": True}}
swe_s, swe_t, _ = rank_one(ng, "Software Engineer", SKILLY)
ds_s, ds_t, ds_r = rank_one(ng, "Data Scientist", SKILLY)          # skill-stuffed, must STILL skip
pm_s, pm_t, _ = rank_one(ng, "Product Manager", SKILLY)
ok(swe_t == "possible", "new-grad SWE: a software role is possible")
ok(ds_t == "skip" and swe_s > ds_s, "new-grad SWE: a skill-stuffed data-science role is still skipped")
ok("outside your target area" in ds_r, "new-grad SWE: the data-science role is flagged as off-target")
ok(pm_t == "skip", "new-grad SWE: a product role is skipped")
# adjacent engineering is NOT family-penalized (no off-target flag)
_, _, be_r = rank_one(ng, "Backend Engineer", SKILLY)
_, _, sec_r = rank_one(ng, "Security Engineer", SKILLY)
ok("outside your target area" not in be_r, "new-grad SWE: a backend role is NOT flagged off-target")
ok("outside your target area" not in sec_r, "new-grad SWE: a security role is NOT flagged off-target")

# Data scientist persona: software roles drop out, data roles stay.
ds_user = {"target_titles": ["Data Scientist"], "years_experience": 3,
           "skills": {"languages": ["Python", "SQL"], "tools": ["pandas", "tensorflow"]},
           "preferences": {"locations": ["Remote"], "remote_ok": True, "onsite_ok": True}}
_, fe_t, fe_r = rank_one(ds_user, "Frontend Engineer", SKILLY)
_, dsr_t, dsr_r = rank_one(ds_user, "Data Scientist", SKILLY)
_, deng_t, deng_r = rank_one(ds_user, "Data Engineer", SKILLY)
ok(fe_t == "skip" and "outside your target area" in fe_r, "data scientist: a frontend role is skipped + flagged")
ok(dsr_t == "possible" and "outside your target area" not in dsr_r, "data scientist: a data-science role is possible, not flagged")
ok("outside your target area" not in deng_r, "data scientist: data engineering shares 'data', not flagged off-target")

# Senior SWE persona: senior software fine, different field out.
sr = {"target_titles": ["Senior Software Engineer", "Staff Software Engineer"], "years_experience": 8,
      "skills": {"languages": ["Go", "Python", "Kubernetes"]},
      "preferences": {"locations": ["Remote"], "remote_ok": True, "onsite_ok": True}}
_, stf_t, stf_r = rank_one(sr, "Staff Software Engineer", SKILLY)
_, sds_t, sds_r = rank_one(sr, "Data Scientist", SKILLY)
ok(stf_t == "possible" and "outside your target area" not in stf_r, "senior SWE: a staff software role is possible, not flagged")
ok(sds_t == "skip" and "outside your target area" in sds_r, "senior SWE: a data-science role is skipped + flagged")

print("\nALL PHASE 20 AUDIENCE TESTS PASSED (%d)" % PASS)
