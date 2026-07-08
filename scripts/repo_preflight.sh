#!/usr/bin/env bash
# Pre-push gate — catches secrets, bulk artifacts, and broken imports.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RED='\033[0;31m'
GRN='\033[0;32m'
YLW='\033[0;33m'
RST='\033[0m'
FAIL=0

ok()   { echo -e "${GRN}✓${RST} $*"; }
warn() { echo -e "${YLW}!${RST} $*"; }
bad()  { echo -e "${RED}✗${RST} $*"; FAIL=1; }

echo "GetAiLab repo preflight"
echo

# Required files
for f in README.md LICENSE .gitignore .env.example requirements.txt CONTRIBUTING.md SECURITY.md; do
  [[ -f "$f" ]] && ok "found $f" || bad "missing $f"
done

[[ -f docs/REPOSITORY_CHECKLIST.md ]] && ok "found docs/REPOSITORY_CHECKLIST.md" || bad "missing docs/REPOSITORY_CHECKLIST.md"
[[ -f .github/workflows/ci.yml ]] && ok "found CI workflow" || bad "missing .github/workflows/ci.yml"

# Secret / env leaks in working tree (staged or not)
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  if git ls-files --error-unmatch .env >/dev/null 2>&1; then
    bad ".env is tracked by git — run: git rm --cached .env"
  else
    ok ".env not tracked"
  fi
  TRACKED_SECRETS=$(git ls-files '.env.*' 2>/dev/null | grep -v '.env.example' || true)
  if [[ -n "$TRACKED_SECRETS" ]]; then
    bad "tracked env files: $TRACKED_SECRETS"
  else
    ok "no tracked .env.* secrets"
  fi
  TRACKED_DB=$(git ls-files '*.db' 2>/dev/null || true)
  if [[ -n "$TRACKED_DB" ]]; then
    bad "tracked database files: $TRACKED_DB"
  else
    ok "no tracked *.db"
  fi
  BIG_REPORTS=$(git ls-files 'loop_*_report.md' 2>/dev/null | wc -l)
  if [[ "$BIG_REPORTS" -gt 0 ]]; then
    bad "$BIG_REPORTS loop_*_report.md files tracked — should be gitignored"
  else
    ok "no loop reports in index"
  fi
else
  warn "not a git repo yet — run: git init -b main"
fi

# Local files that must never be pushed (even if git not init)
[[ -f .env ]] && warn ".env exists locally (OK if gitignored)" || ok "no local .env file"
for pattern in oracle_last_payload.json chimera_lab.db; do
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1 && git ls-files --error-unmatch "$pattern" >/dev/null 2>&1; then
    bad "$pattern is tracked"
  fi
done

# Rough size check — scientists vault bulk
VAULT_MB=$(du -sm data/labs/*/scientists 2>/dev/null | awk '{s+=$1} END {print s+0}')
if [[ "$VAULT_MB" -gt 50 ]]; then
  if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    VAULT_TRACKED=$(git ls-files 'data/labs/*/scientists/' 2>/dev/null | wc -l)
    if [[ "$VAULT_TRACKED" -gt 0 ]]; then
      bad "~${VAULT_MB}MB vault under data/labs/*/scientists/ and $VAULT_TRACKED files tracked"
    else
      ok "vault present locally (~${VAULT_MB}MB) but not tracked"
    fi
  else
    warn "local vault ~${VAULT_MB}MB — ensure .gitignore before first commit"
  fi
else
  ok "no large tracked vault detected"
fi

# Python import smoke (no network / no boot)
python3 - <<'PY' || bad "Python import check failed"
import importlib
import sys
from pathlib import Path
root = Path(".")
sys.path.insert(0, str(root))
for mod in ("getailab", "getailab.lab_config", "getailab.resonance", "getailab.integrity.verify"):
    importlib.import_module(mod)
print("imports OK")
PY
[[ $? -eq 0 ]] && ok "core Python imports" || true

# Syntax compile key entrypoints
python3 -m py_compile run_chimera.py uni_lab.py 2>/dev/null && ok "entrypoint syntax" || bad "syntax error in run_chimera.py or uni_lab.py"

echo
if [[ $FAIL -eq 0 ]]; then
  echo -e "${GRN}Preflight PASSED${RST} — safe to commit and push"
  exit 0
else
  echo -e "${RED}Preflight FAILED${RST} — fix items above before push"
  exit 1
fi