#!/usr/bin/env bash
# GovTech Hunter - Daily Scanner Runner (Linux equivalent of run_scanner.ps1)
# Runs the full pipeline and writes a dated log to logs/.
# Called by cron (crontab -l on this box) -- see CLAUDE.md Session Protocol.
set -uo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
PYTHON_BIN="$PROJECT_ROOT/.venv/bin/python"
EXECUTION_DIR="$PROJECT_ROOT/execution"
LOG_FILE="$LOG_DIR/scan_$(date +%Y-%m-%d_%H%M).log"

mkdir -p "$LOG_DIR"

if [ ! -x "$PYTHON_BIN" ]; then
    echo "ERROR: venv not found at $PYTHON_BIN - create venv and pip install requirements" >&2
    exit 1
fi

if ! grep -q "^ANTHROPIC_API_KEY=.\+" "$PROJECT_ROOT/.env" 2>/dev/null; then
    echo "ERROR: ANTHROPIC_API_KEY not set in .env - pipeline will fall back to keywords only" >&2
fi

{
    echo "=== GovTech Hunter - $(date '+%Y-%m-%d %H:%M') ==="
    echo "Log: $LOG_FILE"
    echo ""
} | tee "$LOG_FILE"

export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
# Tell the Observatory recorder which log file this run wrote to, so the
# dashboard can deep-link from a run record to its raw log (mirrors run_scanner.ps1).
export SCAN_LOG_PATH="$LOG_FILE"

pushd "$EXECUTION_DIR" > /dev/null
"$PYTHON_BIN" main.py 2>&1 | tee -a "$LOG_FILE"
RUN_STATUS=${PIPESTATUS[0]}
popd > /dev/null

{
    echo ""
    echo "=== Done: $(date '+%Y-%m-%d %H:%M') (exit $RUN_STATUS) ==="
} | tee -a "$LOG_FILE"

# Trim logs older than 30 days
find "$LOG_DIR" -maxdepth 1 -name "scan_*.log" -mtime +30 -delete

exit "$RUN_STATUS"
