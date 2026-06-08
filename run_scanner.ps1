# GovTech Hunter — Daily Scanner Runner
# Runs the full pipeline and writes a dated log to logs\
# Called by Windows Task Scheduler (task: GovTechHunterDaily)

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
    Write-Host "ERROR: venv not found at $PythonExe — run: python -m venv .venv && .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

$EnvFile = Join-Path $ProjectRoot ".env"
$EnvContent = Get-Content $EnvFile -Raw -ErrorAction SilentlyContinue
if ($EnvContent -notmatch "ANTHROPIC_API_KEY=.+") {
    Write-Host "ERROR: ANTHROPIC_API_KEY not set in .env — pipeline will fall back to keywords only"
}

Write-Host "=== GovTech Hunter — $(Get-Date -Format 'yyyy-MM-dd HH:mm') ===" | Tee-Object -FilePath $LogFile
Write-Host "Log: $LogFile"
Write-Host ""

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
