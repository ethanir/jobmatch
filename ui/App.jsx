import React, { useState, useMemo } from "react";

// ───────────────────────────────────────────────────────────────────────────
// JobMatch — ranked feed UI
// Self-contained: mock data lives here so it runs with no backend. In production
// the `JOBS` array is replaced by the ranked_jobs output from the pipeline.
// ───────────────────────────────────────────────────────────────────────────

const JOBS = [
  {
    id: "1", company: "Loop", title: "New Grad Software Engineer, Full-Stack",
    location: "Chicago, IL", posted: "2 days ago", source: "greenhouse",
    tier: "strong", score: 92,
    reasons: [
      "Explicitly a new-grad full-stack role — exact match for your level and focus.",
      "Stack overlap: React + Python backend lines up with BioTrack and your bot projects.",
      "Chicago-based, your top location preference.",
    ],
    matched: ["React", "Python", "FastAPI", "PostgreSQL", "REST APIs"],
    missing: ["Kubernetes"],
    contacts: [
      { name: "Tara Whitfield", title: "Technical Recruiter", email: "tara.whitfield@loop.com", status: "valid", linkedin: "#" },
      { name: "Marcus Lee", title: "Engineering Manager", email: "marcus.lee@loop.com", status: "valid", linkedin: "#" },
    ],
    draft: "Hi Tara,\n\nI just applied to the New Grad Full-Stack role at Loop and wanted to reach out directly. I'm a May 2026 UIC CS grad who ships full-stack products end to end — most recently MixerAI, a multi-model AI Chrome extension live at mixerai.net, plus an iOS app on the App Store.\n\nLoop's full-stack work lines up closely with what I've built (React + FastAPI + Postgres). My resume's attached — I'd love to be considered, and happy to point you to anything else useful.\n\nThanks,\nEthan",
  },
  {
    id: "2", company: "JPMorgan Chase", title: "Software Engineer — 2026 Program",
    location: "Chicago, IL", posted: "4 days ago", source: "workday",
    tier: "strong", score: 86,
    reasons: [
      "Large, structured new-grad program with high intake — strong odds for early career.",
      "In Chicago, your preferred metro.",
      "Backend/full-stack track fits your Python + Java-adjacent experience.",
    ],
    matched: ["Python", "SQL", "REST APIs", "Git"],
    missing: ["Java", "Spring"],
    contacts: [
      { name: "Priya Nadkarni", title: "Recruiter", email: "priya.nadkarni@jpmchase.com", status: "valid", linkedin: "#" },
    ],
    draft: "Hi Priya,\n\nI just applied to the 2026 Software Engineer Program at JPMorgan Chase in Chicago. I'm a UIC CS grad who builds and ships real products — a live AI Chrome extension and a native iOS app on the App Store among them.\n\nI'd love to be considered for the program. Resume attached, and I'm happy to provide anything else you need.\n\nThanks,\nEthan",
  },
  {
    id: "3", company: "Replit", title: "Software Engineer — New Grad, Summer 2026",
    location: "Foster City, CA · Remote", posted: "1 week ago", source: "ashby",
    tier: "possible", score: 71,
    reasons: [
      "Genuine new-grad req, remote-friendly.",
      "Developer-tools company — your AI/extension work is relevant.",
      "Bay Area HQ; remote possible but on-site leans local.",
    ],
    matched: ["TypeScript", "React", "Node.js"],
    missing: ["Go (production)", "Distributed systems"],
    contacts: [
      { name: "Dana Ortiz", title: "Technical Recruiter", email: "dana@replit.com", status: "risky", linkedin: "#" },
    ],
    draft: "Hi Dana,\n\nI just applied to the New Grad SWE role at Replit. As someone who builds developer-facing AI tools (MixerAI, a multi-model Chrome extension), Replit's mission really resonates.\n\nResume attached — I'd love to be considered. Thanks for taking a look.\n\nEthan",
  },
  {
    id: "4", company: "Sierra", title: "Software Engineer, Agent",
    location: "San Francisco, CA · New York, NY", posted: "1 week ago", source: "ashby",
    tier: "possible", score: 64,
    reasons: [
      "AI-agent focus matches your MixerAI orchestration work.",
      "No explicit new-grad signal — may expect some experience.",
      "On-site SF/NYC; relocation required.",
    ],
    matched: ["Python", "TypeScript", "LLM orchestration"],
    missing: ["Production ML", "On-site relocation"],
    contacts: [],
    draft: "Hi there,\n\nI applied to the Software Engineer, Agent role at Sierra. My project MixerAI runs a multi-model orchestration pipeline (draft → synthesize → critique), which lines up closely with agentic work.\n\nResume attached — would love to be considered. Thanks,\nEthan",
  },
  {
    id: "5", company: "Northrop Grumman", title: "Associate Software Engineer",
    location: "Aurora, CO", posted: "5 days ago", source: "workday",
    tier: "skip", score: 38,
    reasons: [
      "Requires an active security clearance you don't currently hold.",
      "Relocation to Colorado required; outside your stated preferences.",
      "Defense embedded focus is a weaker match for your web/full-stack profile.",
    ],
    matched: ["C", "C++"],
    missing: ["Security clearance", "Embedded systems"],
    contacts: [],
    draft: "",
  },
];

const TIERS = {
  strong:   { label: "Strong fit",   dot: "#1f9d55", bg: "#eaf6ef", text: "#176844" },
  possible: { label: "Possible fit", dot: "#c6881b", bg: "#fbf3e2", text: "#8a5d10" },
  skip:     { label: "Skip",         dot: "#9aa0a6", bg: "#f0f1f2", text: "#5f6368" },
};

const FONT_DISPLAY = "'Fraunces', Georgia, serif";
const FONT_BODY = "'Newsreader', Georgia, serif";
const FONT_UI = "'IBM Plex Sans', system-ui, sans-serif";

// Point this at the FastAPI server (server.py). If it's unreachable, the UI
// gracefully falls back to the bundled mock JOBS so it always renders.
const API_BASE = "http://127.0.0.1:8000";

export default function App() {
  const [filter, setFilter] = useState("all");
  const [selectedId, setSelectedId] = useState(null);
  const [copied, setCopied] = useState(false);
  const [jobs, setJobs] = useState([]);
  const [status, setStatus] = useState("loading"); // loading | live | mock | error
  const [scanOpen, setScanOpen] = useState(false);
  const [scanText, setScanText] = useState("");
  const [scanBusy, setScanBusy] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [scanError, setScanError] = useState("");

  React.useEffect(() => {
    let cancelled = false;
    const ctrl = new AbortController();
    const timeout = setTimeout(() => ctrl.abort(), 4000);
    fetch(`${API_BASE}/api/jobs?user_id=me&tier=all`, { signal: ctrl.signal })
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((data) => {
        if (cancelled) return;
        const list = Array.isArray(data.jobs) && data.jobs.length ? data.jobs : JOBS;
        setJobs(list);
        setStatus(Array.isArray(data.jobs) && data.jobs.length ? "live" : "mock");
        setSelectedId(list[0]?.id ?? null);
      })
      .catch(() => {
        if (cancelled) return;
        setJobs(JOBS);            // graceful fallback to bundled sample
        setStatus("mock");
        setSelectedId(JOBS[0]?.id ?? null);
      })
      .finally(() => clearTimeout(timeout));
    return () => { cancelled = true; ctrl.abort(); clearTimeout(timeout); };
  }, []);

  const filtered = useMemo(() => {
    const base = filter === "all" ? jobs : jobs.filter((j) => j.tier === filter);
    const rank = { strong: 0, possible: 1, skip: 2 };
    return [...base].sort((a, b) => (rank[a.tier] ?? 3) - (rank[b.tier] ?? 3) || b.score - a.score);
  }, [filter, jobs]);

  const selected = jobs.find((j) => j.id === selectedId) || filtered[0] || null;
  const counts = {
    all: jobs.length,
    strong: jobs.filter((j) => j.tier === "strong").length,
    possible: jobs.filter((j) => j.tier === "possible").length,
    skip: jobs.filter((j) => j.tier === "skip").length,
  };

  const copyDraft = () => {
    if (!selected?.draft) return;
    navigator.clipboard?.writeText(selected.draft);
    setCopied(true);
    setTimeout(() => setCopied(false), 1600);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#f6f4ef", color: "#1a1a17", fontFamily: FONT_BODY }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,400;9..144,500;9..144,600&family=Newsreader:opsz,wght@6..72,400;6..72,500&family=IBM+Plex+Sans:wght@400;500;600&display=swap');
        * { box-sizing: border-box; }
        ::selection { background: #d9e8df; }
        .jm-row { transition: background .15s ease, border-color .15s ease; }
        .jm-row:hover { background: #fffdf8; }
        .jm-chip { transition: all .15s ease; }
        .jm-btn { transition: transform .08s ease, background .15s ease, border-color .15s ease; }
        .jm-btn:active { transform: translateY(1px); }
        @keyframes jmIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
        .jm-detail { animation: jmIn .22s ease both; }
      `}</style>

      {/* Header */}
      <header style={{ borderBottom: "1px solid #e4e0d6", background: "#f6f4ef", position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ maxWidth: 1180, margin: "0 auto", padding: "20px 28px", display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 14 }}>
            <span style={{ fontFamily: FONT_DISPLAY, fontSize: 26, fontWeight: 600, letterSpacing: "-0.02em" }}>JobMatch</span>
            <span style={{ fontFamily: FONT_UI, fontSize: 12.5, color: "#8a8578", letterSpacing: ".02em" }}>
              ranked for <strong style={{ color: "#3a382f", fontWeight: 600 }}>Ethan Irimiciuc</strong> · Software Engineering
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <button onClick={() => { setScanOpen(true); setScanResult(null); setScanError(""); }} className="jm-btn"
              style={{ cursor: "pointer", fontFamily: FONT_UI, fontSize: 13, fontWeight: 600,
                padding: "7px 14px", borderRadius: 999, border: "1px solid #1a1a17",
                background: "#1a1a17", color: "#f6f4ef" }}>
              + Scan a role
            </button>
            <span style={{ fontFamily: FONT_UI, fontSize: 12, color: "#9a9486", display: "flex", alignItems: "center", gap: 7 }}>
              <span style={{ width: 7, height: 7, borderRadius: 999, background: status === "live" ? "#1f9d55" : "#c6881b" }} />
              {status === "live" ? `${counts.all} live roles` : status === "loading" ? "loading…" : `${counts.all} sample roles`} · updated today
            </span>
          </div>
        </div>
      </header>

      {status === "loading" ? (
        <div style={{ maxWidth: 1180, margin: "0 auto", padding: "80px 28px", textAlign: "center", fontFamily: FONT_UI, fontSize: 14, color: "#9a9486" }}>
          Loading your ranked roles…
        </div>
      ) : (
      <main style={{ maxWidth: 1180, margin: "0 auto", padding: "28px", display: "grid", gridTemplateColumns: "minmax(360px, 1fr) minmax(440px, 1.25fr)", gap: 28, alignItems: "start" }}>
        {/* Left: filters + list */}
        <section>
          <div style={{ display: "flex", gap: 8, marginBottom: 18, flexWrap: "wrap" }}>
            {[
              ["all", "All"], ["strong", "Strong"], ["possible", "Possible"], ["skip", "Skip"],
            ].map(([key, label]) => {
              const active = filter === key;
              return (
                <button key={key} onClick={() => setFilter(key)} className="jm-btn jm-chip"
                  style={{
                    fontFamily: FONT_UI, fontSize: 13, fontWeight: 500, cursor: "pointer",
                    padding: "7px 14px", borderRadius: 999,
                    border: active ? "1px solid #1a1a17" : "1px solid #e0dcd1",
                    background: active ? "#1a1a17" : "transparent",
                    color: active ? "#f6f4ef" : "#56524a",
                  }}>
                  {label} <span style={{ opacity: .55, marginLeft: 3 }}>{counts[key]}</span>
                </button>
              );
            })}
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 0, border: "1px solid #e4e0d6", borderRadius: 14, overflow: "hidden", background: "#fdfcf8" }}>
            {filtered.map((job, i) => {
              const t = TIERS[job.tier];
              const active = job.id === selected?.id;
              return (
                <button key={job.id} onClick={() => setSelectedId(job.id)} className="jm-row"
                  style={{
                    textAlign: "left", cursor: "pointer", padding: "16px 18px",
                    borderBottom: i < filtered.length - 1 ? "1px solid #ece8dd" : "none",
                    borderLeft: active ? "3px solid #1a1a17" : "3px solid transparent",
                    background: active ? "#fffdf8" : "transparent", fontFamily: FONT_BODY,
                  }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 10 }}>
                    <span style={{ fontFamily: FONT_UI, fontSize: 12.5, fontWeight: 600, color: "#6f6a5d", textTransform: "uppercase", letterSpacing: ".04em" }}>{job.company}</span>
                    <ScoreBadge tier={job.tier} score={job.score} />
                  </div>
                  <div style={{ fontFamily: FONT_DISPLAY, fontSize: 18, fontWeight: 500, margin: "5px 0 7px", lineHeight: 1.18, letterSpacing: "-0.01em" }}>{job.title}</div>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, fontFamily: FONT_UI, fontSize: 12.5, color: "#8a8578" }}>
                    <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
                      <span style={{ width: 6, height: 6, borderRadius: 999, background: t.dot }} /> {t.label}
                    </span>
                    <span>·</span><span>{job.location}</span><span>·</span><span>{job.posted}</span>
                  </div>
                </button>
              );
            })}
          </div>
        </section>

        {/* Right: detail */}
        {selected && (
          <section key={selected.id} className="jm-detail" style={{ position: "sticky", top: 92, border: "1px solid #e4e0d6", borderRadius: 16, background: "#fdfcf8", overflow: "hidden" }}>
            <div style={{ padding: "26px 28px 22px", borderBottom: "1px solid #ece8dd" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
                <div>
                  <div style={{ fontFamily: FONT_UI, fontSize: 13, fontWeight: 600, color: "#6f6a5d", textTransform: "uppercase", letterSpacing: ".05em", marginBottom: 6 }}>{selected.company}</div>
                  <h1 style={{ fontFamily: FONT_DISPLAY, fontSize: 27, fontWeight: 600, margin: 0, lineHeight: 1.12, letterSpacing: "-0.02em" }}>{selected.title}</h1>
                  <div style={{ fontFamily: FONT_UI, fontSize: 13, color: "#8a8578", marginTop: 10, display: "flex", gap: 9, flexWrap: "wrap" }}>
                    <span>{selected.location}</span><span>·</span><span>{selected.posted}</span><span>·</span><span style={{ textTransform: "capitalize" }}>{selected.source}</span>
                  </div>
                </div>
                <ScoreRing tier={selected.tier} score={selected.score} />
              </div>
            </div>

            <div style={{ padding: "22px 28px" }}>
              <SectionLabel>Why this {selected.tier === "skip" ? "isn't" : "is"} a fit</SectionLabel>
              <ul style={{ margin: "0 0 22px", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 9 }}>
                {selected.reasons.map((r, i) => (
                  <li key={i} style={{ display: "flex", gap: 10, fontSize: 15.5, lineHeight: 1.5, color: "#33312a" }}>
                    <span style={{ color: TIERS[selected.tier].dot, marginTop: 2, flexShrink: 0 }}>{selected.tier === "skip" ? "✕" : "→"}</span>
                    <span>{r}</span>
                  </li>
                ))}
              </ul>

              <div style={{ display: "flex", gap: 26, marginBottom: 22, flexWrap: "wrap" }}>
                <div style={{ flex: 1, minWidth: 160 }}>
                  <SectionLabel>You match</SectionLabel>
                  <ChipRow items={selected.matched} kind="match" />
                </div>
                {selected.missing.length > 0 && (
                  <div style={{ flex: 1, minWidth: 160 }}>
                    <SectionLabel>Gaps</SectionLabel>
                    <ChipRow items={selected.missing} kind="gap" />
                  </div>
                )}
              </div>

              {/* Contacts + action */}
              {selected.tier !== "skip" ? (
                <>
                  <SectionLabel>Who to reach</SectionLabel>
                  {selected.contacts.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 20 }}>
                      {selected.contacts.map((c, i) => (
                        <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "11px 14px", border: "1px solid #ece8dd", borderRadius: 10, background: "#fffdf8" }}>
                          <div>
                            <div style={{ fontFamily: FONT_UI, fontSize: 14, fontWeight: 600, color: "#2a2823" }}>{c.name}</div>
                            <div style={{ fontFamily: FONT_UI, fontSize: 12.5, color: "#8a8578" }}>{c.title} · {c.email}</div>
                          </div>
                          <EmailStatus status={c.status} />
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ fontFamily: FONT_UI, fontSize: 13.5, color: "#9a9486", margin: "0 0 20px" }}>No verified contact found yet — apply directly, or check LinkedIn for the hiring team.</p>
                  )}

                  {selected.draft && (
                    <>
                      <SectionLabel>Outreach draft</SectionLabel>
                      <div style={{ position: "relative", border: "1px solid #ece8dd", borderRadius: 12, background: "#fbfaf4", padding: "16px 18px", marginBottom: 16 }}>
                        <pre style={{ margin: 0, fontFamily: FONT_BODY, fontSize: 14.5, lineHeight: 1.55, color: "#33312a", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{selected.draft}</pre>
                      </div>
                    </>
                  )}

                  <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
                    <a className="jm-btn" href="#" onClick={(e) => e.preventDefault()}
                      style={{ flex: 1, minWidth: 150, textAlign: "center", textDecoration: "none", fontFamily: FONT_UI, fontSize: 14, fontWeight: 600, padding: "13px 18px", borderRadius: 10, background: "#1a1a17", color: "#f6f4ef", border: "1px solid #1a1a17" }}>
                      Apply on {selected.source.charAt(0).toUpperCase() + selected.source.slice(1)} →
                    </a>
                    {selected.draft && (
                      <button className="jm-btn" onClick={copyDraft}
                        style={{ flex: 1, minWidth: 150, cursor: "pointer", fontFamily: FONT_UI, fontSize: 14, fontWeight: 600, padding: "13px 18px", borderRadius: 10, background: "transparent", color: "#1a1a17", border: "1px solid #cfcabc" }}>
                        {copied ? "Copied ✓" : "Copy email draft"}
                      </button>
                    )}
                  </div>
                </>
              ) : (
                <div style={{ padding: "16px 18px", border: "1px dashed #d8d3c6", borderRadius: 12, background: "#f7f6f1", fontFamily: FONT_UI, fontSize: 13.5, color: "#7a756a", lineHeight: 1.55 }}>
                  This role is flagged <strong>skip</strong>, so no contacts or draft were generated. Spend your effort on the strong matches instead.
                </div>
              )}
            </div>
          </section>
        )}
      </main>
      )}

      {scanOpen && (
        <div onClick={() => !scanBusy && setScanOpen(false)}
          style={{ position: "fixed", inset: 0, background: "rgba(26,26,23,0.45)", backdropFilter: "blur(3px)",
            display: "flex", alignItems: "center", justifyContent: "center", zIndex: 100, padding: 20 }}>
          <div onClick={(e) => e.stopPropagation()} className="jm-detail"
            style={{ background: "#fdfcf8", borderRadius: 16, border: "1px solid #e4e0d6",
              width: "100%", maxWidth: 720, maxHeight: "90vh", overflow: "auto" }}>
            <div style={{ padding: "22px 26px", borderBottom: "1px solid #ece8dd", display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
              <div>
                <h2 style={{ fontFamily: FONT_DISPLAY, fontSize: 22, fontWeight: 600, margin: 0, letterSpacing: "-0.01em" }}>Scan a role</h2>
                <p style={{ fontFamily: FONT_UI, fontSize: 13, color: "#8a8578", margin: "6px 0 0" }}>
                  Paste a job description (or a URL) from LinkedIn, Handshake, or anywhere. We'll rank it, find the recruiter, and draft your outreach.
                </p>
              </div>
              <button onClick={() => !scanBusy && setScanOpen(false)} aria-label="close"
                style={{ cursor: "pointer", background: "transparent", border: "none", fontSize: 22, color: "#8a8578", padding: 4 }}>×</button>
            </div>

            {!scanResult ? (
              <div style={{ padding: "20px 26px" }}>
                <textarea value={scanText} onChange={(e) => setScanText(e.target.value)} disabled={scanBusy}
                  placeholder="Paste the job description here — or a https:// URL to the posting."
                  style={{ width: "100%", minHeight: 220, padding: "14px 16px", borderRadius: 10,
                    border: "1px solid #cfcabc", background: "#fffdf8", color: "#1a1a17",
                    fontFamily: FONT_UI, fontSize: 14, lineHeight: 1.55, resize: "vertical",
                    outline: "none" }} />
                {scanError && (
                  <div style={{ marginTop: 12, fontFamily: FONT_UI, fontSize: 13, color: "#a13a2c" }}>
                    {scanError}
                  </div>
                )}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: 16, gap: 12 }}>
                  <span style={{ fontFamily: FONT_UI, fontSize: 12, color: "#9a9486" }}>
                    {scanText.length} chars
                  </span>
                  <div style={{ display: "flex", gap: 8 }}>
                    <button onClick={() => !scanBusy && setScanOpen(false)} disabled={scanBusy} className="jm-btn"
                      style={{ cursor: scanBusy ? "default" : "pointer", fontFamily: FONT_UI, fontSize: 14, fontWeight: 500,
                        padding: "10px 16px", borderRadius: 10, background: "transparent",
                        color: "#56524a", border: "1px solid #cfcabc", opacity: scanBusy ? 0.5 : 1 }}>
                      Cancel
                    </button>
                    <button onClick={runScan} disabled={scanBusy || !scanText.trim()} className="jm-btn"
                      style={{ cursor: (scanBusy || !scanText.trim()) ? "default" : "pointer", fontFamily: FONT_UI, fontSize: 14, fontWeight: 600,
                        padding: "10px 18px", borderRadius: 10, background: "#1a1a17",
                        color: "#f6f4ef", border: "1px solid #1a1a17",
                        opacity: (scanBusy || !scanText.trim()) ? 0.55 : 1 }}>
                      {scanBusy ? "Scanning…" : "Scan this role"}
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <ScanResult result={scanResult} onClear={() => { setScanResult(null); setScanText(""); }} onCopyDraft={() => {
                if (scanResult.draft) {
                  navigator.clipboard?.writeText(scanResult.draft);
                  setCopied(true); setTimeout(() => setCopied(false), 1600);
                }
              }} copied={copied} />
            )}
          </div>
        </div>
      )}
    </div>
  );

  async function runScan() {
    setScanBusy(true);
    setScanError("");
    try {
      const res = await fetch(`${API_BASE}/api/scan`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: scanText, user_id: "me" }),
      });
      if (!res.ok) {
        const msg = await res.text();
        throw new Error(`server returned ${res.status}: ${msg.slice(0, 140)}`);
      }
      const data = await res.json();
      setScanResult(data);
    } catch (e) {
      setScanError(
        e.name === "TypeError"
          ? "Couldn't reach the scan API. Start the server (uvicorn server:app) and try again."
          : e.message
      );
    } finally {
      setScanBusy(false);
    }
  }
}

function ScanResult({ result, onClear, onCopyDraft, copied }) {
  const r = result || {};
  const tier = r.tier || "possible";
  const t = TIERS[tier];
  return (
    <div style={{ padding: "22px 26px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16, marginBottom: 18 }}>
        <div>
          <div style={{ fontFamily: FONT_UI, fontSize: 12.5, fontWeight: 600, color: "#6f6a5d", textTransform: "uppercase", letterSpacing: ".04em", marginBottom: 4 }}>{r.company || "Scanned role"}</div>
          <h3 style={{ fontFamily: FONT_DISPLAY, fontSize: 21, fontWeight: 600, margin: 0, lineHeight: 1.18, letterSpacing: "-0.01em" }}>{r.title || "(no title)"}</h3>
          <div style={{ fontFamily: FONT_UI, fontSize: 12.5, color: "#8a8578", marginTop: 6, display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
            <span style={{ display: "inline-flex", alignItems: "center", gap: 5 }}>
              <span style={{ width: 6, height: 6, borderRadius: 999, background: t.dot }} /> {t.label}
            </span>
            {r.location && <><span>·</span><span>{r.location}</span></>}
          </div>
        </div>
        <ScoreRing tier={tier} score={r.score || 0} />
      </div>

      {r.reasons?.length > 0 && (
        <>
          <SectionLabel>Why this {tier === "skip" ? "isn't" : "is"} a fit</SectionLabel>
          <ul style={{ margin: "0 0 18px", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 8 }}>
            {r.reasons.map((reason, i) => (
              <li key={i} style={{ display: "flex", gap: 10, fontSize: 15, lineHeight: 1.5, color: "#33312a" }}>
                <span style={{ color: t.dot, marginTop: 2, flexShrink: 0 }}>{tier === "skip" ? "✕" : "→"}</span>
                <span>{reason}</span>
              </li>
            ))}
          </ul>
        </>
      )}

      {(r.matched?.length > 0 || r.missing?.length > 0) && (
        <div style={{ display: "flex", gap: 22, marginBottom: 18, flexWrap: "wrap" }}>
          {r.matched?.length > 0 && (
            <div style={{ flex: 1, minWidth: 160 }}>
              <SectionLabel>You match</SectionLabel><ChipRow items={r.matched} kind="match" />
            </div>
          )}
          {r.missing?.length > 0 && (
            <div style={{ flex: 1, minWidth: 160 }}>
              <SectionLabel>Gaps</SectionLabel><ChipRow items={r.missing} kind="gap" />
            </div>
          )}
        </div>
      )}

      {r.contacts?.length > 0 && (
        <>
          <SectionLabel>Who to reach</SectionLabel>
          <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
            {r.contacts.map((c, i) => (
              <div key={i} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, padding: "10px 14px", border: "1px solid #ece8dd", borderRadius: 10, background: "#fffdf8" }}>
                <div>
                  <div style={{ fontFamily: FONT_UI, fontSize: 14, fontWeight: 600, color: "#2a2823" }}>{c.name}</div>
                  <div style={{ fontFamily: FONT_UI, fontSize: 12.5, color: "#8a8578" }}>{c.title} · {c.email}</div>
                </div>
                <EmailStatus status={c.status} />
              </div>
            ))}
          </div>
        </>
      )}

      {r.draft && (
        <>
          <SectionLabel>Outreach draft</SectionLabel>
          <div style={{ border: "1px solid #ece8dd", borderRadius: 12, background: "#fbfaf4", padding: "14px 16px", marginBottom: 14 }}>
            <pre style={{ margin: 0, fontFamily: FONT_BODY, fontSize: 14, lineHeight: 1.55, color: "#33312a", whiteSpace: "pre-wrap", wordBreak: "break-word" }}>{r.draft}</pre>
          </div>
        </>
      )}

      <div style={{ display: "flex", gap: 10, marginTop: 6 }}>
        <button onClick={onClear} className="jm-btn"
          style={{ cursor: "pointer", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 14, fontWeight: 500,
            padding: "10px 16px", borderRadius: 10, background: "transparent",
            color: "#56524a", border: "1px solid #cfcabc" }}>
          Scan another
        </button>
        {r.draft && (
          <button onClick={onCopyDraft} className="jm-btn"
            style={{ cursor: "pointer", fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 14, fontWeight: 600,
              padding: "10px 16px", borderRadius: 10, background: "#1a1a17",
              color: "#f6f4ef", border: "1px solid #1a1a17" }}>
            {copied ? "Copied ✓" : "Copy draft"}
          </button>
        )}
      </div>
    </div>
  );
}

function SectionLabel({ children }) {
  return (
    <div style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 11, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".09em", color: "#a39d8e", marginBottom: 11 }}>
      {children}
    </div>
  );
}

function ScoreBadge({ tier, score }) {
  const t = TIERS[tier];
  return (
    <span style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 12, fontWeight: 600, color: t.text, background: t.bg, padding: "2px 9px", borderRadius: 999, flexShrink: 0 }}>{score}</span>
  );
}

function ScoreRing({ tier, score }) {
  const t = TIERS[tier];
  const r = 26, c = 2 * Math.PI * r, off = c * (1 - score / 100);
  return (
    <div style={{ position: "relative", width: 64, height: 64, flexShrink: 0 }}>
      <svg width="64" height="64" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="32" cy="32" r={r} fill="none" stroke="#ece8dd" strokeWidth="5" />
        <circle cx="32" cy="32" r={r} fill="none" stroke={t.dot} strokeWidth="5" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off} style={{ transition: "stroke-dashoffset .5s ease" }} />
      </svg>
      <div style={{ position: "absolute", inset: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontFamily: "'Fraunces', serif", fontSize: 19, fontWeight: 600, lineHeight: 1, color: "#1a1a17" }}>{score}</span>
        <span style={{ fontFamily: "'IBM Plex Sans', sans-serif", fontSize: 8.5, fontWeight: 600, textTransform: "uppercase", letterSpacing: ".06em", color: t.text }}>fit</span>
      </div>
    </div>
  );
}

function ChipRow({ items, kind }) {
  const style = kind === "match"
    ? { color: "#176844", background: "#eaf6ef", border: "1px solid #cfe7d8" }
    : { color: "#8a5d10", background: "#fbf3e2", border: "1px solid #ecdcb8" };
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
      {items.map((it, i) => (
        <span key={i} style={{ ...style, fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 12.5, fontWeight: 500, padding: "3px 10px", borderRadius: 7 }}>{it}</span>
      ))}
    </div>
  );
}

function EmailStatus({ status }) {
  const map = {
    valid: { label: "Verified", color: "#176844", bg: "#eaf6ef" },
    risky: { label: "Risky", color: "#8a5d10", bg: "#fbf3e2" },
    invalid: { label: "Invalid", color: "#a13a2c", bg: "#f8ebe8" },
  };
  const s = map[status] || { label: "Unknown", color: "#5f6368", bg: "#f0f1f2" };
  return (
    <span style={{ fontFamily: "'IBM Plex Sans', system-ui, sans-serif", fontSize: 11, fontWeight: 600, color: s.color, background: s.bg, padding: "3px 9px", borderRadius: 999, flexShrink: 0, whiteSpace: "nowrap" }}>{s.label}</span>
  );
}
