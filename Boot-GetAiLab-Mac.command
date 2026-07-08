#!/bin/bash
# Double-click in Finder to boot Project Chimera on macOS.
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

osascript -e 'display notification "Igniting Chimera squad…" with title "GetAiLab"' 2>/dev/null || true

PY="python3"
[[ -f .venv/bin/python ]] && PY=".venv/bin/python"

if [[ ! -f .venv/bin/python ]] && [[ ! -f .env ]]; then
    echo "📦 First run — running setup..."
    "$PY" scripts/bootstrap_env.py --non-interactive --skip-playwright || true
fi

if [[ -f .env ]]; then
    set -a
    # shellcheck source=/dev/null
    source .env
    set +a
fi

chmod +x scripts/lab_launcher.py scripts/lab_ops.py 2>/dev/null || true
"$PY" scripts/lab_launcher.py "$@"
RC=$?

echo ""
read -r -p "Press Enter to close this window..."
exit $RC