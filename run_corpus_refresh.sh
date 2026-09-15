#!/usr/bin/env bash
# Weekly regulatory corpus refresh -- keeps FAR/DFARS (eCFR, current text),
# Executive Orders, and GAO reports up to date, then re-embeds. Companion to
# run_scanner.sh (daily opportunity scan). Jay's directive 2026-09-07: "obtain
# and keep up to date every law, rule, & order affecting our field."
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
LOG_FILE="$LOG_DIR/corpus_refresh_$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$LOG_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "ERROR: venv not found at $PYTHON_BIN - create venv and pip install requirements" >&2
    exit 1
fi

{
    echo "=== Corpus Refresh - $(date '+%Y-%m-%d %H:%M') ==="
} | tee "$LOG_FILE"

cd "$PROJECT_ROOT"
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8

# 35-day lookback on GAO (weekly cadence + buffer) -- cheap, re-ingesting an
# already-seen package is a no-op upsert, not wasted work.
GAO_START=$(date -d '35 days ago' +%Y-%m-%d)

RUN_STATUS=0
echo "--- FAR (eCFR, current) ---" | tee -a "$LOG_FILE"
"$PYTHON_BIN" -m observatory.ingest ecfr --part 52  --source far   2>&1 | tee -a "$LOG_FILE" || RUN_STATUS=1
echo "--- DFARS (eCFR, current) ---" | tee -a "$LOG_FILE"
"$PYTHON_BIN" -m observatory.ingest ecfr --part 252 --source dfars 2>&1 | tee -a "$LOG_FILE" || RUN_STATUS=1
echo "--- Executive Orders ---" | tee -a "$LOG_FILE"
"$PYTHON_BIN" -m observatory.ingest eo --limit 100                 2>&1 | tee -a "$LOG_FILE" || RUN_STATUS=1
echo "--- EO full-text fill ---" | tee -a "$LOG_FILE"
"$PYTHON_BIN" -m observatory.fulltext --source eo                  2>&1 | tee -a "$LOG_FILE" || RUN_STATUS=1
echo "--- GAO reports (since $GAO_START) ---" | tee -a "$LOG_FILE"
"$PYTHON_BIN" -m observatory.ingest gao --start "$GAO_START"       2>&1 | tee -a "$LOG_FILE" || RUN_STATUS=1
echo "--- Re-embed corpus_docs ---" | tee -a "$LOG_FILE"
"$PYTHON_BIN" -m observatory.embed_corpus                          2>&1 | tee -a "$LOG_FILE" || RUN_STATUS=1

{
    echo ""
    echo "=== Done: $(date '+%Y-%m-%d %H:%M') (exit $RUN_STATUS) ==="
} | tee -a "$LOG_FILE"

# Trim logs older than 90 days (corpus refresh is weekly, not daily -- keep more history)
find "$LOG_DIR" -maxdepth 1 -name "corpus_refresh_*.log" -mtime +90 -delete

exit "$RUN_STATUS"
