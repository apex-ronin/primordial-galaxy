#!/usr/bin/env bash
# Direct-source procurement watcher - daily extraction run (Linux cron).
# Separate cron entry from run_scanner.sh by design: this hits 5,308+
# individual government sites directly (not an aggregator API), and its
# per-run cost now scales with how many pages actually changed since the
# last check, not the full sample size -- see procurement_watch.py's
# run_extraction() new/changed filter (2026-09-13).
#
# Takes a region as $1 (eastern/central/pacific/all) -- Jay's directive
# 2026-09-13: run each US timezone's entities during ITS OWN 1-4am local
# window, not one global time. See REGION_STATES in procurement_watch.py
# for the bucketing (approximate, state-majority-zone, not per-entity).
#
# THIS BOX'S CRON RUNS ONE SYSTEM TIMEZONE (UTC), NOT PER-JOB TZ --
# confirmed via `man 5 crontab`: TZ set in a crontab only affects the
# command's environment, not when it fires. So the 3 region cron entries
# below are manually UTC-converted for CURRENT DST (EDT/CDT/PDT, active
# through the first Sunday of November 2026) and WILL DRIFT BY 1 HOUR
# at each DST transition until manually re-adjusted:
#
#   crontab -l   (current entries, as of 2026-09-13, DST/EDT+CDT+PDT in effect)
#   0  5 * * * .../run_scanner.sh                              # federal/SAM.gov main -- 1am Eastern
#   0  7 * * * .../run_procurement_watch.sh eastern             # 3am Eastern
#   0  8 * * * .../run_procurement_watch.sh central             # 3am Central
#   0 10 * * * .../run_procurement_watch.sh pacific             # 3am Pacific
#
# At the Nov DST rollback (EST/CST/PST, UTC offsets go up by 1hr each),
# add 1 hour to every entry above (05->06, 07->08, 08->09, 10->11) to hold
# the same real local times. Reverse at the next spring-forward.
set -uo pipefail

REGION="${1:-}"
if [[ -z "$REGION" ]]; then
  echo "Usage: $0 <eastern|central|pacific|all>" >&2
  exit 1
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
LOG_FILE="$LOG_DIR/procurement_watch_${REGION}_$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$LOG_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "venv python not found at $PYTHON_BIN" | tee -a "$LOG_FILE"
  exit 1
fi

cd "$PROJECT_ROOT"
if [[ "$REGION" == "all" ]]; then
  REGION_ARGS=()
else
  REGION_ARGS=(--region "$REGION")
fi
"$PYTHON_BIN" -m observatory.procurement_watch extract --limit 100 "${REGION_ARGS[@]}" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# 30-day log trim, matching run_scanner.sh's convention.
find "$LOG_DIR" -name "procurement_watch_*.log" -mtime +30 -delete

exit $EXIT_CODE
