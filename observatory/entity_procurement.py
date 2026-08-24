"""Arc #6 Heartland, Phase 1 — entity_procurement seed + verifier job.

Source data: principalities-index (separate repo, sibling checkout) --
78,291 Census-of-Governments entities, one JSON object per line at
G:\\repos\\principalities-index\\data\\master_gov_units_2022.jsonl. That repo
is the source of truth for entity identity (id/name/state/county/population/
website); this module only reads it, never writes it.

Two-step job, matching the ARC6 plan (ARC6_HEARTLAND_PLAN_2026-08-05.md):
  1. seed   -- load entities into observatory's entity_procurement table
              (verify_status='pending'). Cheap, no network calls.
  2. verify -- for each pending entity: confirm the website is live, look for
              a procurement/bids page, and detect which shared portal
              platform (if any) it runs on. Slow and deliberate on purpose
              (rate-limited, resumable) -- mirrors fulltext.py's pattern.

Midwest-first per the plan: IL OH IN MI WI MN IA MO KS NE ND SD.

Usage (repo root, venv python):
    python -m observatory.entity_procurement seed --states IL,OH,IN,MI,WI,MN,IA,MO,KS,NE,ND,SD
    python -m observatory.entity_procurement verify --state IL --limit 50
    python -m observatory.entity_procurement stats
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import requests

from . import db

PRINCIPALITIES_JSONL = Path(r"G:\repos\principalities-index\data\master_gov_units_2022.jsonl")

# execution/ isn't a package (no __init__.py, its own modules use bare sibling
# imports) -- add it to sys.path explicitly so this package can reuse the real
# LLM cascade for the grounded compliance check below, instead of duplicating it.
_EXECUTION_DIR = Path(r"G:\repos\primordial-galaxy\execution")
if str(_EXECUTION_DIR) not in sys.path:
    sys.path.insert(0, str(_EXECUTION_DIR))

MIDWEST_STATES = ["IL", "OH", "IN", "MI", "WI", "MN", "IA", "MO", "KS", "NE", "ND", "SD"]

# Census Bureau regions, same pattern as MIDWEST_STATES above (which is exactly
# East North Central + West North Central). Region sweep order per Jay's
# 2026-08-10/11 direction: Midwest -> West Coast (done) -> South -> East.
WEST_COAST_STATES = ["CA", "OR", "WA"]
SOUTH_STATES = [  # South Atlantic + East South Central + West South Central
    "DE", "MD", "DC", "VA", "WV", "NC", "SC", "GA", "FL",
    "KY", "TN", "MS", "AL",
    "AR", "LA", "OK", "TX",
]

# Census-of-Governments (principalities-index) is LOCAL government only --
# confirmed 2026-08-10 (government_type values are only County/Municipal/
# Township/None, no State). State-level procurement portals typically carry
# more RFP volume per entity than any single county/township, per Jay's
# 2026-08-10 direction to cascade state -> county -> city/township. This is
# a separate, hand-curated seed (~50 entries max, not scraped) -- each URL
# below was looked up and sourced this session, not recalled from memory, to
# hold to the same "trust but verify" bar as the scraped data (state, name,
# procurement office URL, source).
STATE_PORTALS = {
    "IL": ("Illinois", "https://www.bidbuy.illinois.gov/bso/"),
    "OH": ("Ohio", "https://procure.ohio.gov"),
    "IN": ("Indiana", "https://secure.in.gov/idoa/procurement/current-business-opportunities/"),
    "MI": ("Michigan", "https://www.michigan.gov/dtmb/procurement/contractconnect"),
    "WI": ("Wisconsin", "https://vendornet.wi.gov/"),
    "MN": ("Minnesota", "https://mn.gov/admin/osp/vendors/solicitations-and-contract-opportunities/supplier-portal/"),
    "IA": ("Iowa", "https://bidopportunities.iowa.gov/"),
    "MO": ("Missouri", "https://missouribuys.mo.gov/bid-board"),
    "KS": ("Kansas", "https://admin.ks.gov/offices/procurement-contracts/bidding--contracts/additional-bid-opportunities"),
    "NE": ("Nebraska", "https://das.nebraska.gov/materiel/bid-opportunities.html"),
    "ND": ("North Dakota", "https://www.omb.nd.gov/doing-business-state/procurement/ndbuys"),
    "SD": ("South Dakota", "https://boa.sd.gov/central-services/procurement-management/"),
    "CA": ("California", "https://caleprocure.ca.gov/"),
    "OR": ("Oregon", "https://orpin.oregon.gov/"),
    "WA": ("Washington", "https://des.wa.gov/sell/bid-opportunities"),
    # South region, sourced 2026-08-11
    "DE": ("Delaware", "https://bids.delaware.gov/"),
    "MD": ("Maryland", "https://procurement.maryland.gov"),
    "DC": ("District of Columbia", "https://ocp.dc.gov/"),
    "VA": ("Virginia", "https://eva.virginia.gov/"),
    "WV": ("West Virginia", "https://wvtreasury.gov/about/bidding-opportunities"),
    "NC": ("North Carolina", "https://evp.nc.gov/"),
    "SC": ("South Carolina", "https://scbo.sc.gov/"),
    "GA": ("Georgia", "https://ssl.doas.state.ga.us/gpr/"),
    "FL": ("Florida", "https://vendor.myfloridamarketplace.com/"),
    "KY": ("Kentucky", "https://finance.ky.gov/eProcurement/Pages/default.aspx"),
    "TN": ("Tennessee", "https://www.tn.gov/generalservices/procurement.html"),
    "MS": ("Mississippi", "https://www.ms.gov/dfa/contract_bid_search/Bid"),
    "AL": ("Alabama", "https://purchasing.alabama.gov"),
    "AR": ("Arkansas", "https://sas.arkansas.gov/procurement/bid-opportunities/"),
    "LA": ("Louisiana", "https://wwwcfprd.doa.louisiana.gov/osp/lapac/pubmain.cfm"),
    "OK": ("Oklahoma", "https://www.ok.gov/dcs/solicit/app/index.php"),
    "TX": ("Texas", "https://www.txsmartbuy.gov/esbd"),
}

_UA = {
    "User-Agent": "primordial-observatory/1.0 (sovereign-local entity verifier; contact jay@apexronin.com)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Domain substrings for the ~10 shared platforms small governments cluster on
# (ARC6 plan, phase 2 rationale -- one adapter unlocks thousands of entities).
# Matched against any outbound link found on the entity's homepage.
PLATFORM_SIGNATURES = {
    "bidnetdirect.com": "bidnet_direct",
    "gobonfire.com": "bonfire",
    "bonfirehub.com": "bonfire",
    "procurenow.com": "opengov_procurenow",
    "opengov.com": "opengov_procurenow",
    "demandstar.com": "demandstar",
    "publicpurchase.com": "publicpurchase",
    "questcdn.com": "questcdn",
    "ionwave.net": "ionwave",
    "periscopeholdings.com": "periscope_bidsync",
    "bidsync.com": "periscope_bidsync",
    "cit-e.net": "cit_e",
}

# Fallback: link text/href keywords when no known-platform domain is found --
# still a real procurement-page candidate, just on a custom/plain-HTML site.
PROCUREMENT_KEYWORDS = ["bid", "rfp", "rfq", "procurement", "purchasing", "solicitation", "vendor"]

_ANCHOR_RE = re.compile(r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', re.I | re.S)
_TAG_RE = re.compile(r"<[^>]+>")


# ---------------------------------------------------------------------------
# step 1: seed
# ---------------------------------------------------------------------------

def load_entities(states: list[str] | None = None) -> list[dict]:
    """Read principalities-index's master JSONL, optionally filtered to `states`."""
    if not PRINCIPALITIES_JSONL.exists():
        raise FileNotFoundError(
            f"principalities-index data not found at {PRINCIPALITIES_JSONL} "
            "(expected a sibling checkout at G:\\repos\\principalities-index)"
        )
    wanted = {s.upper() for s in states} if states else None
    out = []
    with open(PRINCIPALITIES_JSONL, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            meta = rec.get("metadata", {})
            state = meta.get("state_code")
            if wanted and state not in wanted:
                continue
            contact = rec.get("contact_skeleton") or {}
            out.append({
                "entity_id": rec["id"],
                "name": rec.get("name"),
                "state_code": state,
                "government_type": meta.get("government_type"),
                "county": meta.get("county"),
                "population": meta.get("population"),
                "website": contact.get("web_address"),
                "contact_email": contact.get("caio_email"),
            })
    return out


def seed(states: list[str] | None = None) -> int:
    entities = load_entities(states)
    seen_at = _now()
    db.init_db()
    n = 0
    with db.session() as conn:
        for e in entities:
            db.seed_entity(conn, e, seen_at)
            n += 1
    return n


def seed_states(states: list[str] | None = None) -> int:
    """Seed the hand-curated STATE_PORTALS rows. entity_id is "STATE-<code>"."""
    wanted = states or list(STATE_PORTALS.keys())
    seen_at = _now()
    db.init_db()
    n = 0
    with db.session() as conn:
        for code in wanted:
            if code not in STATE_PORTALS:
                continue
            name, url = STATE_PORTALS[code]
            db.seed_entity(conn, {
                "entity_id": f"STATE-{code}",
                "name": f"State of {name} (procurement office)",
                "state_code": code,
                "government_type": "0 - STATE",
                "county": None,
                "population": None,
                "website": url,
            }, seen_at)
            n += 1
    return n


# ---------------------------------------------------------------------------
# step 2: verify
# ---------------------------------------------------------------------------

def _strip_tags(html: str) -> str:
    return " ".join(_TAG_RE.sub(" ", html).split())


def _find_procurement_link(html: str, base_url: str) -> tuple[str | None, str | None, str | None]:
    """Scan a homepage's anchors for a known portal domain or a procurement-keyword link.

    Returns (procurement_url, portal_platform, confidence). confidence is
    "domain_signature" | "keyword_match" | None.
    """
    import urllib.parse as up

    candidates = []
    for href, text in _ANCHOR_RE.findall(html):
        abs_url = up.urljoin(base_url, href.strip())
        label = _strip_tags(text).lower()
        candidates.append((abs_url, label))

    # pass 1: known shared-platform domains -- highest confidence, tells us the
    # adapter target directly (ARC6 plan phase 2).
    for abs_url, _label in candidates:
        host = (up.urlparse(abs_url).hostname or "").lower()
        for sig, platform in PLATFORM_SIGNATURES.items():
            if sig in host:
                return abs_url, platform, "domain_signature"

    # pass 2: keyword match on link text or path -- custom/plain-HTML sites.
    for abs_url, label in candidates:
        path = up.urlparse(abs_url).path.lower()
        if any(kw in label or kw in path for kw in PROCUREMENT_KEYWORDS):
            return abs_url, "custom_html", "keyword_match"

    return None, None, None


def verify_one(row) -> dict:
    """Check one entity_procurement row's website. Returns a record_verification()-shaped dict."""
    website = row["website"]
    if not website:
        return {
            "website_live": None, "website_status_code": None, "procurement_url": None,
            "procurement_confidence": None, "portal_platform": None,
            "verify_status": "no_website", "error_detail": None, "meta_json": None,
        }

    # Always try HTTPS first regardless of what scheme the 2022 source data
    # recorded: most gov sites are HTTPS-only now (or reject/hang on port 80
    # entirely), and the source's own "http://" prefix is just as often stale
    # as a bare domain would be (2026-08-10 finding: Alameda/Contra Costa/El
    # Dorado all stored as "http://..." and timed out on port 80). Only try
    # the second scheme on a connection-level failure, never on an HTTP
    # status code -- a 403/404 is a real answer from a real server.
    host_and_path = re.sub(r"^https?://", "", website, flags=re.I)
    candidates = [f"https://{host_and_path}", f"http://{host_and_path}"]

    resp = last_exc = None
    for url in candidates:
        try:
            # No shared session: each entity is a different host, so connection-pool
            # reuse buys nothing, and a plain requests.get() keeps this call
            # trivially thread-safe for the concurrent verify() pool below.
            resp = requests.get(url, headers=_UA, timeout=12, allow_redirects=True)
            break
        except requests.RequestException as e:
            last_exc = e
            continue

    if resp is None:
        return {
            "website_live": 0, "website_status_code": None, "procurement_url": None,
            "procurement_confidence": None, "portal_platform": None,
            "verify_status": "site_down", "error_detail": str(last_exc)[:500], "meta_json": None,
        }
    try:
        live = resp.status_code < 400
        if not live:
            return {
                "website_live": 0, "website_status_code": resp.status_code, "procurement_url": None,
                "procurement_confidence": None, "portal_platform": None,
                "verify_status": "site_down", "error_detail": f"HTTP {resp.status_code}", "meta_json": None,
            }
        proc_url, platform, confidence = _find_procurement_link(resp.text, resp.url)
        if proc_url:
            status = "verified"
        else:
            platform, status = "none", "no_procurement_found"
        return {
            "website_live": 1, "website_status_code": resp.status_code, "procurement_url": proc_url,
            "procurement_confidence": confidence, "portal_platform": platform,
            "verify_status": status, "error_detail": None, "meta_json": None,
        }
    except Exception as e:
        return {
            "website_live": None, "website_status_code": None, "procurement_url": None,
            "procurement_confidence": None, "portal_platform": None,
            "verify_status": "error", "error_detail": str(e)[:500], "meta_json": None,
        }


def verify(state_code: str | None = None, limit: int | None = None,
          delay: float = 0.0, workers: int = 20) -> dict:
    """Run the verifier over pending rows, `workers` requests in flight at once.

    Resumable: only touches verify_status='pending'. Network fetches
    (verify_one) run concurrently in a thread pool -- each entity is a
    different host, so there's no shared connection or rate-limit state to
    protect, unlike the single-API fulltext.py job this pattern otherwise
    mirrors. DB writes stay on the main thread (one row at a time, own
    short-lived connection per write) so sqlite never sees concurrent
    writers -- only the I/O-bound part is parallel.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    db.init_db()
    with db.session() as conn:
        rows = db.pending_entities(conn, state_code, limit)
    total = len(rows)
    print(f"[*] {total} pending entities" + (f" (state={state_code})" if state_code else "")
          + f"  workers={workers}")

    verified = no_website = site_down = no_proc = errors = 0
    done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(verify_one, row): row for row in rows}
        for fut in as_completed(futures):
            row = futures[fut]
            try:
                result = fut.result()
            except Exception as e:  # pragma: no cover - verify_one already catches broadly
                result = {
                    "website_live": None, "website_status_code": None, "procurement_url": None,
                    "procurement_confidence": None, "portal_platform": None,
                    "verify_status": "error", "error_detail": str(e)[:500], "meta_json": None,
                }
            with db.session() as conn:
                db.record_verification(conn, row["entity_id"], result, _now())
            done += 1
            status = result["verify_status"]
            verified += status == "verified"
            no_website += status == "no_website"
            site_down += status == "site_down"
            no_proc += status == "no_procurement_found"
            errors += status == "error"
            if done % 50 == 0 or done == total:
                print(f"    {done}/{total}  verified={verified} no_website={no_website} "
                      f"site_down={site_down} no_procurement={no_proc} errors={errors}")
            if delay:
                time.sleep(delay)

    summary = {"total": total, "verified": verified, "no_website": no_website,
               "site_down": site_down, "no_procurement_found": no_proc, "error": errors}
    print(f"[*] done: {summary}")
    return summary


# ---------------------------------------------------------------------------
# step 3: compliance scan + review queue (2026-08-11, Jay's directive)
#
# Local/county solicitations don't run under the FAR themselves -- but when a
# local project is federally grant-funded (FEMA, DOT, HUD, etc.) the award
# terms flow federal clauses down into the local solicitation, and that
# boilerplate is exactly the kind of thing that goes stale (ARC6 plan's
# "compliance red-team as wedge": RFO effective 2026-04-17 renumbered/split a
# lot of FAR clauses -- see corpus_docs source='far' vs 'far_rfo').
#
# Two-stage, per Jay's explicit correction (2026-08-11) -- the regex citation
# match is a CHEAP PREFILTER to shortlist candidates, never the determination
# itself. Every regex hit gets a real grounded pass (antibody_agent's actual
# corpus_docs retrieval + the now-live local LLM tier) before anything is
# trusted enough to reach the review queue.
# ---------------------------------------------------------------------------

_FAR_CITATION_RE = re.compile(r"(?:FAR|DFARS)\s*(\d{1,3}\.\d{2,4}(?:-\d{1,4})?)", re.I)


def scan_one_compliance(row) -> list[str]:
    """Fetch a verified entity's procurement_url and return raw FAR/DFARS citation candidates
    (regex prefilter only -- NOT a verdict, see assess_far_citation)."""
    url = row["procurement_url"]
    if not url:
        return []
    try:
        resp = requests.get(url, headers=_UA, timeout=12, allow_redirects=True)
        if resp.status_code >= 400:
            return []
        return sorted(set(_FAR_CITATION_RE.findall(resp.text)))
    except requests.RequestException:
        return []


def _corpus_lookup(citation_number: str, source: str) -> str | None:
    """corpus_docs title+text for a bare FAR-style number (e.g. '52.204-21') in one source, or None."""
    with db.session() as conn:
        row = conn.execute(
            "SELECT title, text FROM corpus_docs WHERE source = ? AND citation LIKE ? LIMIT 1",
            (source, f"%{citation_number}%"),
        ).fetchone()
    if not row:
        return None
    return f"{row['title'] or ''}\n{(row['text'] or '')[:600]}".strip()


def assess_far_citation(citation_number: str) -> dict:
    """Grounded verdict on one citation: current, superseded, or uncertain.

    Evidence comes from corpus_docs, not the model's own memory: looks the
    citation up in BOTH the RFO-current corpus (source='far_rfo', effective
    2026-04-17) and the older CFR-edition corpus (source='far'). The LLM's job
    is to weigh evidence that's actually retrieved, not to recall FAR numbers
    from training data -- same grounding discipline as antibody_agent._is_grounded.
    """
    current_text = _corpus_lookup(citation_number, "far_rfo")
    old_text = _corpus_lookup(citation_number, "far")

    if current_text is None and old_text is None:
        return {
            "status": "uncertain",
            "note": (f"FAR {citation_number} not found in either corpus on file "
                     "(far_rfo ingest only covers Parts 3/9/15/19/52 so far -- "
                     "absence isn't proof of anything either way)."),
        }

    evidence = (
        f"RFO-current corpus (effective 2026-04-17) entry for FAR {citation_number}: "
        f"{current_text[:600] if current_text else 'NOT FOUND in current corpus.'}\n\n"
        f"Older CFR-edition corpus entry for FAR {citation_number}: "
        f"{old_text[:600] if old_text else 'NOT FOUND in older corpus.'}"
    )
    prompt = (
        f"A local government's posted procurement solicitation cites \"FAR {citation_number}\".\n\n"
        f"{evidence}\n\n"
        "Based ONLY on this evidence, is this citation likely still current, or likely "
        "stale/superseded/renumbered? Do not guess beyond what the evidence shows -- if the "
        "evidence is ambiguous or thin, say uncertain rather than force a call.\n\n"
        "Return ONLY valid JSON, no markdown, no backticks:\n"
        '{"status": "current" | "superseded" | "uncertain", "note": "one sentence, cite the evidence"}'
    )
    from llm_client import complete as llm_complete
    raw = llm_complete(prompt, system="You are a JSON-only API. Output strictly valid JSON.", mode="fast")
    if not raw:
        return {"status": "uncertain", "note": "Local + fallback LLM tiers both unavailable for the grounded check."}
    try:
        if "```" in raw:
            raw = raw.split("```")[1]
            raw = raw[4:] if raw.startswith("json") else raw
        verdict = json.loads(raw.strip())
        status = verdict.get("status")
        if status not in ("current", "superseded", "uncertain"):
            status = "uncertain"
        return {"status": status, "note": str(verdict.get("note", ""))[:400]}
    except Exception:
        return {"status": "uncertain", "note": "LLM response wasn't parseable JSON."}


def scan_compliance(limit: int | None = None, workers: int = 20) -> dict:
    """Compliance-scan every verified-but-unscanned entity: regex prefilter, then a grounded
    LLM verdict on every candidate citation. Resumable like verify()."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    db.init_db()
    with db.session() as conn:
        rows = db.unscanned_verified_entities(conn, limit)
    total = len(rows)
    print(f"[*] {total} verified entities need a compliance scan  workers={workers}")

    # Stage 1: cheap concurrent prefilter (network I/O bound, same pattern as verify()).
    prefiltered = done = 0
    candidates = {}  # entity_id -> row, only rows with >=1 citation candidate
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(scan_one_compliance, row): row for row in rows}
        for fut in as_completed(futures):
            row = futures[fut]
            try:
                citations = fut.result()
            except Exception:
                citations = []
            done += 1
            if citations:
                candidates[row["entity_id"]] = (row, citations)
                prefiltered += 1
            else:
                with db.session() as conn:
                    db.record_far_citations(conn, row["entity_id"], [])
            if done % 100 == 0 or done == total:
                print(f"    prefilter {done}/{total}  candidates={prefiltered}")

    # Stage 2: grounded LLM verdict per candidate citation -- CPU-bound (local tier),
    # sequential on purpose (Jay's 50% cap is a per-call resource cap, not a license to
    # fan out N concurrent local-model calls at once).
    flagged = 0
    total_candidates = len(candidates)
    print(f"[*] {total_candidates} entities have citation candidates -- running grounded checks")
    for i, (entity_id, (row, citations)) in enumerate(candidates.items(), 1):
        verdicts = [{"citation": c, **assess_far_citation(c)} for c in citations]
        with db.session() as conn:
            db.record_far_citations(conn, entity_id, verdicts)
        if any(v["status"] == "superseded" for v in verdicts):
            flagged += 1
        if i % 10 == 0 or i == total_candidates:
            print(f"    grounded {i}/{total_candidates}  superseded={flagged}")

    summary = {"total": total, "prefiltered": prefiltered, "flagged_superseded": flagged}
    print(f"[*] done: {summary}")
    return summary


def _draft_for(row, superseded: list[dict]) -> tuple[str, int, str, str]:
    """Build (reason, priority_score, draft_subject, draft_body) for an entity with at least
    one citation the grounded check actually assessed as superseded (not just cited)."""
    cite_list = ", ".join(f"FAR {v['citation']}" for v in superseded)
    notes = " ".join(f"({v['citation']}: {v['note']})" for v in superseded if v.get("note"))
    reason = f"Grounded check flagged possibly-superseded clause(s): {cite_list}. {notes}".strip()
    priority = 15 * len(superseded)
    subject = f"Quick note on a federal clause reference in {row['name']}'s posted solicitation"
    body = (
        f"Hello,\n\n"
        f"While reviewing publicly posted procurement notices, we noticed {row['name']}'s "
        f"solicitation page ({row['procurement_url']}) references {cite_list}, which our "
        f"records suggest may no longer be current following the FAR overhaul effective "
        f"2026-04-17. Details: {notes}\n\n"
        f"If this solicitation involves federally-funded work, it may be worth a quick check "
        f"that the cited clause language is still accurate. Happy to share what we found and "
        f"talk through it if useful -- no obligation either way.\n\n"
        f"Best,\n[Your name]"
    )
    return reason, priority, subject, body


def build_review_queue(limit: int | None = None) -> int:
    """Promote entities with a grounded 'superseded' verdict into outreach_review.
    Citation-found-but-current, or uncertain, do NOT promote -- only an actual verdict does.
    Returns count added/refreshed."""
    db.init_db()
    created_at = _now()
    n = 0
    with db.session() as conn:
        sql = ("SELECT * FROM entity_procurement WHERE verify_status = 'verified' "
               "AND far_citations_json IS NOT NULL AND far_citations_json != '[]'")
        if limit:
            sql += f" LIMIT {int(limit)}"
        rows = conn.execute(sql).fetchall()
        for row in rows:
            try:
                verdicts = json.loads(row["far_citations_json"] or "[]")
            except Exception:
                continue
            # Old-format rows (pre-grounded-check, bare citation strings) have no "status" --
            # skip them; they'll get real verdicts next scan-compliance pass.
            superseded = [v for v in verdicts if isinstance(v, dict) and v.get("status") == "superseded"]
            if not superseded:
                continue
            reason, priority, subject, body = _draft_for(row, superseded)
            db.upsert_outreach_review(conn, {
                "entity_id": row["entity_id"],
                "reason": reason,
                "priority_score": priority,
                "contact_email": row["contact_email"],
                "draft_subject": subject,
                "draft_body": body,
            }, created_at)
            n += 1
    return n


def _now() -> str:
    return datetime.now().isoformat()


def main() -> None:
    ap = argparse.ArgumentParser(description="Arc #6 Heartland Phase 1: entity_procurement seed + verifier.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_seed = sub.add_parser("seed", help="Load entities from principalities-index into entity_procurement")
    p_seed.add_argument("--states", default=",".join(MIDWEST_STATES),
                        help=f"comma-separated state codes (default: Midwest, {','.join(MIDWEST_STATES)}); 'all' for every entity")

    p_verify = sub.add_parser("verify", help="Check website liveness + locate procurement page + detect platform")
    p_verify.add_argument("--state", default=None, help="restrict to one state code")
    p_verify.add_argument("--limit", type=int, default=None, help="cap rows this run (use a small value to test)")
    p_verify.add_argument("--delay", type=float, default=0.0, help="extra seconds after each completed request (default 0, no throttle needed -- each entity is a different host)")
    p_verify.add_argument("--workers", type=int, default=20, help="concurrent requests in flight (default 20)")

    p_seed_states = sub.add_parser("seed-states", help="Seed the hand-curated state-level procurement portals (STATE_PORTALS)")
    p_seed_states.add_argument("--states", default=None,
                               help="comma-separated state codes (default: all in STATE_PORTALS)")

    p_scan = sub.add_parser("scan-compliance", help="Scan verified entities' procurement pages for FAR/DFARS clause citations")
    p_scan.add_argument("--limit", type=int, default=None)
    p_scan.add_argument("--workers", type=int, default=20)

    p_queue = sub.add_parser("build-queue", help="Promote FAR-citation-flagged entities into the outreach_review queue")
    p_queue.add_argument("--limit", type=int, default=None)

    sub.add_parser("stats", help="Print entity_procurement counts by status and platform")

    args = ap.parse_args()
    if args.cmd == "seed":
        states = None if args.states.lower() == "all" else [s.strip() for s in args.states.split(",") if s.strip()]
        n = seed(states)
        print(f"[*] Seeded {n} entities into entity_procurement.")
        print(f"[*] DB: {db.DB_PATH}")
    elif args.cmd == "seed-states":
        states = [s.strip() for s in args.states.split(",")] if args.states else None
        n = seed_states(states)
        print(f"[*] Seeded {n} state-level procurement portals into entity_procurement.")
        print(f"[*] DB: {db.DB_PATH}")
    elif args.cmd == "verify":
        verify(args.state, args.limit, args.delay, args.workers)
    elif args.cmd == "scan-compliance":
        scan_compliance(args.limit, args.workers)
    elif args.cmd == "build-queue":
        n = build_review_queue(args.limit)
        print(f"[*] {n} entities in the review queue (pending_review rows refreshed, human decisions untouched).")
    elif args.cmd == "stats":
        db.init_db()
        with db.session() as conn:
            print(json.dumps(db.entity_procurement_stats(conn), indent=2))
    else:  # pragma: no cover
        ap.error("unknown command")


if __name__ == "__main__":
    main()
