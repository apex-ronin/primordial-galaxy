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
LOCAL_EXTRACT_RETRIES = 3      # retries of the SAME local call on transient failure -- never a
                                # different provider. Jay's directive, 2026-09-10: no silent
                                # Venice fallback for this module until local is fully trusted.
RETRY_BACKOFF_SEC = 5
FLAG_EXTRACTION_COUNT_THRESHOLD = 10  # more than this from one page is treated as likely
                                       # over-extraction (see libertycountyfl.org, 2026-09-10)
                                       # -- held for review instead of auto-ingested

# Regional split for cron scheduling (Jay's directive, 2026-09-13): run each US
# timezone's entities during ITS OWN 1-4am local window, not one global time that's
# off-peak for some states and mid-morning for others. This box's cron daemon runs
# a single system timezone (UTC) with no per-job TZ support (confirmed via
# `man 5 crontab` -- TZ set in a crontab only affects the command's environment,
# not when it fires), so each region gets its own cron entry at a manually
# UTC-converted time. That conversion drifts by 1hr at each DST transition --
# see run_procurement_watch.sh's header for the current offsets in use.
#
# APPROXIMATE by design, not survey-grade: bucketed by each state's MAJORITY zone,
# folded down to Jay's requested 3 buckets (Mountain states folded into "central",
# AK/HI folded into "pacific" as the nearest available bucket). States that
# genuinely split zones (TX, TN, FL panhandle, IN, KY, ND/SD/NE/KS western edges,
# ID, plus AZ not observing DST at all) are bucketed by population-weighted
# majority, not perfectly per-entity. Good enough for scheduling; if this list
# needs to become per-entity-precise later, that's a real (bigger) project, not
# a quick edit here.
REGION_STATES = {
    "eastern": {
        "CT", "DE", "DC", "FL", "GA", "IN", "KY", "ME", "MD", "MA", "MI", "NH",
        "NJ", "NY", "NC", "OH", "PA", "RI", "SC", "VT", "VA", "WV",
    },
    "central": {
        "AL", "AR", "IA", "IL", "KS", "LA", "MN", "MS", "MO", "NE", "ND", "OK",
        "SD", "TN", "TX", "WI", "CO", "MT", "NM", "UT", "WY", "AZ", "ID",
    },
    "pacific": {
        "CA", "NV", "OR", "WA", "AK", "HI",
    },
}


class ExtractionError(Exception):
    """Local extraction failed after retries. Deliberately NOT caught inside
    run_extraction() -- per Jay's directive, this halts the whole batch rather
    than silently skipping the page or falling back to a cloud provider."""


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

    Preserves line breaks between block-level elements -- a flat single-line
    join (the original version of this function) destroys the relationship
    between a section heading and the items under it. Verified live 2026-09-10
    (libertycountyfl.org): a page with an explicit "CLOSED BIDS" heading had
    its 7 closed items extracted as open, while the 2 genuinely-open items
    under a separate "NOTICE TO RECEIVE SEALED BIDS" heading were missed
    entirely -- a complete inversion. With everything mashed into one line,
    the model has no signal for which items a heading actually governs.
    """
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()
    for tag in soup.find_all(attrs={"type": "hidden"}):
        tag.decompose()
    for comment in soup.find_all(string=lambda t: isinstance(t, Comment)):
        comment.extract()
    text = soup.get_text(separator="\n")
    lines = [" ".join(line.split()) for line in text.splitlines()]
    lines = [line for line in lines if line]  # drop now-empty lines, but keep line boundaries elsewhere
    return "\n".join(lines)


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


def check_one(entity_id: str, url: str, keep_text: bool = False) -> dict:
    """Robots-check + fetch + hash one URL. Never raises -- errors are captured in the result dict.

    keep_text=True also returns the extracted visible_text in-memory (not persisted --
    procurement_watch only stores the hash) for a caller doing extraction in the same
    pass, so a page is never fetched twice in one run.
    """
    domain = _domain(url)
    now = datetime.now(timezone.utc).isoformat()
    result = {
        "entity_id": entity_id, "url": url, "domain": domain,
        "content_hash": None, "robots_allowed": None, "last_status_code": None,
        "last_checked": now, "last_changed": None, "last_error": None, "visible_text": None,
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
        text = _visible_text(resp.text)
        result["content_hash"] = _hash(text)
        if keep_text:
            result["visible_text"] = text
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


MAX_EXTRACT_CHARS = 15_000  # visible-text budget for the extraction prompt

_EXTRACT_SYSTEM = "You are a JSON-only API. Output strictly valid JSON. No markdown, no code blocks, no backticks."

_EXTRACT_PROMPT = """You are reviewing a government agency's procurement/bids web page. Your job is to find
solicitations that are STILL ACCEPTING SUBMISSIONS TODAY ({today}). Most government bid pages are
mostly historical archive -- old, already-decided procurements kept online for the public record.
Treating archive entries as currently-open is a serious error you must avoid.

The page text is one item per line, in the same top-to-bottom order as the real page. HEADING SCOPE
RULE: a section heading governs every item listed AFTER it, up until the NEXT heading appears --
never the items before it. If you see "Notice to Receive Sealed Bids" followed by two titles, then
"Closed Bids" followed by ten more titles, the first two belong to "Notice to Receive Sealed Bids"
(open) and the ten after belong to "Closed Bids" (closed) -- not the reverse, and not all lumped
together. Pages are full of unrelated navigation-menu and footer text (site menus, department links,
office hours, social links) -- ignore all of that; it is not a heading and governs nothing.

Work in two passes:

PASS 1 -- list every distinct solicitation (RFP/RFQ/ITB/bid) named on the page, and for each one note
which heading (per the scope rule above) governs it, plus whatever other closure evidence appears
near it.

PASS 2 -- from that list, KEEP ONLY items where NONE of the following closure evidence is present:
  - "Recommendation of Award", "Notice of Award", "Award", "Awarded", "Bid Tabulation"
  - "Selection Committee" meeting minutes/results, evaluation committee scoring, ranked proposals
  - "Reject", "Rejected", "Cancelled"
  - Grouped under a section heading that itself says something like "Closed Bids", "Awarded",
    "Past Opportunities", "Archive", or similar
  - A stated deadline/closing date that is BEFORE {today}
  - The item is dated (by its own number, e.g. "RFP 2021-01", or by context) from a prior year with
    no indication it's still active

An item grouped under a section heading that itself says something like "Notice to Receive Sealed
Bids", "Open Bids", "Current Opportunities", "Active Solicitations", or similar IS positive evidence
of being open -- keep it even if no explicit deadline is stated near it. The heading itself is
real evidence; don't discard it for lack of a separate date.

If you genuinely cannot find evidence either way for an item -- no governing heading, no dates, no
closure language -- DEFAULT TO EXCLUDING IT. But an item positively labeled open by its own section
heading is not that ambiguous case.

Do not invent a solicitation if the page shows none genuinely open -- an empty list is a correct and
expected answer for most pages, not a failure.

ADDENDA ARE NOT SEPARATE OPPORTUNITIES. "Addendum No. 1", "Addendum #2", corrected bid forms,
site-visit notices, and similar follow-up documents all belong to their PARENT solicitation --
never list them as their own entry. If the same underlying solicitation (same bid/RFP number or
same title) appears more than once on the page (e.g. listed under multiple category headings),
list it only ONCE in your output.

Return ONLY valid JSON -- a list, no markdown, no backticks, no wrapper object, just the array itself:
[
  {{
    "title": "the bid/RFP title exactly as shown (bid number if present)",
    "description": "1-2 sentence summary of what's being solicited, from the page text",
    "deadline": "the submission deadline as shown, or null if not stated",
    "detail_url": "a specific URL for this item if one appears in the page text, or null"
  }}
]

Page URL: {url}

Page text:
{text}
"""


def extract_rfps(page_url: str, visible_text: str) -> list[dict]:
    """LLM call: does this page list any open bids/RFPs? Extract each one found.

    Returns [] on no listings found or truncated input. Raises ExtractionError
    on any LLM failure -- Jay's explicit directive (2026-09-10): no silent
    fallback to Venice for this module. local failing is a full stop, not a
    quiet cloud success. See LOCAL_EXTRACT_RETRIES/RETRY_BACKOFF_SEC for the
    retry policy on transient local failures (a live 404 was reproduced twice
    against baycountyfl-scale prompts, root-caused to Ollama contention from
    a concurrent manual test hitting the same CPU-bound instance -- retrying
    the SAME local call, never falling through to a different provider, is
    the fix).
    """
    if not visible_text or len(visible_text) < 50:
        return []

    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "execution"))
    import llm_client  # noqa: E402  -- calling _try_local directly, not complete(), so a
                        # local failure can never silently cascade to venice/anthropic.

    text = visible_text[:MAX_EXTRACT_CHARS]
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = _EXTRACT_PROMPT.format(url=page_url, text=text, today=today)

    raw = None
    last_err = None
    for attempt in range(1, LOCAL_EXTRACT_RETRIES + 1):
        try:
            raw = llm_client._try_local(prompt, _EXTRACT_SYSTEM, "fast", json_mode=True)
            if raw:
                break
            last_err = "local returned no content"
        except Exception as e:
            last_err = str(e)
        if attempt < LOCAL_EXTRACT_RETRIES:
            logger.warning("Local extraction attempt %d/%d failed for %s: %s -- retrying in %ds",
                            attempt, LOCAL_EXTRACT_RETRIES, page_url, last_err, RETRY_BACKOFF_SEC)
            time.sleep(RETRY_BACKOFF_SEC)

    if not raw:
        raise ExtractionError(f"Local extraction failed for {page_url} after {LOCAL_EXTRACT_RETRIES} attempts: {last_err}")

    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.split("```")[0]
    import json
    result = json.loads(raw.strip())
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        # Local model routinely wraps the array in a named key
        # ({"bid_postings": [...]}) despite the prompt asking for a bare
        # list -- verified live 2026-09-10 (baycountyfl.gov: 4 real bids
        # correctly extracted, then silently dropped by an earlier
        # strict-list-only parse). Take the first list-valued key rather
        # than assume one specific name across every model response.
        for v in result.values():
            if isinstance(v, list):
                return v
    return []


def _synthetic_link(page_url: str, title: str, detail_url: str | None) -> str:
    """A stable dedup key for an RFP that has no unique URL of its own.

    Prefers a real detail_url if the LLM found one on the page. Otherwise anchors
    to the page URL + a hash of the title, so the SAME posting on a future run
    (unchanged title) dedupes correctly via the normal opportunities.link key --
    only a genuinely new/renamed title produces a new link.
    """
    if detail_url:
        return detail_url
    title_hash = hashlib.sha256((title or "").encode("utf-8", errors="ignore")).hexdigest()[:16]
    return f"{page_url}#{title_hash}"


def run_extraction(limit: int = 100, dry_run: bool = False, region: str | None = None) -> dict:
    """Phase B: fetch + hash + extract + ingest, for every site in the sample.

    Extraction only runs on pages that are new or changed since the last check
    (see the new/changed filter below) -- unchanged pages already have their
    opportunities recorded, so re-extracting them would just cost an LLM call
    for no new information. Whatever's found is scored and saved through the
    exact same path a SAM.gov/grants.gov/CSDA result takes
    (hunter_brain.analyze_opportunity -> observatory.recorder.record_run), so
    it shows up in opportunities/the dashboard/Phase 3.5 antibody eligibility
    like any other source -- not a separate parallel system.

    region: one of REGION_STATES's keys ("eastern"/"central"/"pacific"), or None
    for no filtering (all verified entities regardless of state). Used to split
    this into 3 separate cron jobs, each running during ITS OWN 1-4am local
    window -- see REGION_STATES's comment for why and its bucketing caveats.
    """
    import os
    import sys
    _repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(_repo_root, "execution"))
    from hunter_brain import analyze_opportunity  # noqa: E402
    from . import recorder

    if region is not None and region not in REGION_STATES:
        raise ValueError(f"Unknown region {region!r} -- expected one of {sorted(REGION_STATES)} or None")

    db.init_db()
    with db.session() as conn:
        if region:
            states = sorted(REGION_STATES[region])
            placeholders = ",".join("?" * len(states))
            rows = conn.execute(
                f"SELECT entity_id, name, procurement_url FROM entity_procurement "
                f"WHERE verify_status = 'verified' AND procurement_url IS NOT NULL "
                f"AND state_code IN ({placeholders}) "
                f"ORDER BY entity_id LIMIT ?",
                (*states, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT entity_id, name, procurement_url FROM entity_procurement "
                "WHERE verify_status = 'verified' AND procurement_url IS NOT NULL "
                "ORDER BY entity_id LIMIT ?",
                (limit,),
            ).fetchall()
        breakered = {
            r["entity_id"]
            for r in conn.execute(
                "SELECT entity_id FROM procurement_watch WHERE consecutive_errors >= ?",
                (CIRCUIT_BREAKER_THRESHOLD,),
            ).fetchall()
        }

    targets = [(r["entity_id"], r["name"], r["procurement_url"]) for r in rows if r["entity_id"] not in breakered]
    logger.info("Phase B%s: %d candidates, %d skipped (circuit breaker), %d to fetch",
                f" [{region}]" if region else "", len(rows), len(rows) - len(targets), len(targets))

    started_at = datetime.now(timezone.utc).isoformat()
    fetch_results = []
    with ThreadPoolExecutor(max_workers=GLOBAL_CONCURRENCY) as pool:
        futures = {}
        for entity_id, name, url in targets:
            time.sleep(random.uniform(JITTER_MIN_SEC, JITTER_MAX_SEC) / GLOBAL_CONCURRENCY)
            futures[pool.submit(check_one, entity_id, url, True)] = name
        for i, fut in enumerate(as_completed(futures), 1):
            name = futures[fut]
            r = fut.result()
            fetch_results.append(r)
            tag = "OK" if r["content_hash"] else ("BLOCKED" if r["robots_allowed"] == 0 else "ERROR")
            logger.info("[fetch %d/%d] %-9s %-30s", i, len(targets), tag, name[:30])

    # Look up prior state once, before persisting -- needed both for the bookkeeping
    # below AND for the new/changed filter that decides what gets extracted.
    with db.session() as conn:
        priors = {r["entity_id"]: db.get_procurement_watch(conn, r["entity_id"]) for r in fetch_results}

    def _is_new_or_changed(r) -> bool:
        prior = priors.get(r["entity_id"])
        if not prior or not prior.get("content_hash"):
            return True  # no baseline yet -- first time seeing this page, needs a baseline extraction
        return prior["content_hash"] != r["content_hash"]

    # Persist the same Phase A hash bookkeeping (baseline for future change-detection).
    if not dry_run:
        with db.session() as conn:
            for r in fetch_results:
                prior = priors.get(r["entity_id"])
                consecutive_errors = 0 if r["content_hash"] else (prior.get("consecutive_errors", 0) if prior else 0) + 1
                is_change = bool(r["content_hash"] and prior and prior.get("content_hash") and prior["content_hash"] != r["content_hash"])
                db.upsert_procurement_watch(conn, {
                    **{k: v for k, v in r.items() if k != "visible_text"},
                    "last_changed": r["last_checked"] if is_change else (prior.get("last_changed") if prior else None),
                    "consecutive_errors": consecutive_errors,
                    "check_count": (prior.get("check_count", 0) if prior else 0) + 1,
                    "change_count": (prior.get("change_count", 0) if prior else 0) + (1 if is_change else 0),
                    "first_checked": prior.get("first_checked") if prior else r["last_checked"],
                })

    # Phase B: extract only on pages that are new or changed since the last check --
    # Jay's directive 2026-09-13: an unchanged page has nothing new to find, so skip
    # the expensive LLM call entirely rather than re-extracting the whole sample every run.
    all_fetched = [r for r in fetch_results if r["content_hash"] and r["visible_text"]]
    fetched = [r for r in all_fetched if _is_new_or_changed(r)]
    logger.info("Phase B: extracting on %d new/changed pages (%d unchanged, skipped)...",
                len(fetched), len(all_fetched) - len(fetched))

    raw_opportunities = []
    flagged_pages = []
    for r in fetched:
        rfps = extract_rfps(r["url"], r["visible_text"])
        if len(rfps) > FLAG_EXTRACTION_COUNT_THRESHOLD:
            # 2026-09-10, Jay's directive: don't let a hard page (messy nav-heavy
            # site, ambiguous open/closed structure -- libertycountyfl.org was the
            # case that surfaced this) block ingesting the pages that work cleanly.
            # An unusually high count on one page is exactly the signature of the
            # over-extraction failure mode already seen live -- hold it for a human
            # look instead of trusting it blind. The page still gets a real hash
            # recorded above (Phase A baseline unaffected), just not auto-ingested.
            logger.warning("  %s -> %d listing(s) -- FLAGGED (over threshold %d), holding for review, not ingesting",
                            r["url"], len(rfps), FLAG_EXTRACTION_COUNT_THRESHOLD)
            flagged_pages.append({
                "entity_id": r["entity_id"], "url": r["url"], "count": len(rfps),
                "titles": [x.get("title") for x in rfps],
                "flagged_at": r["last_checked"],
            })
            continue
        for rfp in rfps:
            raw_opportunities.append({
                "title": rfp.get("title") or "Untitled",
                "link": _synthetic_link(r["url"], rfp.get("title", ""), rfp.get("detail_url")),
                "snippet": rfp.get("description", ""),
                "source": "Direct-Source Watch",
                "_deadline": rfp.get("deadline"),
                "_entity_id": r["entity_id"],
            })
        if rfps:
            logger.info("  %s -> %d listing(s)", r["url"], len(rfps))

    logger.info("Phase B: %d raw listing(s) extracted across %d pages (%d pages flagged for review, not ingested)",
                len(raw_opportunities), len(fetched), len(flagged_pages))

    if flagged_pages:
        import json as _json
        flag_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                  "data", "procurement_watch_flagged_for_review.jsonl")
        os.makedirs(os.path.dirname(flag_path), exist_ok=True)
        with open(flag_path, "a", encoding="utf-8") as f:
            for fp in flagged_pages:
                f.write(_json.dumps(fp) + "\n")
        logger.info("Flagged pages appended to %s", flag_path)

    if dry_run:
        return {
            "candidates": len(rows), "fetched_total": len(all_fetched),
            "extracted_on": len(fetched), "raw_extracted": len(raw_opportunities), "dry_run": True,
        }

    # Delta-check + score + ingest, exactly like main.py's Phase 2.
    scored_opportunities = []
    new_count = reused_count = 0
    for opp in raw_opportunities:
        link = opp["link"]
        with db.session() as conn:
            existing = db.get_opportunity_by_link(conn, link)
        if existing and existing.get("raw_json"):
            import json as _json
            scored = _json.loads(existing["raw_json"])
            scored["delta_status"] = "reused"
            reused_count += 1
        else:
            scored = analyze_opportunity(opp)
            scored["delta_status"] = "new"
            new_count += 1
        scored_opportunities.append(scored)

    run_id = None
    if scored_opportunities:
        run_id = recorder.record_run(
            scored_opportunities=scored_opportunities,
            source_counts={"Direct-Source Watch": len(scored_opportunities)},
            errors=[],
            started_at=started_at,
        )

    high = [o for o in scored_opportunities if o.get("fit_label") == "High"]
    summary = {
        "candidates": len(rows),
        "fetched_total": len(all_fetched),
        "extracted_on": len(fetched),
        "raw_extracted": len(raw_opportunities),
        "new_scored": new_count,
        "reused": reused_count,
        "high_fit": len(high),
        "run_id": run_id,
        "dry_run": False,
    }
    logger.info("Phase B summary: %s", summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Direct-source procurement page watcher.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_pilot = sub.add_parser("pilot", help="Phase A only: fetch + hash, no LLM extraction.")
    p_pilot.add_argument("--limit", type=int, default=100)
    p_pilot.add_argument("--dry-run", action="store_true", help="Fetch + check robots.txt but don't write to the DB.")

    p_extract = sub.add_parser("extract", help="Phase B: fetch + hash + LLM-extract + score + ingest.")
    p_extract.add_argument("--limit", type=int, default=100)
    p_extract.add_argument("--dry-run", action="store_true", help="Fetch + extract but don't score/ingest/write.")
    p_extract.add_argument("--region", choices=sorted(REGION_STATES), default=None,
                            help="Only run entities whose state falls in this US timezone bucket "
                                 "(see REGION_STATES) -- used to split cron runs by timezone.")

    args = parser.parse_args()
    if args.command == "pilot":
        pilot(limit=args.limit, dry_run=args.dry_run)
    elif args.command == "extract":
        run_extraction(limit=args.limit, dry_run=args.dry_run, region=args.region)


if __name__ == "__main__":
    main()
