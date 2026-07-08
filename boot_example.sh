#!/usr/bin/env bash
# Boot the shipped example lab (2 scientists + Oracle + sandbox).
# Forge your own: python3 scripts/create_lab.py
set -euo pipefail
cd "$(dirname "$0")"

export LAB_ID=example
export PERSONAS_YAML=personas/example_squad.yaml
export ORACLE_PORT=5124
export LAB_PORT=5135
export ORACLE_URL=http://localhost:5124
export LAB_URL=http://localhost:5135

if [[ -f .env ]]; then set -a; source .env; set +a; fi
if [[ -f .env.example ]]; then set -a; source .env.example; set +a; fi

echo ""
echo "  ╔══════════════════════════════════════════════════════════════════════╗"
echo "  ║   GET AILAB — EXAMPLE LAB (builder starter)                           ║"
echo "  ╚══════════════════════════════════════════════════════════════════════╝"
echo ""

pkill -f "scientists/forges/example/" 2>/dev/null || true
fuser -k 5124/tcp 5135/tcp 5125/tcp 5126/tcp 2>/dev/null || true
sleep 1
mkdir -p logs

echo "⚙️  Lab sandbox :5135..."
LAB_ID=example LAB_PORT=5135 ORACLE_URL=http://localhost:5124 \
  python3 lab/app_lab.py > logs/example_lab.log 2>&1 &
sleep 2

echo "🔮 Oracle :5124..."
LAB_ID=example PERSONAS_YAML=personas/example_squad.yaml ORACLE_PORT=5124 \
  python3 scientists/app_oracle.py > logs/example_oracle.log 2>&1 &
sleep 2

echo "🧠 Squad (researcher, critic)..."
LAB_ID=example PERSONAS_YAML=personas/example_squad.yaml \
  python3 scientists/forges/example/app_researcher.py > logs/example_researcher.log 2>&1 &
sleep 0.2
LAB_ID=example PERSONAS_YAML=personas/example_squad.yaml \
  python3 scientists/forges/example/app_critic.py > logs/example_critic.log 2>&1 &

echo ""
echo "✅ Example lab online — Oracle :5124 · Lab/Dashboard :5135"
echo "   python3 run_chimera.py --status"
echo "   python3 scripts/create_lab.py   # forge your own division"
echo ""