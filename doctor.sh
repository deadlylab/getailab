#!/usr/bin/env bash
# GetAiLab — one-command health check (active LAB_ID squad)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
RST='\033[0m'

ok()   { echo -e "${GRN}✓${RST} $*"; }
warn() { echo -e "${YLW}!${RST} $*"; }
bad()  { echo -e "${RED}✗${RST} $*"; }

echo "GetAiLab doctor — $(date '+%Y-%m-%d %H:%M')"
echo

# Python scientific stack
python3 - <<'PY' || warn "Scientific stack incomplete — run: pip install -r lab/requirements.txt"
import importlib
missing = []
for mod in ("numpy", "scipy", "matplotlib", "pandas", "sympy", "pyarrow"):
    try:
        importlib.import_module(mod)
    except ImportError:
        missing.append(mod)
if missing:
    raise SystemExit("missing: " + ", ".join(missing))
print("scientific stack OK (incl. pyarrow)")
PY
if [ $? -eq 0 ]; then ok "Scientific libraries (numpy, pandas, pyarrow, …)"; fi

# Ollama / LLM
if curl -sf "${LLM_ENDPOINT:-http://localhost:11434}/api/tags" >/dev/null 2>&1; then
  ok "Ollama reachable at ${LLM_ENDPOINT:-http://localhost:11434}"
else
  warn "Ollama not reachable — cloud model in .env may still work"
fi

# Squad + lab via CLI
if python3 run_chimera.py --status >/tmp/getailab_status.json 2>/dev/null; then
  ok "Service status written — see /tmp/getailab_status.json"
  python3 - <<'PY'
import json
from pathlib import Path
d = json.loads(Path("/tmp/getailab_status.json").read_text())
lab = d.get("lab", {})
ora = d.get("oracle", {})
print(f"  Lab: {lab.get('status', 'offline')}  libraries={lab.get('libraries', [])}")
print(f"  Oracle: {ora.get('status', 'offline')}")
offline = [k for k, v in d.items() if k not in ("lab", "oracle") and v.get("status") == "offline"]
if offline:
    print(f"  Scientists offline (sample): {', '.join(offline)}")
PY
else
  bad "run_chimera.py --status failed — boot squad: ./boot_example.sh"
fi

echo
echo "Fix hints:"
echo "  ./boot_example.sh              — start full squad"
echo "  pip install -r lab/requirements.txt   — fix pandas/pyarrow warnings"
echo "  ./docker.sh build && ./docker.sh up   — example lab in Docker"
echo "  python3 run_chimera.py --status"