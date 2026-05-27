"""
Database layer — PostgreSQL schema + access helpers.

Holds the shared job DB (pulled once, served to all users), the self-growing
company registry, profiles, rankings, and contacts. Freshness lives here too:
every job carries first_seen / last_seen / active, and a sync marks any job that
drops out of the latest pull as dead — that's the anti-staleness guarantee.

Uses psycopg (v3). Set DATABASE_URL, e.g.:
    postgresql://user:pass@localhost:5432/jobmatch

If DATABASE_URL is unset, the API falls back to reading ranked_jobs.json so the
whole stack still runs end to end without a database during development.
"""
import hashlib
import os
import time

try:
    import psycopg
    from psycopg.rows import dict_row
    HAVE_PG = True
except ImportError:  # dev without psycopg installed
    HAVE_PG = False


SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL,
    ats         TEXT NOT NULL,
    token       TEXT NOT NULL,
    last_validated TIMESTAMPTZ,
    active      BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (ats, token)
);

CREATE TABLE IF NOT EXISTS jobs (
    id            TEXT PRIMARY KEY,         -- content hash
    company       TEXT NOT NULL,
    title         TEXT NOT NULL,
    location      TEXT,
    url           TEXT,
    description   TEXT,
    ats           TEXT,
    token         TEXT,
    source        TEXT,
    date_posted   BIGINT,
    first_seen    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen     TIMESTAMPTZ NOT NULL DEFAULT now(),
    active        BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE INDEX IF NOT EXISTS idx_jobs_active ON jobs (active);

CREATE TABLE IF NOT EXISTS profiles (
    id      SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    data    JSONB NOT NULL,
    UNIQUE (user_id)
);

CREATE TABLE IF NOT EXISTS rankings (
    id          SERIAL PRIMARY KEY,
    job_id      TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    profile_id  INTEGER NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
    score       INTEGER,
    tier        TEXT,
    reasons     JSONB,
    disqualifiers JSONB,
    matched     JSONB,
    missing     JSONB,
    ranked_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (job_id, profile_id)
);

CREATE TABLE IF NOT EXISTS contacts (
    id           SERIAL PRIMARY KEY,
    job_id       TEXT REFERENCES jobs(id) ON DELETE CASCADE,
    name         TEXT,
    title        TEXT,
    email        TEXT,
    email_status TEXT,
    linkedin     TEXT,
    source       TEXT
);
"""


def job_hash(job):
    """Stable id from the identity of a posting."""
    raw = f"{job.get('company','')}|{job.get('title','')}|{job.get('location','')}".lower()
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


def connect():
    url = os.environ.get("DATABASE_URL")
    if not (HAVE_PG and url):
        return None
    return psycopg.connect(url, row_factory=dict_row)


def init_db(conn):
    with conn.cursor() as cur:
        cur.execute(SCHEMA)
    conn.commit()


def sync_jobs(conn, jobs):
    """Upsert this pull's jobs and mark anything not seen this run as dead.
    Returns (n_upserted, n_marked_dead). This is the freshness engine."""
    now_ids = []
    with conn.cursor() as cur:
        for j in jobs:
            jid = job_hash(j)
            now_ids.append(jid)
            cur.execute(
                """
                INSERT INTO jobs (id, company, title, location, url, description,
                                  ats, token, source, date_posted, active, last_seen)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s, TRUE, now())
                ON CONFLICT (id) DO UPDATE SET
                    last_seen = now(), active = TRUE,
                    description = EXCLUDED.description, url = EXCLUDED.url
                """,
                (jid, j.get("company", ""), j.get("title", ""), j.get("location", ""),
                 j.get("url", ""), j.get("description", ""), j.get("ats", ""),
                 j.get("token", ""), j.get("source", ""), j.get("date_posted")),
            )
        # death detection: anything active but not in this pull is now dead
        if now_ids:
            cur.execute(
                "UPDATE jobs SET active = FALSE WHERE active = TRUE AND id <> ALL(%s)",
                (now_ids,),
            )
            dead = cur.rowcount
        else:
            dead = 0
    conn.commit()
    return len(now_ids), dead


def fetch_ranked(conn, user_id, limit=200):
    """Return active jobs joined with their ranking for this user, best-first."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT j.id, j.company, j.title, j.location, j.url, j.source, j.date_posted,
                   r.score, r.tier, r.reasons, r.disqualifiers, r.matched, r.missing
            FROM jobs j
            JOIN profiles p ON p.user_id = %s
            LEFT JOIN rankings r ON r.job_id = j.id AND r.profile_id = p.id
            WHERE j.active = TRUE
            ORDER BY
                CASE r.tier WHEN 'strong' THEN 0 WHEN 'possible' THEN 1
                            WHEN 'skip' THEN 2 ELSE 3 END,
                r.score DESC NULLS LAST
            LIMIT %s
            """,
            (user_id, limit),
        )
        return cur.fetchall()
