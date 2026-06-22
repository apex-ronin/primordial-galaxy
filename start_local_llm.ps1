# start_local_llm.ps1 -- bring up the sovereign-local LLM tier.
# ASCII-only on purpose: PS 5.1 reads UTF-8-no-BOM as ANSI and chokes on em-dashes.
#
# Two profiles, because the right device depends on the session:
#   LOGON  (user jnel9, display active): GPU split -- partial offload + capped
#          context gives acceleration while leaving VRAM for the monitor.
#          The RX580 is the display GPU; full offload + 128k context drops the screen.
#   BOOT   (SYSTEM, session 0): CPU-only. GPU/Vulkan is unreliable in session 0,
#          so the 0700 unattended scan stays on CPU (gemma-4-e4b is small enough).
#
# Params:
#   -GpuOffload    "off" (CPU) | "max" | a 0..1 ratio. Default off (safe for boot).
#   -ContextLength tokens. Default 8192 (VRAM-safe at 0.5 offload: ~4.3GB of 8GB).
#   -Reload        force unload+reload (logon uses this to flip a CPU boot-load to GPU).
#
# Wired by:
#   LMStudioServerAtLogon -> ... start_local_llm.ps1 -GpuOffload 0.5 -ContextLength 8192 -Reload
#   LMStudioServerAtBoot  -> ... start_local_llm.ps1   (defaults = CPU-only)
param(
    [string]$GpuOffload = "off",
    [int]$ContextLength = 8192,
    [switch]$Reload
)
$ErrorActionPreference = 'SilentlyContinue'
$lms   = "C:\Users\jnel9\.lmstudio\bin\lms.exe"
$model = "google/gemma-4-e4b"

& $lms server start | Out-Null
Start-Sleep -Seconds 5

$loaded = ((& $lms ps 2>&1 | Out-String) -match [regex]::Escape($model))
if ($Reload -and $loaded) {
    & $lms unload --all | Out-Null
    $loaded = $false
}
if (-not $loaded) {
    & $lms load $model --gpu $GpuOffload --context-length $ContextLength -y | Out-Null
}
