"""Backfill the Observatory DB from an existing opportunities.json + scan log.

The recorder normally runs live inside main.py. This utility reconstructs a run
record after the fact so the dashboard has history immediately (e.g. today's
07:00 scan, which predates the recorder hook).

It parses the orchestrator log for per-module "Items: N" counts and timing, and
derives the fit distribution / served tier from the opportunities.json records.

Usage (from repo root, venv python):
    python -m observatory.backfill                       # newest scan log + execution/opportunities.json
    python -m observatory.backfill --log logs/scan_2026-06-14_0700.log
    python -m observatory.backfill --opps execution/opportunities.json --log <logfile>
"""

from __future__ import annotations

import argparse
import glob
import json
import os
import re
from datetime import datetime

from . import db
from .recorder import build_run_record

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# "2026-06-14 07:00:52,880 - Orchestrator - INFO - Module CSDA (Honey Pot) completed successfully. Items: 9"
_DONE = re.compile(
    r"(?P<ts>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)[,\d]* - Orchestrator - INFO - "
    r"Module (?P<name>.+?) completed successfully\. Items: (?P<n>\d+)"
)
# "2026-06-14 07:00:28,245 - Orchestrator - INFO - Starting module:"
_TS_ANY = re.compile(r"(?P<ts>\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)")
_FAIL = re.compile(
    r"- Orchestrator - ERROR - Module (?P<name>.+?) failed.*?: (?P<err>.+)"
)


def _newest_log() -> str | None:
    logs = sorted(glob.glob(os.path.join(_REPO_ROOT, "logs", "scan_*.log")))
    return logs[-1] if logs else None


def _read_text(path: str) -> str:
    """Read a log file regardless of encoding. PowerShell 5.1 Tee-Object writes
    UTF-16 LE (BOM); main.py's own stdout is UTF-8. Sniff the BOM, else try
    UTF-8 then fall back to UTF-16."""
    raw = open(path, "rb").read()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return raw.decode("utf-16")
    if raw[:3] == b"\xef\xbb\xbf":
        return raw.decode("utf-8-sig")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("utf-16", errors="replace")


def parse_log(log_path: str) -> dict:
    """Extract per-source counts, timing window, and errors from a scan log."""
    source_counts: dict[str, int] = {}
    errors: list[dict] = []
    timestamps: list[str] = []
    for line in _read_text(log_path).splitlines():
        m = _DONE.search(line)
        if m:
            source_counts[m.group("name")] = int(m.group("n"))
        mt = _TS_ANY.search(line)
        if mt:
            timestamps.append(mt.group("ts"))
        mf = _FAIL.search(line)
        if mf:
            errors.append({"module": mf.group("name"), "error": mf.group("err").strip()})
    started = finished = None
    if timestamps:
        started = timestamps[0].replace(" ", "T")
        finished = timestamps[-1].replace(" ", "T")
    return {
        "source_counts": source_counts,
        "errors": errors,
        "started_at": started,
        "finished_at": finished,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Backfill Observatory DB from a past run.")
    ap.add_argument("--opps", default=os.path.join(_REPO_ROOT, "execution", "opportunities.json"))
    ap.add_argument("--log", default=None, help="scan log path (default: newest in logs/)")
    args = ap.parse_args()

    log_path = args.log or _newest_log()
    with open(args.opps, "r", encoding="utf-8") as f:
        opps = json.load(f)

    parsed = {"source_counts": {}, "errors": [], "started_at": None, "finished_at": None}
    if log_path and os.path.exists(log_path):
        parsed = parse_log(log_path)
        print(f"[*] Parsed log: {os.path.basename(log_path)} -> sources={parsed['source_counts']}")
    else:
        print("[!] No scan log found; deriving source counts from opportunities.json only.")

    # Fall back to per-source counts from the records themselves if the log
    # yielded nothing (e.g. older logs without the module lines).
    source_counts = parsed["source_counts"]
    if not source_counts:
        from collections import Counter
        source_counts = dict(Counter(o.get("source", "Unknown") for o in opps))

    started = parsed["started_at"] or datetime.now().isoformat()
    finished = parsed["finished_at"] or started

    db.init_db()
    run = build_run_record(opps, source_counts, parsed["errors"], started, finished, log_path)
    with db.session() as conn:
        run_id = db.insert_run(conn, run)
        for o in opps:
            if o.get("link"):
                db.upsert_opportunity(conn, o, run_id, finished)

    print(f"[*] Backfilled run #{run_id}: status={run['status']} "
          f"scored={run['total_scored']} high={run['high_count']} "
          f"tier={run['tier_served']} local_used={bool(run['local_tier_used'])}")
    print(f"[*] DB: {db.DB_PATH}")


if __name__ == "__main__":
    main()
