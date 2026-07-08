#!/usr/bin/env bash
# ==============================================================================
# GetAiLab — Linux first-time setup (double-click in file manager or: ./Install-...)
# Creates .venv, installs deps, seeds .env, checks Ollama.
# ==============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

echo ""
echo "  GetAiLab Linux Setup"
echo "  Project: $ROOT"
echo ""

# Optional system packages (asks for sudo password)
if ! python3 -c "import venv" 2>/dev/null; then
    echo "⚠️  python3-venv not available."
    if [[ -t 0 ]] && read -r -p "Install python3-venv with sudo apt? [Y/n] " ans; then
        [[ -z "$ans" || "$ans" =~ ^[Yy] ]] && {
            echo "🔐 Asking sudo for python3-venv..."
            sudo apt-get update
            sudo apt-get install -y python3-venv python3-pip curl
        }
    fi
fi

if [[ -f .python-version ]] && command -v pyenv >/dev/null 2>&1; then
    export PATH="${HOME}/.pyenv/bin:${HOME}/.pyenv/shims:${PATH}"
    eval "$(pyenv init -)" 2>/dev/null || true
    echo "🐍 pyenv: $(python3 --version 2>/dev/null)"
fi

if [[ ! -f .venv/bin/python ]] && [[ -t 0 ]]; then
    read -r -p "Run full pyenv Python 3.11 setup (./setup_python.sh)? [y/N] " pysetup
    if [[ "$pysetup" =~ ^[Yy] ]]; then
        if [[ -x ./setup_python.sh ]]; then
            ./setup_python.sh
        fi
    fi
fi

PY="python3"
if [[ -f .venv/bin/python ]]; then
    PY=".venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
    PY="python3.11"
fi

chmod +x scripts/bootstrap_env.py scripts/boot_services.py 2>/dev/null || true
exec "$PY" scripts/bootstrap_env.py "$@"