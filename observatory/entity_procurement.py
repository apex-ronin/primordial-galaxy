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

_UA = {"User-Agent": "primordial-observatory/1.0 (sovereign-local entity verifier; contact jay@apexronin.com)"}

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

_session = requests.Session()
_session.headers.update(_UA)


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

    url = website if website.startswith(("http://", "https://")) else f"http://{website}"
    try:
        resp = _session.get(url, timeout=15, allow_redirects=True)
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
    except requests.RequestException as e:
        return {
            "website_live": 0, "website_status_code": None, "procurement_url": None,
            "procurement_confidence": None, "portal_platform": None,
            "verify_status": "site_down", "error_detail": str(e)[:500], "meta_json": None,
        }
    except Exception as e:
        return {
            "website_live": None, "website_status_code": None, "procurement_url": None,
            "procurement_confidence": None, "portal_platform": None,
            "verify_status": "error", "error_detail": str(e)[:500], "meta_json": None,
        }


def verify(state_code: str | None = None, limit: int | None = None, delay: float = 1.0) -> dict:
    """Run the verifier over pending rows. Resumable: only touches verify_status='pending'."""
    db.init_db()
    verified = no_website = site_down = no_proc = errors = 0
    with db.session() as conn:
        rows = db.pending_entities(conn, state_code, limit)
        total = len(rows)
        print(f"[*] {total} pending entities" + (f" (state={state_code})" if state_code else ""))
        for i, row in enumerate(rows, 1):
            result = verify_one(row)
            db.record_verification(conn, row["entity_id"], result, _now())
            conn.commit()  # per-row commit -> killable/resumable, same as fulltext.py
            status = result["verify_status"]
            verified += status == "verified"
            no_website += status == "no_website"
            site_down += status == "site_down"
            no_proc += status == "no_procurement_found"
            errors += status == "error"
            if i % 10 == 0 or i == total:
                print(f"    {i}/{total}  verified={verified} no_website={no_website} "
                      f"site_down={site_down} no_procurement={no_proc} errors={errors}")
            if status != "no_website":  # no network call was made for no_website rows
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
    p_verify.add_argument("--delay", type=float, default=1.0, help="seconds between requests (default 1.0)")

    sub.add_parser("stats", help="Print entity_procurement counts by status and platform")

    args = ap.parse_args()
    if args.cmd == "seed":
        states = None if args.states.lower() == "all" else [s.strip() for s in args.states.split(",") if s.strip()]
        n = seed(states)
        print(f"[*] Seeded {n} entities into entity_procurement.")
        print(f"[*] DB: {db.DB_PATH}")
    elif args.cmd == "verify":
        verify(args.state, args.limit, args.delay)
    elif args.cmd == "stats":
        db.init_db()
        with db.session() as conn:
            print(json.dumps(db.entity_procurement_stats(conn), indent=2))
    else:  # pragma: no cover
        ap.error("unknown command")


if __name__ == "__main__":
    main()
