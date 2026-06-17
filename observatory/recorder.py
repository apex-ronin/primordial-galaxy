"""Run recorder — ingests a completed scanner run into the Observatory DB.

Called once from main.py at the end of a run (PHASE 3). Designed to be
*non-fatal*: main.py wraps the call so any exception here is logged and
swallowed. Observability must never take down acquisition.

What it captures, per run:
  - timing (started/finished/duration) and a derived status
  - per-source counts (from the raw module results)
  - fit distribution (High/Medium/Low) and totals
  - which LLM tier actually served, parsed from each record's analysis_method
    ("LLM Dual-Track [venice (llama-3.3-70b)]" -> tier "venice"), and whether
    the sovereign-local tier served anything at all
  - orchestrator errors and the log path

Then upserts every scored opportunity (deduped by link, first_seen preserved).
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import datetime

from . import db

_BRACKET = re.compile(r"\[(.+)\]")


def _provider_from_method(analysis_method: str | None) -> str | None:
    """'LLM Dual-Track [venice (llama-3.3-70b)]' -> 'venice (llama-3.3-70b)'.

    Returns None for keyword fallback / missing methods.
    """
    if not analysis_method:
        return None
    m = _BRACKET.search(analysis_method)
    if not m:
        return None
    inner = m.group(1).strip()
    if inner.lower() in ("unknown", ""):
        return None
    return inner


def _tier_name(provider: str | None) -> str | None:
    """'venice (llama-3.3-70b)' -> 'venice'."""
    if not provider:
        return None
    return provider.split("(")[0].strip().lower()


def _git_commit() -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        return out.stdout.strip() or None
    except Exception:
        return None


def build_run_record(
    scored_opportunities: list[dict],
    source_counts: dict[str, int],
    errors: list[dict],
    started_at: str,
    finished_at: str,
    log_path: str | None,
) -> dict:
    """Assemble the `runs` row dict from raw run artifacts (pure function)."""
    fits = Counter((o.get("fit_label") or "?") for o in scored_opportunities)

    providers = [_provider_from_method(o.get("analysis_method")) for o in scored_opportunities]
    tier_breakdown = Counter(p for p in providers if p)
    tier_names = Counter(_tier_name(p) for p in providers if p)
    tier_served = tier_names.most_common(1)[0][0] if tier_names else None
    local_used = any((t == "local") for t in tier_names)

    total_found = sum(source_counts.values()) if source_counts else len(scored_opportunities)
    total_scored = len(scored_opportunities)

    # Status: failed if nothing scored; partial if any module errored or any
    # source returned zero; otherwise success.
    if total_scored == 0:
        status = "failed"
    elif errors or any(v == 0 for v in (source_counts or {}).values()):
        status = "partial"
    else:
        status = "success"

    try:
        start_dt = datetime.fromisoformat(started_at)
        end_dt = datetime.fromisoformat(finished_at)
        duration = (end_dt - start_dt).total_seconds()
    except Exception:
        duration = None

    return {
        "started_at": started_at,
        "finished_at": finished_at,
        "duration_sec": duration,
        "status": status,
        "total_found": total_found,
        "total_scored": total_scored,
        "high_count": fits.get("High", 0),
        "medium_count": fits.get("Medium", 0),
        "low_count": fits.get("Low", 0),
        "sources_json": json.dumps(source_counts or {}),
        "errors_json": json.dumps(errors or []),
        "tier_served": tier_served,
        "tier_breakdown_json": json.dumps(dict(tier_breakdown)),
        "local_tier_used": int(local_used),
        "log_path": log_path,
        "git_commit": _git_commit(),
    }


def record_run(
    scored_opportunities: list[dict],
    source_counts: dict[str, int],
    errors: list[dict],
    started_at: str,
    finished_at: str | None = None,
    log_path: str | None = None,
) -> int:
    """Persist a completed run + its opportunities. Returns the new run_id."""
    finished_at = finished_at or datetime.now().isoformat()
    db.init_db()
    run = build_run_record(
        scored_opportunities, source_counts, errors,
        started_at, finished_at, log_path,
    )
    with db.session() as conn:
        run_id = db.insert_run(conn, run)
        seen_at = finished_at
        for opp in scored_opportunities:
            if not opp.get("link"):
                continue  # link is the dedup key; skip records without one
            db.upsert_opportunity(conn, opp, run_id, seen_at)
    return run_id
