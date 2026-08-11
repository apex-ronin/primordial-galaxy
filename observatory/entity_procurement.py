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
import time
from datetime import datetime
from pathlib import Path

import requests

from . import db

PRINCIPALITIES_JSONL = Path(r"G:\repos\principalities-index\data\master_gov_units_2022.jsonl")

MIDWEST_STATES = ["IL", "OH", "IN", "MI", "WI", "MN", "IA", "MO", "KS", "NE", "ND", "SD"]

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
            out.append({
                "entity_id": rec["id"],
                "name": rec.get("name"),
                "state_code": state,
                "government_type": meta.get("government_type"),
                "county": meta.get("county"),
                "population": meta.get("population"),
                "website": (rec.get("contact_skeleton") or {}).get("web_address"),
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
    elif args.cmd == "stats":
        db.init_db()
        with db.session() as conn:
            print(json.dumps(db.entity_procurement_stats(conn), indent=2))
    else:  # pragma: no cover
        ap.error("unknown command")


if __name__ == "__main__":
    main()
