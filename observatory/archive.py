"""Opportunity document archive (Jay's directive, 2026-09-07).

Permanent, full-text storage of every RFP/grant opportunity ever fetched --
regardless of its score -- kept for a retention window, so raw content
survives even after a posting is taken down from the source site. Storage is
file-per-link on disk (data/opportunity_archive/, gitignored -- these can be
multi-page documents, SQLite is not the right place for the bytes); the DB
row is metadata + path only.

This module only WRITES the archive. The decision to skip re-fetching/
re-scoring an already-seen link lives in execution/main.py, keyed off
observatory.db.get_opportunity_by_link() -- the existing `opportunities`
table already accumulates one row per link across every run, so that's the
"have we seen this" check. This module is purely the raw-text side of it.

Usage: called from execution/hunter_brain.py right after it fetches full
document text for a genuinely new opportunity (main.py only calls
analyze_opportunity() for links not already in `opportunities`).
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

from . import db

# Defensive, not currently load-bearing: main.py already calls load_dotenv()
# before this module gets imported (lazily, inside hunter_brain.analyze_
# opportunity), so ARCHIVE_DIR/RETENTION_DAYS below already see .env today.
# But observatory/embed_corpus.py just proved that assumption is exactly the
# kind of thing that silently breaks the moment this gets imported from a
# different entry point -- calling it here directly instead of relying on a
# caller having already done it.
load_dotenv()

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE_DIR = Path(os.environ.get(
    "OPPORTUNITY_ARCHIVE_DIR", os.path.join(_REPO_ROOT, "data", "opportunity_archive")
))
# Jay: "house physical copies ... maybe even after for a couple years" -- default
# retention window; metadata only for now (retention_until is tracked, nothing
# auto-deletes yet -- a real pruning job is a separate, later task).
RETENTION_DAYS = int(os.environ.get("ARCHIVE_RETENTION_DAYS", "730"))


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _path_for(link: str) -> Path:
    # Filename keyed on the link's own hash, not the content hash, so a
    # re-fetch of the same link overwrites its own file rather than orphaning
    # the old one under a changed name.
    h = hashlib.sha256(link.encode("utf-8", errors="ignore")).hexdigest()
    return ARCHIVE_DIR / f"{h}.txt"


def archive_document(link: str, raw_text: str, seen_at: str | None = None) -> dict:
    """Persist raw_text to disk and upsert its opportunity_documents row.

    Idempotent and cheap to call repeatedly for the same link+content (the
    on-disk write only happens when content_hash actually changes).
    Returns {"path": str, "content_hash": str, "changed": bool}.
    """
    if not link:
        return {"path": None, "content_hash": None, "changed": False}

    seen_at = seen_at or datetime.now(timezone.utc).isoformat()
    raw_text = raw_text or ""
    content_hash = _hash(raw_text)

    db.init_db()
    with db.session() as conn:
        existing = conn.execute(
            "SELECT content_hash, first_seen FROM opportunity_documents WHERE link = ?", (link,)
        ).fetchone()

    changed = existing is None or existing["content_hash"] != content_hash
    path = _path_for(link)

    if changed:
        ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(raw_text, encoding="utf-8")

    first_seen = existing["first_seen"] if existing else seen_at
    retention_until = (
        datetime.now(timezone.utc) + timedelta(days=RETENTION_DAYS)
    ).isoformat()

    with db.session() as conn:
        db.upsert_opportunity_document(conn, {
            "link": link,
            "content_hash": content_hash,
            "raw_text_path": str(path),
            "char_count": len(raw_text),
            "first_seen": first_seen,
            "last_seen": seen_at,
            "retention_until": retention_until,
        })

    return {"path": str(path), "content_hash": content_hash, "changed": changed}
