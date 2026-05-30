"""
Cheap, fast, FREE prefilter. Runs before the LLM so we never pay to rank
thousands of obviously-wrong jobs. Rule-based only: title sanity + light
location/keyword checks against the profile.

The LLM (rank.py) does the nuanced scoring on whatever survives here.
"""
import os
import re

# Multi-field switch. ON by default: the shared pool covers tech AND professional,
# resume-driven roles in other fields (finance, marketing, sales, HR, healthcare, legal,
# education, ops, and more), dropping only clearly hourly/manual roles where a resume plus
# an AI fit-read adds little. Set MULTIFIELD=off in the environment to revert to tech-only.
MULTIFIELD = os.environ.get("MULTIFIELD", "on").strip().lower() in ("1", "true", "on", "yes")

# Broad "is this a software / CS / tech role?" allowlist, used to build the SHARED
# pool at full breadth. It is intentionally generous (software, data, ML, security,
# devops, QA, product, design, embedded, and adjacent CS roles) so one pool can
# serve every kind of candidate; per-user scoring (score.py) then narrows each
# person's feed by discipline, level, and location. Only the title is judged.
TECH_ROLE_RX = re.compile(
    r"software|\bswe\b|\bsde\b|\bsdet\b|back.?end|front.?end|full.?stack|"
    r"web (?:developer|engineer)|application (?:engineer|developer)|"
    r"platform engineer|infrastructure|systems? (?:engineer|programmer)|"
    r"devops|\bsre\b|site reliability|reliability engineer|cloud engineer|"
    r"\bprogrammer\b|\bdeveloper\b|mobile (?:engineer|developer|app)|\bios\b|android|"
    r"game(?:play)? (?:engineer|developer|programmer)|graphics (?:engineer|programmer)|"
    r"engine (?:programmer|engineer)|compiler|kernel|embedded|firmware|"
    r"distributed systems|operating system|"
    r"data engineer|data scientist|data science|machine learning|\bml\b|"
    r"deep learning|\bmlops\b|\bai\b (?:engineer|researcher|scientist)|applied scientist|"
    r"research (?:scientist|engineer)|\bnlp\b|computer vision|"
    r"data analyst|data analytics|business intelligence|\bbi\b (?:developer|engineer|analyst)|"
    r"analytics engineer|\betl\b|data platform|"
    r"security engineer|security software|application security|\bappsec\b|\binfosec\b|"
    r"cyber.?security|security analyst|security researcher|product security|penetration test|"
    r"\bqa\b|quality (?:assurance|engineer)|test engineer|test automation|engineer in test|"
    r"product manager|technical program manager|\btpm\b|product owner|"
    r"developer (?:advocate|relations|experience|tools)|\bdevrel\b|"
    r"solutions (?:engineer|architect)|forward deployed|implementation engineer|integration engineer|"
    r"\bux\b|\bui\b (?:engineer|designer)|product designer|design (?:engineer|technologist)|"
    r"hardware engineer|\bfpga\b|\basic\b|\brtl\b|robotics|"
    r"computer (?:engineer|scientist)|\bsdk\b|"
    r"blockchain|smart contract|web3|crypto engineer|"
    r"\barchitect\b|technical lead|tech lead", re.I)

# Explicit non-tech roles to drop even if a tech keyword happens to appear. Kept to
# role-defining nouns (not domain words like "marketing"), so a software role in a
# non-tech domain (e.g. "Software Engineer, Marketing Platform") is still kept.
NONTECH_RX = re.compile(
    r"\brecruit|talent acquisition|account executive|sales (?:representative|development|manager|associate)|"
    r"\bbdr\b|\bsdr\b|business development representative|customer success|customer support|"
    r"support specialist|help desk|\bnurse\b|physician|clinician|therapist|pharmacist|"
    r"\bdental\b|veterinar|phlebotom|attorney|legal counsel|paralegal|accountant|bookkeep|"
    r"barista|cashier|warehouse|forklift|\bdriver\b|janitor|custodian|\bchef\b|\bcook\b|"
    r"mechanical engineer|civil engineer|chemical engineer|biomedical engineer|"
    r"industrial engineer|structural engineer|petroleum|\bhvac\b|plumb|electrician|"
    r"social worker|real estate|loan officer|underwriter|teacher|tutor", re.I)

# Professional, resume-driven roles in non-tech fields. Used ONLY in multi-field mode to
# WIDEN the pool beyond tech. Intentionally generous (an allowlist); per-user scoring and
# the blocklist below narrow things afterward.
PROFESSIONAL_ROLE_RX = re.compile(
    # finance & accounting
    r"\baccountant\b|accounting|\bauditor\b|\baudit\b|financial analyst|\bfinance\b|\bcontroller\b|"
    r"\bcpa\b|\bcfa\b|\binvestment\b|equity research|financial advisor|\bwealth\b|treasury|\bfp&a\b|"
    r"\btax\b|bookkeep|\bactuary\b|underwriter|loan officer|credit analyst|portfolio manager|"
    # marketing & communications
    r"|market(?:ing|er)|\bbrand\b|content (?:strategist|manager|marketing|writer)|\bseo\b|\bsem\b|"
    r"\bgrowth\b|social media|communications|public relations|copywriter|demand generation|"
    # sales & business development
    r"|account executive|\bsales\b|business development|\bbdr\b|\bsdr\b|account manager|partnerships|"
    # people / HR / recruiting
    r"|\brecruit|talent acquisition|human resources|\bhr\b|people operations|people partner|"
    r"compensation|benefits (?:analyst|manager)|learning and development|\bl&d\b|"
    # operations & supply chain
    r"|\boperations\b|\bops\b|supply chain|logistics|procurement|category manager|"
    # legal & compliance
    r"|\battorney\b|\blawyer\b|\bcounsel\b|\bparalegal\b|\blegal\b|compliance|contracts|regulatory|"
    # healthcare (professional / clinical)
    r"|\bnurse\b|\brn\b|nurse practitioner|\bphysician\b|clinician|\bpharmacist\b|therapist|"
    r"physician assistant|medical (?:assistant|director|officer)|\bdietitian\b|dental|radiolog|"
    r"sonograph|clinical|healthcare|health care|\bcna\b|"
    # education & academia
    r"|\bteacher\b|\bprofessor\b|\binstructor\b|\blecturer\b|\beducator\b|teaching|curriculum|"
    r"\btutor\b|academic|school counselor|\bfaculty\b|school principal|"
    # consulting / strategy / business
    r"|consultant|consulting|\bstrategy\b|advisory|business analyst|operations analyst|"
    # project / program management
    r"|project manager|program manager|project coordinator|\bpmo\b|scrum master|"
    # customer success / client services
    r"|customer success|client services|customer experience|"
    # writing / editorial / creative (non-product)
    r"|\bwriter\b|\beditor\b|journalist|graphic designer|art director|creative director|"
    # science / research (non-CS)
    r"|research (?:associate|assistant|scientist)|\bscientist\b|\bchemist\b|biolog|laboratory|"
    r"clinical research|"
    # admin / executive (professional)
    r"|executive assistant|office manager|chief of staff", re.I)

# Clearly hourly / manual roles where a resume + AI fit-read adds little. Used ONLY in
# multi-field mode to DROP these even if they slipped past the allowlist.
HOURLY_MANUAL_RX = re.compile(
    r"\bcashier\b|\bbarista\b|\bserver\b|\bwaiter\b|\bwaitress\b|host(?:ess)?\b|line cook|\bcook\b|"
    r"\bchef\b|dishwasher|\bbusser\b|food service|fast food|\bretail\b|sales associate|store associate|"
    r"stock(?:er| associate| clerk)|\bbagger\b|warehouse (?:associate|worker|operative)|\bpicker\b|"
    r"\bpacker\b|forklift|material handler|\bdriver\b|delivery|\bcourier\b|\bchauffeur\b|\bjanitor\b|"
    r"custodian|housekeep|\bcleaner\b|groundskeep|landscap|\bporter\b|security guard|\bguard\b|"
    r"\blaborer\b|general labor|\bfactory\b|assembler|machine operator|production (?:worker|associate|operator)|"
    r"\bvalet\b|\bbartender\b|\bdoorman\b|\bmaid\b|sanitation|\bmover\b", re.I)


def prefilter_generic(jobs):
    """Build the SHARED pool: keep any software / CS / tech role at FULL breadth,
    with NO seniority or location filtering and NO coupling to any one profile.
    Per-user scoring narrows each person's feed afterward, so this single pool can
    serve a new grad, a senior, a data scientist, a security engineer, and more.
    A recognized tech title is kept unless it also matches the non-tech blocklist."""
    kept = []
    for j in jobs:
        title = j.get("title", "") or ""
        if MULTIFIELD:
            # multi-field: keep any tech OR professional resume-driven role, and drop
            # only the clearly hourly/manual ones. The non-tech blocklist is NOT applied
            # here, because those professional roles are exactly what we now want.
            if not (TECH_ROLE_RX.search(title) or PROFESSIONAL_ROLE_RX.search(title)):
                continue
            if HOURLY_MANUAL_RX.search(title):
                continue
        else:
            # tech-only (default, unchanged): keep a recognized tech title unless it is
            # also on the non-tech blocklist.
            if not TECH_ROLE_RX.search(title):
                continue
            if NONTECH_RX.search(title):
                continue
        kept.append(j)
    # de-dupe by (company, title), same as prefilter()
    seen, deduped = set(), []
    for j in kept:
        key = ((j.get("company") or "").lower().strip(), (j.get("title") or "").lower().strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    return deduped


SWE_RX = re.compile(
    r"software|engineer|developer|backend|back.?end|front.?end|full.?stack|swe|"
    r"\bsde\b|web|platform|infrastructure|programmer",
    re.I,
)
SENIOR_RX = re.compile(
    r"\bsenior\b|\bstaff\b|\bprincipal\b|\blead\b|\bmanager\b|\bdirector\b|"
    r"\bvp\b|\bhead of\b|\barchitect\b|\bsr\.?\b|\b(ii|iii|iv|v)\b|\b[2-9]\+?\b\s*years",
    re.I,
)


def prefilter(jobs, profile, max_years_for_entry=2):
    """Return only jobs worth sending to the LLM."""
    years = profile.get("years_experience") or 0
    pref = profile.get("preferences") or {}
    pref_locs = [l.lower() for l in (pref.get("locations") or [])]
    remote_ok = pref.get("remote_ok", True)

    kept = []
    for j in jobs:
        title = j.get("title", "")
        if not SWE_RX.search(title):
            continue
        # if candidate is early-career, drop senior-coded titles
        if years <= max_years_for_entry and SENIOR_RX.search(title):
            continue
        # light location gate (only if the candidate specified locations and isn't remote-open)
        loc = (j.get("location") or "").lower()
        if pref_locs and not remote_ok:
            if not (any(p in loc for p in pref_locs) or "remote" in loc):
                continue
        kept.append(j)

    # de-dupe by (company, title)
    seen, deduped = set(), []
    for j in kept:
        key = (j["company"].lower().strip(), j["title"].lower().strip())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(j)
    return deduped
