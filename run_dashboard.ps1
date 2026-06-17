# Primordial Observatory - dashboard launcher
# Starts the live FastAPI dashboard over data\primordial.db
# NOTE: Keep this file 100% ASCII (Windows PowerShell 5.1 misreads UTF-8-no-BOM).
#
# Usage:   .\run_dashboard.ps1            (defaults to port 8787)
#          .\run_dashboard.ps1 -Port 9000
# Then open http://127.0.0.1:8787 in a browser.

param(
    [int]$Port = 8787,
    [string]$BindHost = "127.0.0.1"
)

$ProjectRoot = $PSScriptRoot
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: venv not found at $PythonExe - create venv and pip install requirements"
    exit 1
}

$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "=== Primordial Observatory ==="
Write-Host "Dashboard:  http://$($BindHost):$Port"
Write-Host "API docs:   http://$($BindHost):$Port/api/docs"
Write-Host "DB:         $(Join-Path $ProjectRoot 'data\primordial.db')"
Write-Host "Ctrl+C to stop."
Write-Host ""

# Run from repo root so the observatory package imports cleanly.
Push-Location $ProjectRoot
try {
    & $PythonExe -m uvicorn observatory.server:app --host $BindHost --port $Port
} finally {
    Pop-Location
}
