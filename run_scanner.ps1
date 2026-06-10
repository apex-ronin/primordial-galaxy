# GovTech Hunter - Daily Scanner Runner
# Runs the full pipeline and writes a dated log to logs\
# Called by Windows Task Scheduler (task: GovTechHunterDaily)
# NOTE: Keep this file 100% ASCII. Task host is Windows PowerShell 5.1,
# which misreads UTF-8-no-BOM files as ANSI (em dashes become curly quotes
# and break string parsing). ASCII parses identically everywhere.

$ProjectRoot = $PSScriptRoot
$LogDir = Join-Path $ProjectRoot "logs"
$PythonExe = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$ExecutionDir = Join-Path $ProjectRoot "execution"
$LogFile = Join-Path $LogDir ("scan_" + (Get-Date -Format "yyyy-MM-dd_HHmm") + ".log")

# Ensure logs directory exists
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}

# Sanity checks
if (-not (Test-Path $PythonExe)) {
    Write-Host "ERROR: venv not found at $PythonExe - create venv and pip install requirements"
    exit 1
}

$EnvFile = Join-Path $ProjectRoot ".env"
$EnvContent = Get-Content $EnvFile -Raw -ErrorAction SilentlyContinue
if ($EnvContent -notmatch "ANTHROPIC_API_KEY=.+") {
    Write-Host "ERROR: ANTHROPIC_API_KEY not set in .env - pipeline will fall back to keywords only"
}

Write-Host "=== GovTech Hunter - $(Get-Date -Format 'yyyy-MM-dd HH:mm') ===" | Tee-Object -FilePath $LogFile
Write-Host "Log: $LogFile"
Write-Host ""

# Force UTF-8 for Python stdio. Under Task Scheduler (SYSTEM, no console)
# Python defaults to cp1252 and dies on Unicode output (charmap codec errors).
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

# Playwright browser location. The user-profile ms-playwright copy is
# virtualized inside the Claude Desktop MSIX container (invisible to SYSTEM).
# Real binaries live on G: - neutral, SYSTEM-visible, survives app uninstall.
$env:PLAYWRIGHT_BROWSERS_PATH = "G:\AI-Models\ms-playwright"

# Run pipeline
Push-Location $ExecutionDir
try {
    & $PythonExe main.py 2>&1 | Tee-Object -FilePath $LogFile -Append
} finally {
    Pop-Location
}

Write-Host ""
Write-Host "=== Done: $(Get-Date -Format 'yyyy-MM-dd HH:mm') ===" | Tee-Object -FilePath $LogFile -Append

# Trim logs older than 30 days
Get-ChildItem $LogDir -Filter "scan_*.log" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-30) } |
    Remove-Item -Force
