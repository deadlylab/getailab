#!/usr/bin/env bash
# ==============================================================================
# GetAiLab — Linux boot (setup if needed, then ignite Chimera squad)
# ==============================================================================
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY="python3"
if [[ -f .venv/bin/python ]]; then
    PY=".venv/bin/python"
fi

if [[ ! -f .venv/bin/python ]] && [[ ! -f .env ]]; then
    echo "📦 First run — running setup..."
    chmod +x Install-GetAiLab-Linux.sh 2>/dev/null || true
    ./Install-GetAiLab-Linux.sh --non-interactive --skip-playwright || true
fi

if [[ -f .env ]]; then
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
fi

chmod +x scripts/lab_launcher.py scripts/lab_ops.py 2>/dev/null || true
exec "$PY" scripts/lab_launcher.py "$@"