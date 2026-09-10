"""Direct-source procurement page watcher (Jay's directive, 2026-09-10).

Third-party aggregators (SAM.gov, grants.gov, CSDA) necessarily lag the
primary source -- an agency posts on its own site before any aggregator
picks it up. This module watches the entity_procurement URLs directly:
fetch once, hash the content, and on the next run compare hashes. A changed
hash means "this agency's procurement page moved" -- worth a human/LLM
look, without re-parsing 5,601 pages of arbitrary HTML every single day.

This is deliberately NOT one crawler hitting one target repeatedly -- these
are 5,601+ *different* government domains, so hitting each one once is not
a DoS pattern the way hammering one shared platform (OpenGov, BidNet, etc.
-- see STATE.md 2026-09-09/10) would be. The actual risk here is the
opposite: looking like a coordinated sweep if every request fires at once.
Mitigated by:
  - a real, honest User-Agent (never disguise what this is)
  - robots.txt checked and respected per domain, every run, not cached
    across runs (a small agency's site could change its policy any time)
  - a modest global concurrency cap (not per-domain -- there IS no
    per-domain repeat within a single run)
  - random jitter between request submissions so the whole batch isn't a
    tight burst
  - a circuit breaker: a domain that errors/times out repeatedly gets
    skipped on subsequent runs rather than retried forever

Extraction (deciding whether a *change* is actually a new RFP posting, and
pulling out title/deadline/description) is deliberately NOT this module's
job -- 5,308 different one-off government sites means 5,308 different HTML
shapes, not something worth hand-parsing. That's Phase B: feed a changed
page's text through the local LLM cascade (same pattern as everywhere else
in this pipeline) rather than writing per-site parsers. Not built yet.

Usage:
    python -m observatory.procurement_watch pilot --limit 100
    python -m observatory.procurement_watch pilot --limit 100 --dry-run
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import random
import time
import urllib.robotparser
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup, Comment
from dotenv import load_dotenv

from . import db

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USER_AGENT = "ApexRoninBot/1.0 (+contact: jsn.nlsn@gmail.com; government-procurement-research)"
REQUEST_TIMEOUT = 15  # seconds -- don't hang on a slow small-town server
ROBOTS_TIMEOUT = 10
GLOBAL_CONCURRENCY = 6  # in-flight requests at once, across all domains
JITTER_MIN_SEC = 0.5    # spacing between request *submissions*, not per-domain crawl-delay
JITTER_MAX_SEC = 2.5
CIRCUIT_BREAKER_THRESHOLD = 5  # consecutive errors before a domain is skipped on future runs


def _visible_text(html: str) -> str:
    """Strip a page down to human-visible text before hashing.

    Pilot run (2026-09-10) found the naive raw-body hash flagged 39/100 pages
    as "changed" within a 40-second gap -- almost all of it ASP.NET's
    __VIEWSTATE hidden field, which is regenerated fresh on every page load
    and carries zero content signal. Rather than enumerate every framework's
    version of that trap (WordPress nonces, CSRF tokens, session-embedded
    URLs, ad-rotation scripts...) across 5,308 different government sites,
    strip to what a human reader would actually see: no scripts, styles,
    comments, or hidden form fields, whitespace collapsed.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(attrs={"type": "hidden"}):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    text = soup.get_text(separator=" ")
    return " ".join(text.split())


def _hash(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()


def _domain(url: str) -> str:
    return urlparse(url).netloc


def _check_robots(url: str) -> bool | None:
    """True/False if robots.txt resolved and gave a clear answer; None if the
    fetch itself failed (treated as skip, not allow -- fail closed, not open)."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = urllib.robotparser.RobotFileParser()
    rp.set_url(robots_url)
    try:
        resp = requests.get(robots_url, headers={"User-Agent": USER_AGENT}, timeout=ROBOTS_TIMEOUT)
        if resp.status_code >= 400:
            # No robots.txt (404) is a clear "no restrictions stated" -- allow.
            # Any other error (5xx, etc.) is inconclusive -- fail closed.
            return resp.status_code == 404
        rp.parse(resp.text.splitlines())
        return rp.can_fetch(USER_AGENT, url)
    except Exception as e:
        logger.warning("robots.txt check failed for %s: %s", robots_url, e)
        return None


def check_one(entity_id: str, url: str) -> dict:
    """Robots-check + fetch + hash one URL. Never raises -- errors are captured in the result dict."""
    domain = _domain(url)
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "entity_id": entity_id, "url": url, "domain": domain,
        "content_hash": None, "robots_allowed": None, "last_status_code": None,
        "last_checked": now, "last_changed": None, "last_error": None,
    }

    allowed = _check_robots(url)
    result["robots_allowed"] = 1 if allowed is True else (0 if allowed is False else None)
    if allowed is not True:
        result["last_error"] = "robots.txt disallows or could not be verified"
        return result

    try:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT)
        result["last_status_code"] = resp.status_code
        if resp.status_code >= 400:
            result["last_error"] = f"HTTP {resp.status_code}"
            return result
        result["content_hash"] = _hash(_visible_text(resp.text))
    except Exception as e:
        result["last_error"] = str(e)

    return result


def pilot(limit: int = 100, dry_run: bool = False) -> dict:
    """Run the watcher against a sample of `limit` verified entity_procurement rows.

    dry_run=True does the robots.txt + fetch pass but does not write to the DB --
    for a first look at what a batch would actually do before trusting it with writes.
    """
    db.init_db()
    with db.session() as conn:
        rows = conn.execute(
            "SELECT entity_id, name, procurement_url FROM entity_procurement "
            "WHERE verify_status = 'verified' AND procurement_url IS NOT NULL "
            "ORDER BY entity_id LIMIT ?",
            (limit,),
        ).fetchall()
        # Circuit breaker: skip entities already backed off from a prior run.
        breakered = {
            r["entity_id"]
            for r in conn.execute(
                "SELECT entity_id FROM procurement_watch WHERE consecutive_errors >= ?",
                (CIRCUIT_BREAKER_THRESHOLD,),
            ).fetchall()
        }

    targets = [(r["entity_id"], r["name"], r["procurement_url"]) for r in rows if r["entity_id"] not in breakered]
    skipped_breaker = len(rows) - len(targets)
    logger.info("Pilot: %d candidates, %d skipped (circuit breaker), %d to check",
                len(rows), skipped_breaker, len(targets))

    results = []
    with ThreadPoolExecutor(max_workers=GLOBAL_CONCURRENCY) as pool:
        futures = {}
        for entity_id, name, url in targets:
            time.sleep(random.uniform(JITTER_MIN_SEC, JITTER_MAX_SEC) / GLOBAL_CONCURRENCY)
            futures[pool.submit(check_one, entity_id, url)] = name
        for i, fut in enumerate(as_completed(futures), 1):
            name = futures[fut]
            r = fut.result()
            results.append(r)
            tag = "OK" if r["content_hash"] else ("BLOCKED" if r["robots_allowed"] == 0 else "ERROR")
            logger.info("[%d/%d] %-9s %-30s %s", i, len(targets), tag, name[:30], r.get("last_error") or "")

    blocked = sum(1 for r in results if r["robots_allowed"] == 0)
    robots_unknown = sum(1 for r in results if r["robots_allowed"] is None)
    fetched = sum(1 for r in results if r["content_hash"])
    changed = 0
    errored = sum(1 for r in results if r["last_error"] and r["content_hash"] is None and r["robots_allowed"] != 0)

    if not dry_run:
        with db.session() as conn:
            for r in results:
                prior = db.get_procurement_watch(conn, r["entity_id"])
                consecutive_errors = 0
                if r["content_hash"]:
                    is_change = bool(prior and prior.get("content_hash") and prior["content_hash"] != r["content_hash"])
                    if is_change:
                        changed += 1
                        r["last_changed"] = r["last_checked"]
                    elif prior:
                        r["last_changed"] = prior.get("last_changed")
                else:
                    consecutive_errors = (prior.get("consecutive_errors", 0) if prior else 0) + 1

                db.upsert_procurement_watch(conn, {
                    **r,
                    "consecutive_errors": consecutive_errors,
                    "check_count": (prior.get("check_count", 0) if prior else 0) + 1,
                    "change_count": (prior.get("change_count", 0) if prior else 0) + (1 if r.get("last_changed") == r["last_checked"] else 0),
                    "first_checked": prior.get("first_checked") if prior else r["last_checked"],
                })

    summary = {
        "candidates": len(rows),
        "skipped_breaker": skipped_breaker,
        "checked": len(targets),
        "fetched_ok": fetched,
        "blocked_by_robots": blocked,
        "robots_unknown": robots_unknown,
        "errored": errored,
        "changed_since_last_run": changed,
        "dry_run": dry_run,
    }
    logger.info("Pilot summary: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Direct-source procurement page watcher.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_pilot = sub.add_parser("pilot", help="Run against a small sample before scaling up.")
    p_pilot.add_argument("--limit", type=int, default=100)
    p_pilot.add_argument("--dry-run", action="store_true", help="Fetch + check robots.txt but don't write to the DB.")

    args = parser.parse_args()
    if args.command == "pilot":
        pilot(limit=args.limit, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
