# GetAiLab — Windows boot (Chimera squad + Commander Console)
$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "  GetAiLab Windows Boot"
Write-Host ""

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $py = $venvPy
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $py = "py -3"
} else {
    $py = "python"
}

if (-not (Test-Path $venvPy) -and -not (Test-Path (Join-Path $Root ".env"))) {
    Write-Host "📦 First run — running setup..."
    & $py "$Root\scripts\bootstrap_env.py" --non-interactive --skip-playwright
}

if (Test-Path (Join-Path $Root ".env")) {
    Get-Content (Join-Path $Root ".env") | ForEach-Object {
        if ($_ -match '^\s*([^#=]+)=(.*)$') {
            [System.Environment]::SetEnvironmentVariable($matches[1].Trim(), $matches[2].Trim(), "Process")
        }
    }
}

& $py "$Root\scripts\lab_launcher.py" @args
Read-Host "Press Enter to exit"