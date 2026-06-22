# register_boot_task.ps1 -- RUN THIS ELEVATED (Run as Administrator).
# Registers LMStudioServerAtBoot: starts the LM Studio server + CPU-preloads gemma
# at system startup so the 0700 unattended scan has the sovereign-local tier even
# when Jay is logged out. CPU-only (via start_local_llm.ps1) keeps the display GPU free.
# ASCII-only on purpose: PS 5.1 reads UTF-8-no-BOM as ANSI and chokes on em-dashes.

$elevated = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator)
if (-not $elevated) {
    Write-Host "NOT ELEVATED. Close this and re-run in an Administrator PowerShell." -ForegroundColor Red
    return
}

$arg = '-NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "G:\repos\primordial-galaxy\start_local_llm.ps1"'
$action    = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument $arg
$trigger   = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings  = New-ScheduledTaskSettingsSet -StartWhenAvailable

try {
    Register-ScheduledTask -TaskName 'LMStudioServerAtBoot' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force -ErrorAction Stop | Out-Null
    $t = Get-ScheduledTask -TaskName 'LMStudioServerAtBoot'
    Write-Host ("OK - registered. state=" + $t.State + " runas=" + $t.Principal.UserId + " trigger=AtStartup") -ForegroundColor Green
    Write-Host "Verify after next reboot (while logged OUT, then in): run 'lms ps' -- gemma-4-e4b should be loaded." -ForegroundColor Green
} catch {
    Write-Host ("FAILED: " + $_.Exception.Message) -ForegroundColor Red
}
