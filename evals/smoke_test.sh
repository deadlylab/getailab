#!/usr/bin/env bash
# Quick smoke before external sends. Exit 1 on hard fail.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== GetAiLab smoke test ==="

echo "[1/3] Status check..."
STATUS_JSON=$(python3 run_chimera.py --status 2>/dev/null) || {
  echo "FAIL: run_chimera.py --status failed"
  exit 1
}

HEALTHY=$(echo "$STATUS_JSON" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(sum(1 for k,v in d.items() if isinstance(v,dict) and v.get('status')=='healthy' and k not in ('lab','oracle')))
")

echo "    Scientists healthy: $HEALTHY/10"
if [[ "$HEALTHY" -lt 10 ]]; then
  echo "WARN: squad not full — run ./boot_chimera.sh before peer review sends"
fi

echo "[2/3] Collaborative review dry-run..."
python3 scripts/collaborative_review.py --dry-run --text "smoke test" -q "ok?" >/dev/null

echo "[3/3] Oracle health..."
curl -sf http://localhost:5024/health >/dev/null || {
  echo "WARN: Oracle not reachable on :5024"
}

echo "=== Smoke complete ==="