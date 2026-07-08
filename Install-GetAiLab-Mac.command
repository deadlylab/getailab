#!/bin/bash
# Double-click in Finder to install GetAiLab environment on macOS.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

osascript -e 'display notification "GetAiLab setup starting…" with title "GetAiLab"' 2>/dev/null || true

echo ""
echo "  GetAiLab macOS Setup"
echo "  Project: $ROOT"
echo ""

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ python3 not found."
    echo "   Install from https://www.python.org/downloads/macos/"
    echo "   Or: brew install python@3.11"
    read -r -p "Press Enter to close..."
    exit 1
fi

if [[ ! -d .venv ]] && command -v brew >/dev/null 2>&1; then
    read -r -p "Install python@3.11 via Homebrew if needed? [y/N] " brewpy
    if [[ "$brewpy" =~ ^[Yy] ]]; then
        brew install python@3.11 2>/dev/null || true
    fi
fi

PY="python3"
[[ -f .venv/bin/python ]] && PY=".venv/bin/python"

chmod +x scripts/bootstrap_env.py scripts/boot_services.py Install-GetAiLab-Mac.command Boot-GetAiLab-Mac.command 2>/dev/null || true
"$PY" scripts/bootstrap_env.py "$@"
RC=$?

echo ""
read -r -p "Press Enter to close this window..."
exit $RC