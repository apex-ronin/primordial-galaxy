"""SQLite spine for the Observatory.

One file, no server, no cloud. Lives at <repo>/data/primordial.db (gitignored as
runtime data — it is fully regenerable from opportunities.json + scan logs).

Four tables:
  runs               — one row per scanner run: when, how long, status,
                       per-source counts, which LLM tier actually served,
                       errors, log path.
  opportunities      — deduped by link; carries the full scored record plus
                       first_seen / last_seen so the dashboard can show
                       history/trend.
  corpus_docs        — the knowledge store the ORACLE agents draw on (govinfo,
                       FAR, DFARS, EOs, GAO/IG fraud cases). Deduped by
                       (source, citation).
  entity_procurement — Arc #6 Heartland Phase 1: one row per Census-of-
                       Governments entity (principalities-index, 78,291
                       units). Tracks whether its website is live, whether a
                       procurement/bids page was located, and which shared
                       portal platform (if any) it runs on. Deduped by
                       entity_id (the Census GIDID).
  outreach_review    — Arc #6 Heartland review queue (2026-08-11, Jay's
                       directive: his eyes on everything before it sends).
                       One row per entity flagged worth his attention, with a
                       generated draft. Nothing here ever sends itself --
                       "approved" just means Jay has seen it and the draft is
                       ready for HIM to send from his own email client.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager

# Repo root = parent of this package dir. DB lives under data/ (already gitignored).
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(_REPO_ROOT, "data", "primordial.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at          TEXT,
    finished_at         TEXT,
    duration_sec        REAL,
    status              TEXT,   -- success | partial | failed
    total_found         INTEGER,
    total_scored        INTEGER,
    high_count          INTEGER,
    medium_count        INTEGER,
    low_count           INTEGER,
    sources_json        TEXT,   -- {"CSDA (Honey Pot)": 9, "SAM.gov (The Whale)": 13, ...}
    errors_json         TEXT,   -- orchestrator.errors list
    tier_served         TEXT,   -- dominant served tier name, e.g. "venice"
    tier_breakdown_json TEXT,   -- {"venice (llama-3.3-70b)": 64}
    local_tier_used     INTEGER,-- 1 if the local LM Studio tier served any record
    log_path            TEXT,
    git_commit          TEXT
);

CREATE TABLE IF NOT EXISTS opportunities (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    link                    TEXT UNIQUE,
    title                   TEXT,
    source                  TEXT,
    snippet                 TEXT,
    win_probability         INTEGER,
    fit_label               TEXT,
    project_type            TEXT,
    estimated_value         TEXT,
    remote_friendly         INTEGER,
    small_business_setaside INTEGER,
    pdf_status              TEXT,
    strategic_notes         TEXT,
    vulnerability_score     INTEGER,
    primary_vector          TEXT,
    exploit_scenario        TEXT,
    clause_title            TEXT,
    clause_text             TEXT,
    analysis_method         TEXT,
    first_seen              TEXT,
    last_seen               TEXT,
    last_run_id             INTEGER,
    raw_json                TEXT,
    FOREIGN KEY(last_run_id) REFERENCES runs(run_id)
);

CREATE TABLE IF NOT EXISTS corpus_docs (
    doc_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    source      TEXT,   -- govinfo | far | dfars | eo | gao | omb | state
    collection  TEXT,   -- e.g. CFR, FR, BILLS, GAOREPORTS
    citation    TEXT,   -- e.g. "FAR 52.240-93", "EO 14319"
    title       TEXT,
    url         TEXT,   -- primary source URL (CLAUDE.md principle #3)
    published   TEXT,
    fetched_at  TEXT,
    text        TEXT,
    embedded    INTEGER DEFAULT 0,
    meta_json   TEXT,
    UNIQUE(source, citation)
);

CREATE TABLE IF NOT EXISTS entity_procurement (
    entity_id               TEXT PRIMARY KEY,  -- Census GIDID, e.g. "1100100100000"
    name                    TEXT,
    state_code              TEXT,
    government_type         TEXT,   -- Census type code + label, e.g. "1 - COUNTY"
    county                  TEXT,
    population              INTEGER,
    website                 TEXT,   -- input: contact_skeleton.web_address from principalities-index
    contact_email           TEXT,   -- input: contact_skeleton.caio_email from principalities-index -- usually NULL
    website_live            INTEGER,-- 0 | 1 | NULL(not yet checked)
    website_status_code     INTEGER,
    procurement_url         TEXT,   -- discovered bids/RFP/procurement page, if any
    procurement_confidence  TEXT,   -- domain_signature | keyword_match | NULL
    portal_platform         TEXT,   -- bidnet_direct | bonfire | opengov_procurenow | demandstar |
                                    -- publicpurchase | questcdn | ionwave | periscope_bidsync |
                                    -- cit_e | custom_html | none | unknown
    verify_status           TEXT,   -- pending | verified | no_website | site_down | no_procurement_found | error
    verify_attempts         INTEGER DEFAULT 0,
    error_detail            TEXT,
    first_seen              TEXT,
    last_seen               TEXT,
    last_verified_at        TEXT,
    far_citations_json      TEXT,   -- JSON list of FAR/DFARS clause numbers found on procurement_url's
                                    -- page text, e.g. ["52.204-21"] -- a marker the solicitation carries
                                    -- federal grant flow-down clauses, worth a human compliance look.
                                    -- NULL = not scanned yet; "[]" = scanned, none found.
    meta_json               TEXT
);

CREATE TABLE IF NOT EXISTS outreach_review (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id      TEXT,   -- FK to entity_procurement.entity_id
    reason         TEXT,   -- human-readable why this was flagged
    priority_score INTEGER,
    contact_email  TEXT,   -- from principalities-index contact_skeleton.caio_email -- usually NULL;
                           -- when NULL the dashboard must say so plainly, never imply a verified recipient
    draft_subject  TEXT,
    draft_body     TEXT,
    status         TEXT DEFAULT 'pending_review',  -- pending_review | approved | dismissed
    created_at     TEXT,
    decided_at     TEXT,
    UNIQUE(entity_id)
);

CREATE TABLE IF NOT EXISTS opportunity_documents (
    link            TEXT PRIMARY KEY,  -- same key as opportunities.link
    content_hash    TEXT,              -- sha256 of raw_text, detects a re-posted/amended link
    raw_text_path   TEXT,              -- path under data/opportunity_archive/, full fetched text
    char_count      INTEGER,
    first_seen      TEXT,
    last_seen       TEXT,
    retention_until TEXT               -- Jay's directive (2026-09-07): keep every RFP/grant
                                        -- regardless of score, for a retention window (default
                                        -- ~2 years, ARCHIVE_RETENTION_DAYS env-overridable) --
                                        -- metadata only for now, no auto-delete job yet.
);

CREATE INDEX IF NOT EXISTS idx_opp_win   ON opportunities(win_probability DESC);
CREATE INDEX IF NOT EXISTS idx_opp_run   ON opportunities(last_run_id);
CREATE INDEX IF NOT EXISTS idx_runs_time ON runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_corpus_src ON corpus_docs(source);
CREATE INDEX IF NOT EXISTS idx_entproc_state  ON entity_procurement(state_code);
CREATE INDEX IF NOT EXISTS idx_entproc_status ON entity_procurement(verify_status);
CREATE INDEX IF NOT EXISTS idx_entproc_portal ON entity_procurement(portal_platform);
CREATE INDEX IF NOT EXISTS idx_outreach_status   ON outreach_review(status);
CREATE INDEX IF NOT EXISTS idx_outreach_priority ON outreach_review(priority_score DESC);
"""


def _ensure_parent() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open a connection with row access by name and FK enforcement on."""
    _ensure_parent()
    conn = sqlite3.connect(db_path or DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 30000")  # wait, don't error, on concurrent writes
    return conn


# Columns added to entity_procurement after its first release. CREATE TABLE IF
# NOT EXISTS is a no-op on an already-existing table, so new columns need an
# explicit ALTER TABLE -- this keeps the live DB (with real, slow-to-redo
# verification results) intact instead of requiring a drop/recreate.
_ENTITY_PROCUREMENT_MIGRATIONS = [
    ("contact_email", "TEXT"),
    ("far_citations_json", "TEXT"),
]


def _migrate(conn: sqlite3.Connection) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(entity_procurement)")}
    for col, coltype in _ENTITY_PROCUREMENT_MIGRATIONS:
        if col not in existing:
            conn.execute(f"ALTER TABLE entity_procurement ADD COLUMN {col} {coltype}")


def init_db(db_path: str | None = None) -> None:
    """Create tables/indexes if absent, then apply any pending column migrations. Idempotent."""
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
        _migrate(conn)
        conn.commit()


@contextmanager
def session(db_path: str | None = None):
    """Context-managed connection that commits on success, rolls back on error."""
    conn = connect(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------

def insert_run(conn: sqlite3.Connection, run: dict) -> int:
    """Insert a run row, return its run_id."""
    cols = [
        "started_at", "finished_at", "duration_sec", "status",
        "total_found", "total_scored", "high_count", "medium_count", "low_count",
        "sources_json", "errors_json", "tier_served", "tier_breakdown_json",
        "local_tier_used", "log_path", "git_commit",
    ]
    placeholders = ", ".join("?" for _ in cols)
    cur = conn.execute(
        f"INSERT INTO runs ({', '.join(cols)}) VALUES ({placeholders})",
        [run.get(c) for c in cols],
    )
    return cur.lastrowid


def get_opportunity_by_link(conn: sqlite3.Connection, link: str) -> dict | None:
    """Look up a previously-scored opportunity by link, or None if never seen.

    Basis for the delta pipeline (Jay's directive, 2026-09-07): main.py checks
    this before paying for a document fetch + LLM score. `opportunities` already
    accumulates one row per link across every run (see upsert_opportunity),
    first_seen preserved -- no new table needed just to know "have we seen this."
    """
    row = conn.execute("SELECT * FROM opportunities WHERE link = ?", (link,)).fetchone()
    return dict(row) if row else None


def upsert_opportunity_document(conn: sqlite3.Connection, doc: dict) -> None:
    """Insert or refresh a raw-text archive row, keyed on link. See observatory/archive.py."""
    cols = ["link", "content_hash", "raw_text_path", "char_count",
            "first_seen", "last_seen", "retention_until"]
    update_cols = [c for c in cols if c not in ("link", "first_seen")]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO opportunity_documents ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(link) DO UPDATE SET {set_clause}",
        [doc.get(c) for c in cols],
    )


def upsert_opportunity(conn: sqlite3.Connection, opp: dict, run_id: int, seen_at: str) -> None:
    """Insert or update an opportunity keyed on its link.

    first_seen is preserved across runs; last_seen / last_run_id and the scored
    fields refresh each time we see the link again.
    """
    rt = opp.get("red_team") or {}
    im = opp.get("immune_system") or {}
    row = {
        "link": opp.get("link"),
        "title": opp.get("title"),
        "source": opp.get("source"),
        "snippet": opp.get("snippet"),
        "win_probability": opp.get("win_probability"),
        "fit_label": opp.get("fit_label"),
        "project_type": opp.get("project_type"),
        "estimated_value": opp.get("estimated_value"),
        "remote_friendly": int(bool(opp.get("remote_friendly"))) if opp.get("remote_friendly") is not None else None,
        "small_business_setaside": int(bool(opp.get("small_business_setaside"))) if opp.get("small_business_setaside") is not None else None,
        "pdf_status": opp.get("pdf_status"),
        "strategic_notes": opp.get("strategic_notes"),
        "vulnerability_score": rt.get("vulnerability_score"),
        "primary_vector": rt.get("primary_vector"),
        "exploit_scenario": rt.get("exploit_scenario"),
        "clause_title": im.get("clause_title"),
        "clause_text": im.get("clause_text"),
        "analysis_method": opp.get("analysis_method"),
        "last_seen": seen_at,
        "last_run_id": run_id,
        "raw_json": _dumps(opp),
    }
    update_cols = [k for k in row if k != "link"]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
    cols = ["link", "first_seen"] + update_cols
    placeholders = ", ".join("?" for _ in cols)
    values = [row["link"], seen_at] + [row[c] for c in update_cols]
    conn.execute(
        f"INSERT INTO opportunities ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(link) DO UPDATE SET {set_clause}",
        values,
    )


def upsert_corpus_doc(conn: sqlite3.Connection, doc: dict) -> None:
    """Insert or update a knowledge-store document keyed on (source, citation).

    Used by the govinfo / FAR / DFARS / EO ingest (arc #3) and read by the
    ORACLE agents (arc #4).

    2026-09-06 fix: ingest.py's fetch_* functions write cheap metadata rows with
    text="" (or, for EOs, Federal Register's often-empty `abstract`) -- the real
    body is filled later, lazily, by fulltext.py's separate rate-limited pass.
    Before this fix, text=excluded.text unconditionally overwrote on conflict,
    so once scheduling re-runs ingest on a cron, any text fulltext.fill() had
    already backfilled would get silently wiped back to empty on the next sweep
    (embedded flag too, along with it -- see below). Never let a re-ingest
    replace non-empty text with empty; a later fulltext.fill() pass can still
    overwrite text going the other way (empty -> real body).

    2026-09-07 fix: the embedded guard above was too blunt -- "once embedded=1,
    stay 1 forever" also blocked a legitimate re-embed when text genuinely
    *changes* to different non-empty content (e.g. observatory.ingest.
    fetch_ecfr_title48 refreshing a FAR/DFARS row that was previously ingested
    text-empty from the annual-CFR path, or a future amendment). Corrected:
    embedded resets to 0 whenever incoming text is non-empty AND differs from
    what's already stored -- so a real content change is picked up by the next
    embed_corpus.py run, while an empty/unchanged incoming text still can't
    clobber a good embedded=1 row.
    """
    cols = ["source", "collection", "citation", "title", "url",
            "published", "fetched_at", "text", "embedded", "meta_json"]
    update_cols = [c for c in cols if c not in ("source", "citation")]
    set_clause_parts = []
    for c in update_cols:
        if c == "text":
            set_clause_parts.append(
                "text = CASE WHEN excluded.text = '' OR excluded.text IS NULL "
                "THEN corpus_docs.text ELSE excluded.text END"
            )
        elif c == "embedded":
            set_clause_parts.append(
                "embedded = CASE "
                "WHEN excluded.text IS NOT NULL AND excluded.text != '' "
                "     AND excluded.text != corpus_docs.text THEN 0 "
                "WHEN corpus_docs.embedded = 1 THEN 1 "
                "ELSE excluded.embedded END"
            )
        else:
            set_clause_parts.append(f"{c}=excluded.{c}")
    set_clause = ", ".join(set_clause_parts)
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO corpus_docs ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(source, citation) DO UPDATE SET {set_clause}",
        [doc.get(c) for c in cols],
    )


def seed_entity(conn: sqlite3.Connection, entity: dict, seen_at: str) -> None:
    """Insert or refresh an entity_procurement row from principalities-index source data.

    Only the Census-sourced descriptive fields are touched here (name, state,
    government_type, county, population, website, last_seen). Verification
    fields (website_live, procurement_url, portal_platform, verify_status,
    ...) are left alone if the row already exists -- seeding must never
    clobber work the verifier job already did. first_seen/verify_status are
    set only on first insert.
    """
    cols = ["entity_id", "name", "state_code", "government_type", "county",
            "population", "website", "contact_email", "first_seen", "last_seen", "verify_status"]
    row = {
        "entity_id": entity["entity_id"],
        "name": entity.get("name"),
        "state_code": entity.get("state_code"),
        "government_type": entity.get("government_type"),
        "county": entity.get("county"),
        "population": entity.get("population"),
        "website": entity.get("website"),
        "contact_email": entity.get("contact_email"),
        "first_seen": seen_at,
        "last_seen": seen_at,
        "verify_status": "pending",
    }
    update_cols = ["name", "state_code", "government_type", "county",
                   "population", "website", "contact_email", "last_seen"]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO entity_procurement ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(entity_id) DO UPDATE SET {set_clause}",
        [row[c] for c in cols],
    )


def record_verification(conn: sqlite3.Connection, entity_id: str, result: dict, checked_at: str) -> None:
    """Write verifier-job results for one entity_procurement row. Row must already exist (seed_entity first)."""
    cols = ["website_live", "website_status_code", "procurement_url",
            "procurement_confidence", "portal_platform", "verify_status",
            "error_detail", "meta_json"]
    set_clause = ", ".join(f"{c} = ?" for c in cols)
    conn.execute(
        f"UPDATE entity_procurement SET {set_clause}, "
        f"verify_attempts = verify_attempts + 1, last_verified_at = ?, last_seen = ? "
        f"WHERE entity_id = ?",
        [result.get(c) for c in cols] + [checked_at, checked_at, entity_id],
    )


def pending_entities(conn: sqlite3.Connection, state_code: str | None = None,
                     limit: int | None = None) -> list[sqlite3.Row]:
    """Rows still needing a verifier pass (verify_status='pending'), oldest-seeded first."""
    where = "verify_status = 'pending'"
    params: list = []
    if state_code:
        where += " AND state_code = ?"
        params.append(state_code)
    sql = f"SELECT * FROM entity_procurement WHERE {where} ORDER BY first_seen"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql, params).fetchall()


def entity_procurement_stats(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) AS n FROM entity_procurement").fetchone()["n"]
    by_status = {
        r["verify_status"]: r["n"]
        for r in conn.execute(
            "SELECT verify_status, COUNT(*) AS n FROM entity_procurement GROUP BY verify_status"
        ).fetchall()
    }
    by_platform = {
        r["portal_platform"]: r["n"]
        for r in conn.execute(
            "SELECT portal_platform, COUNT(*) AS n FROM entity_procurement "
            "WHERE portal_platform IS NOT NULL GROUP BY portal_platform ORDER BY n DESC"
        ).fetchall()
    }
    return {"total": total, "by_status": by_status, "by_platform": by_platform}


def record_far_citations(conn: sqlite3.Connection, entity_id: str, citations: list[str]) -> None:
    """Store the compliance-scan result for one entity_procurement row (may be an empty list)."""
    conn.execute(
        "UPDATE entity_procurement SET far_citations_json = ? WHERE entity_id = ?",
        (_dumps(citations), entity_id),
    )


def unscanned_verified_entities(conn: sqlite3.Connection, limit: int | None = None) -> list[sqlite3.Row]:
    """Verified rows (real procurement_url) not yet compliance-scanned."""
    sql = ("SELECT * FROM entity_procurement WHERE verify_status = 'verified' "
           "AND far_citations_json IS NULL ORDER BY first_seen")
    if limit:
        sql += f" LIMIT {int(limit)}"
    return conn.execute(sql).fetchall()


def upsert_outreach_review(conn: sqlite3.Connection, row: dict, created_at: str) -> None:
    """Insert or refresh a review-queue row keyed on entity_id. Never overwrites a human decision
    (status stays approved/dismissed across re-runs unless the row is still pending_review)."""
    cols = ["entity_id", "reason", "priority_score", "contact_email",
            "draft_subject", "draft_body", "created_at"]
    row = {**row, "created_at": created_at}
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO outreach_review ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(entity_id) DO UPDATE SET "
        f"reason=excluded.reason, priority_score=excluded.priority_score, "
        f"contact_email=excluded.contact_email, draft_subject=excluded.draft_subject, "
        f"draft_body=excluded.draft_body "
        f"WHERE outreach_review.status = 'pending_review'",
        [row[c] for c in cols],
    )


def review_queue(conn: sqlite3.Connection, status: str = "pending_review",
                 limit: int = 100) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT o.*, e.name AS entity_name, e.state_code, e.county, e.government_type, "
        "e.population, e.website, e.procurement_url, e.portal_platform "
        "FROM outreach_review o JOIN entity_procurement e ON e.entity_id = o.entity_id "
        "WHERE o.status = ? ORDER BY o.priority_score DESC LIMIT ?",
        (status, limit),
    ).fetchall()


def decide_review(conn: sqlite3.Connection, review_id: int, status: str, decided_at: str) -> None:
    """status must be 'approved' or 'dismissed' -- both are human decisions, never automatic."""
    conn.execute(
        "UPDATE outreach_review SET status = ?, decided_at = ? WHERE id = ?",
        (status, decided_at, review_id),
    )


# ---------------------------------------------------------------------------
# Reads (used by the dashboard server)
# ---------------------------------------------------------------------------

def latest_run(conn: sqlite3.Connection) -> sqlite3.Row | None:
    return conn.execute("SELECT * FROM runs ORDER BY run_id DESC LIMIT 1").fetchone()


def recent_runs(conn: sqlite3.Connection, limit: int = 20) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM runs ORDER BY run_id DESC LIMIT ?", (limit,)
    ).fetchall()


def top_opportunities(conn: sqlite3.Connection, run_id: int | None = None,
                      limit: int = 25) -> list[sqlite3.Row]:
    if run_id is not None:
        return conn.execute(
            "SELECT * FROM opportunities WHERE last_run_id = ? "
            "ORDER BY win_probability DESC, vulnerability_score DESC LIMIT ?",
            (run_id, limit),
        ).fetchall()
    return conn.execute(
        "SELECT * FROM opportunities ORDER BY win_probability DESC, "
        "vulnerability_score DESC LIMIT ?", (limit,)
    ).fetchall()


def high_vuln_opportunities(conn: sqlite3.Connection, run_id: int,
                            threshold: int = 70, limit: int = 15) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM opportunities WHERE last_run_id = ? AND vulnerability_score >= ? "
        "ORDER BY vulnerability_score DESC LIMIT ?",
        (run_id, threshold, limit),
    ).fetchall()


def corpus_stats(conn: sqlite3.Connection) -> dict:
    total = conn.execute("SELECT COUNT(*) AS n FROM corpus_docs").fetchone()["n"]
    embedded = conn.execute(
        "SELECT COUNT(*) AS n FROM corpus_docs WHERE embedded = 1"
    ).fetchone()["n"]
    by_source = {
        r["source"]: r["n"]
        for r in conn.execute(
            "SELECT source, COUNT(*) AS n FROM corpus_docs GROUP BY source ORDER BY n DESC"
        ).fetchall()
    }
    return {"total": total, "embedded": embedded, "by_source": by_source}


def counts(conn: sqlite3.Connection) -> dict:
    return {
        "runs": conn.execute("SELECT COUNT(*) AS n FROM runs").fetchone()["n"],
        "opportunities": conn.execute("SELECT COUNT(*) AS n FROM opportunities").fetchone()["n"],
        "corpus_docs": conn.execute("SELECT COUNT(*) AS n FROM corpus_docs").fetchone()["n"],
        "entity_procurement": conn.execute("SELECT COUNT(*) AS n FROM entity_procurement").fetchone()["n"],
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
