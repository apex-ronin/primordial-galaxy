"""SQLite spine for the Observatory.

One file, no server, no cloud. Lives at <repo>/data/primordial.db (gitignored as
runtime data — it is fully regenerable from opportunities.json + scan logs).

Three tables:
  runs          — one row per scanner run: when, how long, status, per-source
                  counts, which LLM tier actually served, errors, log path.
  opportunities — deduped by link; carries the full scored record plus
                  first_seen / last_seen so the dashboard can show history/trend.
  corpus_docs   — the knowledge store the ORACLE agents draw on (govinfo, FAR,
                  DFARS, EOs, GAO/IG fraud cases). Deduped by (source, citation).
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

CREATE INDEX IF NOT EXISTS idx_opp_win   ON opportunities(win_probability DESC);
CREATE INDEX IF NOT EXISTS idx_opp_run   ON opportunities(last_run_id);
CREATE INDEX IF NOT EXISTS idx_runs_time ON runs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_corpus_src ON corpus_docs(source);
"""


def _ensure_parent() -> None:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)


def connect(db_path: str | None = None) -> sqlite3.Connection:
    """Open a connection with row access by name and FK enforcement on."""
    _ensure_parent()
    conn = sqlite3.connect(db_path or DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: str | None = None) -> None:
    """Create tables/indexes if absent. Idempotent."""
    with connect(db_path) as conn:
        conn.executescript(SCHEMA)
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
    """
    cols = ["source", "collection", "citation", "title", "url",
            "published", "fetched_at", "text", "embedded", "meta_json"]
    update_cols = [c for c in cols if c not in ("source", "citation")]
    set_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols)
    placeholders = ", ".join("?" for _ in cols)
    conn.execute(
        f"INSERT INTO corpus_docs ({', '.join(cols)}) VALUES ({placeholders}) "
        f"ON CONFLICT(source, citation) DO UPDATE SET {set_clause}",
        [doc.get(c) for c in cols],
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
    }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _dumps(obj) -> str:
    import json
    return json.dumps(obj, ensure_ascii=False)
