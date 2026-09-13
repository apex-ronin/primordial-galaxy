#!/usr/bin/env bash
# Direct-source procurement watcher - daily extraction run (Linux cron).
# Separate cron entry from run_scanner.sh by design: this hits 5,308+
# individual government sites directly (not an aggregator API), and its
# per-run cost now scales with how many pages actually changed since the
# last check, not the full sample size -- see procurement_watch.py's
# run_extraction() new/changed filter (2026-09-13).
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
LOG_FILE="$LOG_DIR/procurement_watch_$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$LOG_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
  echo "venv python not found at $PYTHON_BIN" | tee -a "$LOG_FILE"
  exit 1
fi

cd "$PROJECT_ROOT"
"$PYTHON_BIN" -m observatory.procurement_watch extract --limit 100 >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# 30-day log trim, matching run_scanner.sh's convention.
find "$LOG_DIR" -name "procurement_watch_*.log" -mtime +30 -delete

exit $EXIT_CODE
