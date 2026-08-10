# set_mirror_secrets.ps1 -- push scanner API keys from local .env to the
# PRIVATE ops mirror's Actions secrets. Values never printed, never logged.
# ASCII-only (PS 5.1 em-dash trap, per STATE 2026-06-09 / 2026-06-20).

$ErrorActionPreference = 'Stop'
$repo = 'jsnnlsn-prog/primordial-galaxy'
$envFile = 'G:\repos\primordial-galaxy\.env'

# .env var name -> GitHub secret name (workflow maps these)
$map = @{
    'SAM_API_KEY'       = 'SAM_GOV_API'
    'VENICE_API_KEY'    = 'VENICE_API'
    'ANTHROPIC_API_KEY' = 'ANTHROPIC_API_KEY'
}

$vars = @{}
foreach ($line in Get-Content $envFile) {
    if ($line -match '^\s*([A-Z0-9_]+)\s*=\s*(.*)$') {
        $vars[$Matches[1]] = $Matches[2].Trim().Trim('"').Trim("'")
    }
}

Write-Host ("vars found in .env: " + ($vars.Keys -join ', '))

# Venice key may live under an alternate name
if (-not $vars['VENICE_API_KEY']) {
    foreach ($alt in 'VENICE_KEY','VENICE_API','VENICE_TOKEN','VENICE_API_TOKEN','VENICEAI_API_KEY') {
        if ($vars[$alt]) { $vars['VENICE_API_KEY'] = $vars[$alt]; Write-Host ("using {0} as VENICE_API_KEY" -f $alt); break }
    }
}

foreach ($envName in $map.Keys) {
    $secretName = $map[$envName]
    $val = $vars[$envName]
    if (-not $val) {
        Write-Host ("MISSING in .env: {0} (wanted for secret {1})" -f $envName, $secretName)
        continue
    }
    $val | gh secret set $secretName -R $repo
    Write-Host ("SET {0} from {1} (length {2})" -f $secretName, $envName, $val.Length)
}

Write-Host '--- secrets now on mirror ---'
gh secret list -R $repo
