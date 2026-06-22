"""Full-text fill (arc #4, phase 2) — populate corpus_docs.text from primary sources.

The ingest pass (ingest.py) stores rows cheaply with text="" and fills the title,
citation, and primary-source URL. This pass pulls the actual document body so the
antibody ORACLE has real content to embed/retrieve, not just titles.

Slow and deliberate on purpose — govinfo is a public API and we do not want to
trip a rate limit:
  - a per-request delay (default 1.0s),
  - honors the X-RateLimit-Remaining header (backs off hard when it runs low),
  - naturally resumable: only fills rows whose text is still empty, so a killed
    run just re-runs and skips what's already done.

Source routing (per docs/GOVINFO_RESEARCH_2026-06-14.md):
  far / dfars -> govinfo granule htm:  /packages/{pkg}/granules/{granuleId}/htm
  gao         -> govinfo package htm:  /packages/{packageId}/htm
  eo          -> already carries the Federal Register abstract from ingest;
                 full-text upgrade is a later refinement (skipped here).

Usage (repo root, venv python):
    python -m observatory.fulltext --source far --limit 3      # test batch
    python -m observatory.fulltext                             # fill all empty rows
"""

from __future__ import annotations

import argparse
import json
import time

import requests

from . import db
from .ingest import GOVINFO_BASE, GOVINFO_KEY, _UA

# Quota is generous (36000/hr) -- the real risk is a burst/connection penalty that
# returns 429 even at low rate. So: reuse one connection, and on 429 back off and
# retry the SAME request rather than skipping it.
_RL_FLOOR = 200          # secondary guard: ease off when the hourly window thins
_RL_COOLDOWN = 30.0
_MAX_429_RETRIES = 4     # connection reuse prevents the burst-trip; keep backoff bounded

_session = requests.Session()
_session.headers.update(_UA)


def _fetch_text(url: str, timeout: int = 60) -> tuple[str, int | None]:
    """GET a URL with 429-aware retry/backoff. Returns (body_text, rl_remaining)."""
    backoff = 15
    for attempt in range(1, _MAX_429_RETRIES + 1):
        r = _session.get(url, timeout=timeout)
        if r.status_code == 429:
            wait = int(r.headers.get("Retry-After") or backoff)
            print(f"    429 throttle -> waiting {wait}s (retry {attempt}/{_MAX_429_RETRIES})")
            time.sleep(wait)
            backoff = min(backoff * 2, 60)
            continue
        r.raise_for_status()
        rem = r.headers.get("X-RateLimit-Remaining")
        return r.text, (int(rem) if rem and rem.isdigit() else None)
    raise RuntimeError(f"429 after {_MAX_429_RETRIES} retries: {url.split('?')[0]}")


def _strip_html(html: str) -> str:
    """HTML -> clean-ish plain text for embedding. Uses bs4 if present."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style"]):
            tag.decompose()
        text = soup.get_text(separator=" ")
    except Exception:
        # crude fallback: drop tags
        import re
        text = re.sub(r"<[^>]+>", " ", html)
    return " ".join(text.split())


def _url_for(row) -> str | None:
    """Build the full-text endpoint URL for a corpus_docs row by source."""
    source = row["source"]
    if source in ("far", "dfars"):
        meta = json.loads(row["meta_json"] or "{}")
        pkg, gid = meta.get("package"), meta.get("granuleId")
        if not (pkg and gid):
            return None
        # CFR granules expose xml/pdf (no htm). xml -> text strips cleanly.
        return f"{GOVINFO_BASE}/packages/{pkg}/granules/{gid}/xml?api_key={GOVINFO_KEY}"
    if source == "gao":
        # GAO packages expose txt (no htm/xml). Plain text -> _strip_html is a no-op.
        return f"{GOVINFO_BASE}/packages/{row['citation']}/txt?api_key={GOVINFO_KEY}"
    return None  # eo handled via its ingest abstract


def fill(source: str | None = None, limit: int | None = None,
         delay: float = 1.0) -> dict:
    """Fill empty corpus_docs.text rows from primary sources. Returns a summary."""
    db.init_db()
    where = "(text IS NULL OR text = '')"
    params: list = []
    if source:
        where += " AND source = ?"
        params.append(source)
    sql = f"SELECT doc_id, source, citation, url, meta_json, text FROM corpus_docs WHERE {where} ORDER BY doc_id"
    if limit:
        sql += f" LIMIT {int(limit)}"

    filled = skipped = failed = 0
    with db.session() as conn:
        rows = conn.execute(sql, params).fetchall()
        total = len(rows)
        print(f"[*] {total} rows need text" + (f" (source={source})" if source else ""))
        for i, row in enumerate(rows, 1):
            url = _url_for(row)
            if not url:
                skipped += 1
                continue
            try:
                body, remaining = _fetch_text(url)
                text = _strip_html(body)
                if not text:
                    failed += 1
                else:
                    conn.execute(
                        "UPDATE corpus_docs SET text = ?, fetched_at = ? WHERE doc_id = ?",
                        (text, _now(), row["doc_id"]),
                    )
                    conn.commit()  # commit per row -> killable/resumable
                    filled += 1
                if i % 25 == 0 or i == total:
                    print(f"    {i}/{total}  filled={filled} failed={failed} "
                          f"skipped={skipped}  rl_remaining={remaining}")
                # deliberate pacing + hard backoff near the rate-limit floor
                if remaining is not None and remaining < _RL_FLOOR:
                    print(f"    rate-limit low ({remaining}); cooling down {_RL_COOLDOWN}s")
                    time.sleep(_RL_COOLDOWN)
                else:
                    time.sleep(delay)
            except Exception as e:
                failed += 1
                print(f"    [fail] doc_id={row['doc_id']} {row['citation']}: {e}")
                time.sleep(delay)

    summary = {"total": total, "filled": filled, "failed": failed, "skipped": skipped}
    print(f"[*] done: {summary}")
    return summary


def _now() -> str:
    from datetime import datetime
    return datetime.now().isoformat()


def main() -> None:
    ap = argparse.ArgumentParser(description="Fill corpus_docs.text from primary sources (deliberate, rate-limited).")
    ap.add_argument("--source", default=None, help="far | dfars | gao (default: all empty rows)")
    ap.add_argument("--limit", type=int, default=None, help="cap rows this run (use a small value to test)")
    ap.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1.0)")
    args = ap.parse_args()
    fill(args.source, args.limit, args.delay)


if __name__ == "__main__":
    main()
