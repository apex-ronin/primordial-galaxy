"""Knowledge-store ingest (arc #3) — feeds the corpus_docs table.

Sovereign-local, read-from-public-APIs. Writes regulatory primary sources into
the same SQLite spine the dashboard reads, so the antibody ORACLE agent (arc #4)
can draw on FAR/DFARS clauses, Executive Orders, and GAO fraud cases without any
cloud dependency.

Source routing (decided from the 2026-06-14 govinfo research — see
docs/GOVINFO_RESEARCH_2026-06-14.md):
  - Executive Orders   -> Federal Register API (federalregister.gov/api/v1).
                          Structured EO endpoint, no key, current to this week.
                          govinfo's CFR Title 3 codification lags ~1 year.
  - FAR / DFARS clauses -> govinfo CFR collection, Title 48 (annual edition).
  - GAO fraud cases    -> govinfo GAOREPORTS collection (published service).
  - OMB memos (M-26-04) -> NOT in govinfo/FR; whitehouse.gov/omb (separate path).

Every ingested doc carries its primary-source URL (CLAUDE.md principle #3).

Usage (repo root, venv python):
    python -m observatory.ingest eo --limit 25          # newest 25 Executive Orders
    python -m observatory.ingest gao --start 2026-01-01 --end 2026-06-14
"""

from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime

from . import db

GOVINFO_BASE = "https://api.govinfo.gov"
FR_BASE = "https://www.federalregister.gov/api/v1"
# DEMO_KEY works but is heavily rate-limited; set GOVINFO_API_KEY in .env for real use.
# Sign up: https://www.govinfo.gov/api-signup
GOVINFO_KEY = os.getenv("GOVINFO_API_KEY", "DEMO_KEY")

_UA = {"User-Agent": "primordial-observatory/1.0 (sovereign-local ingest)"}


def _get_json(url: str, timeout: int = 30) -> dict:
    req = urllib.request.Request(url, headers=_UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


# ---------------------------------------------------------------------------
# Executive Orders  (Federal Register API — best EO source, current, no key)
# ---------------------------------------------------------------------------

def fetch_executive_orders(limit: int = 25) -> list[dict]:
    """Newest `limit` Executive Orders as corpus_doc dicts."""
    fields = ["executive_order_number", "title", "signing_date",
              "document_number", "html_url", "publication_date", "abstract"]
    params = [
        ("conditions[presidential_document_type]", "executive_order"),
        ("order", "newest"),
        ("per_page", str(min(limit, 1000))),
    ]
    for f in fields:
        params.append(("fields[]", f))
    url = f"{FR_BASE}/documents.json?" + urllib.parse.urlencode(params)
    data = _get_json(url)
    fetched_at = datetime.now().isoformat()
    docs = []
    for r in data.get("results", []):
        eo_num = r.get("executive_order_number")
        citation = f"EO {eo_num}" if eo_num else f"FR {r.get('document_number')}"
        docs.append({
            "source": "eo",
            "collection": "FR",
            "citation": citation,
            "title": r.get("title"),
            "url": r.get("html_url"),
            "published": r.get("signing_date") or r.get("publication_date"),
            "fetched_at": fetched_at,
            "text": r.get("abstract") or "",  # full text fetched on demand by ORACLE
            "embedded": 0,
            "meta_json": json.dumps({"document_number": r.get("document_number")}),
        })
    return docs


# ---------------------------------------------------------------------------
# GAO reports  (govinfo published service — fraud cases / Comptroller decisions)
# ---------------------------------------------------------------------------

def fetch_gao_reports(start: str, end: str | None = None, page_size: int = 50) -> list[dict]:
    """GAO reports as corpus_doc dicts, via the govinfo *collections* service.

    IMPORTANT (2026-06-14 research finding): govinfo's GAOREPORTS collection is a
    HISTORICAL archive — 16,569 packages but the newest dateIssued is ~2000. The
    published/{dateIssued} service therefore returns 0 for recent years. The
    collections service (keyed by lastModified) is what actually returns these
    older Comptroller General decisions, many directly procurement/fraud relevant
    ("Federal Acquisition: Trends, Reforms, and Challenges"). For CURRENT GAO
    reports, hit gao.gov directly (separate path, not wired here yet).

    `start` is a lastModified start date (YYYY-MM-DD, coerced to RFC3339).
    One page (page_size, max 1000); offsetMark pagination is a TODO for a full sweep.
    """
    start_ts = f"{start}T00:00:00Z"
    url = (f"{GOVINFO_BASE}/collections/GAOREPORTS/{start_ts}"
           f"?offsetMark=*&pageSize={page_size}&api_key={GOVINFO_KEY}")
    data = _get_json(url)
    fetched_at = datetime.now().isoformat()
    docs = []
    for pkg in data.get("packages", []):
        pkg_id = pkg.get("packageId")
        docs.append({
            "source": "gao",
            "collection": "GAOREPORTS",
            "citation": pkg_id,  # e.g. GAO-26-xxxxxx; unique per report
            "title": pkg.get("title"),
            "url": pkg.get("packageLink") or f"https://www.govinfo.gov/app/details/{pkg_id}",
            "published": pkg.get("dateIssued"),
            "fetched_at": fetched_at,
            "text": "",  # summary/full text pulled on demand via /packages/{id}/htm
            "embedded": 0,
            "meta_json": json.dumps({"lastModified": pkg.get("lastModified")}),
        })
    return docs


# ---------------------------------------------------------------------------
# FAR / DFARS clauses  (govinfo CFR, Title 48 -- clause-level granules)
# ---------------------------------------------------------------------------

def _latest_title48_package(vol: int, probe_back: int = 3) -> tuple[str, int]:
    """Return (packageId, year) for the newest available CFR Title 48 volume.

    CFR annual editions lag -- the 2025 edition was not published as of 2026-06
    (live-probed). Probe the current year backward until a summary resolves.
    """
    this_year = datetime.now().year
    last_err = None
    for year in range(this_year, this_year - probe_back - 1, -1):
        pid = f"CFR-{year}-title48-vol{vol}"
        try:
            _get_json(f"{GOVINFO_BASE}/packages/{pid}/summary?api_key={GOVINFO_KEY}")
            return pid, year
        except Exception as e:  # 404 until we hit a published edition
            last_err = e
    raise RuntimeError(f"No CFR Title 48 vol{vol} in last {probe_back + 1} years: {last_err}")


def _citation_from_granule(granule_id: str, label: str) -> str | None:
    """'CFR-2024-title48-vol2-sec52-204-21' -> 'FAR 52.204-21'."""
    marker = "-sec"
    i = granule_id.find(marker)
    if i == -1:
        return None
    sec = granule_id[i + len(marker):]   # '52-204-21'
    part, _, rest = sec.partition("-")    # '52', '204-21'
    return f"{label} {part}.{rest}" if rest else f"{label} {part}"


def fetch_title48(vol: int = 2, section: str = "sec52", source: str = "far",
                  year: int | None = None, limit: int | None = None) -> list[dict]:
    """FAR/DFARS clause granules from CFR Title 48 as corpus_doc dicts.

    Bounded by default to FAR Part 52 (vol 2 -- solicitation provisions and
    contract clauses), the slice that matters most for compliance. Point at
    DFARS 252 with vol/section/source overrides. Text is left empty (filled by
    the full-text pass) to keep enumeration cheap, mirroring the eo/gao ingest.
    """
    if year is not None:
        pid = f"CFR-{year}-title48-vol{vol}"
    else:
        pid, year = _latest_title48_package(vol)
    label = {"far": "FAR", "dfars": "DFARS"}.get(source, source.upper())
    # vol2 carries ~754 granules; pageSize 1000 returns them in a single page.
    url = (f"{GOVINFO_BASE}/packages/{pid}/granules"
           f"?api_key={GOVINFO_KEY}&pageSize=1000&offsetMark=*")
    data = _get_json(url)
    fetched_at = datetime.now().isoformat()
    needle = f"{section}-"
    docs = []
    for g in data.get("granules", []):
        gid = g.get("granuleId") or ""
        if needle not in gid:
            continue
        citation = _citation_from_granule(gid, label)
        if not citation:
            continue
        docs.append({
            "source": source,
            "collection": "CFR",
            "citation": citation,
            "title": g.get("title"),
            "url": f"https://www.govinfo.gov/app/details/{pid}/{gid}",
            "published": str(year),
            "fetched_at": fetched_at,
            "text": "",  # full text filled on demand via the granule htm endpoint
            "embedded": 0,
            "meta_json": json.dumps({"granuleId": gid, "package": pid, "vol": vol}),
        })
        if limit and len(docs) >= limit:
            break
    return docs


# ---------------------------------------------------------------------------
# persistence
# ---------------------------------------------------------------------------

def ingest(docs: list[dict]) -> int:
    """Upsert docs into corpus_docs (deduped by source+citation). Returns count."""
    db.init_db()
    n = 0
    with db.session() as conn:
        for d in docs:
            if not d.get("citation"):
                continue
            db.upsert_corpus_doc(conn, d)
            n += 1
    return n


def main() -> None:
    ap = argparse.ArgumentParser(description="Ingest regulatory primary sources into corpus_docs.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_eo = sub.add_parser("eo", help="Executive Orders (Federal Register)")
    p_eo.add_argument("--limit", type=int, default=25)

    p_gao = sub.add_parser("gao", help="GAO reports (govinfo collections, historical archive)")
    p_gao.add_argument("--start", required=True, help="lastModified start YYYY-MM-DD")
    p_gao.add_argument("--end", default=None, help="(unused; collections service is start-only)")

    p_far = sub.add_parser("far", help="FAR/DFARS clauses (govinfo CFR Title 48 granules)")
    p_far.add_argument("--vol", type=int, default=2, help="Title 48 volume (FAR Part 52 = vol 2)")
    p_far.add_argument("--section", default="sec52",
                       help="granule section prefix: sec52=FAR Part 52, sec252=DFARS Part 252")
    p_far.add_argument("--source", default="far", choices=["far", "dfars"])
    p_far.add_argument("--year", type=int, default=None, help="CFR edition year (default: newest available)")
    p_far.add_argument("--limit", type=int, default=None)

    args = ap.parse_args()
    if args.cmd == "eo":
        docs = fetch_executive_orders(args.limit)
    elif args.cmd == "gao":
        docs = fetch_gao_reports(args.start, args.end)
    elif args.cmd == "far":
        docs = fetch_title48(args.vol, args.section, args.source, args.year, args.limit)
    else:  # pragma: no cover
        ap.error("unknown command")

    n = ingest(docs)
    print(f"[*] Ingested {n} {args.cmd} docs into corpus_docs.")
    if docs:
        print(f"    sample: {docs[0]['citation']} - {(docs[0]['title'] or '')[:70]}")
    print(f"[*] DB: {db.DB_PATH}")


if __name__ == "__main__":
    main()
