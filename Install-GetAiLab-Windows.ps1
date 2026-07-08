# GetAiLab — Windows first-time setup
# Run: right-click → Run with PowerShell, or double-click Install-GetAiLab-Windows.bat
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "  GetAiLab Windows Setup"
Write-Host "  Project: $Root"
Write-Host ""

function Find-Python {
    foreach ($cmd in @("py -3.11", "py -3.12", "py -3", "python", "python3")) {
        try {
            $parts = $cmd -split " "
            $exe = $parts[0]
            $args = @()
            if ($parts.Length -gt 1) { $args = $parts[1..($parts.Length-1)] }
            $args += @("-c", "import sys; assert sys.version_info[:2] >= (3,10)")
            & $exe @args 2>$null
            if ($LASTEXITCODE -eq 0) { return $cmd }
        } catch {}
    }
    return $null
}

$pyCmd = Find-Python
if (-not $pyCmd) {
    Write-Host "❌ Python 3.10+ not found."
    Write-Host "   Download: https://www.python.org/downloads/windows/"
    Write-Host "   Check 'Add python.exe to PATH' during install."
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "🐍 Using: $pyCmd"

# Optional: winget install Ollama
$installOllama = Read-Host "Install Ollama via winget if missing? [y/N]"
if ($installOllama -match "^[Yy]") {
    try {
        winget install --id Ollama.Ollama -e --accept-source-agreements --accept-package-agreements
    } catch {
        Write-Host "⚠️  winget Ollama install skipped — install manually from https://ollama.com"
    }
}

$venvPy = Join-Path $Root ".venv\Scripts\python.exe"
if (Test-Path $venvPy) {
    $bootstrapPy = $venvPy
} else {
    $bootstrapPy = $pyCmd
}

& $bootstrapPy "$Root\scripts\bootstrap_env.py"
$rc = $LASTEXITCODE
Read-Host "Press Enter to exit"
exit $rc