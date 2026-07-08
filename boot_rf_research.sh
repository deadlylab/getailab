#!/usr/bin/env bash
# Boot forged lab: rf_research
cd "$(dirname "$0")"
set -e

export LAB_ID="rf_research"
export PERSONAS_YAML="personas/rf_research_squad.yaml"
export ORACLE_PORT=5124
export LAB_PORT=5135
export ORACLE_URL="http://localhost:5124"
export LAB_URL="http://localhost:5135"

if [[ -f .env ]]; then
    set -a; source .env; set +a
fi
if [[ -f .env.rf_research ]]; then
    set -a; source .env.rf_research; set +a
fi

echo "🛑 Stopping prior rf_research agents (this lab only)..."
pkill -f "scientists/forges/rf_research/" 2>/dev/null || true
pkill -f "LAB_ID=rf_research.*app_oracle" 2>/dev/null || true
pkill -f "LAB_ID=rf_research.*app_lab" 2>/dev/null || true
fuser -k 5124/tcp 2>/dev/null || true
fuser -k 5135/tcp 2>/dev/null || true
sleep 1

mkdir -p logs
echo "⚙️  Lab sandbox :5135..."
LAB_ID=rf_research LAB_PORT=5135 ORACLE_URL=http://localhost:5124 \\
  python3 lab/app_lab.py > logs/rf_research_lab.log 2>&1 &
sleep 2

echo "🔮 Oracle :5124..."
LAB_ID=rf_research PERSONAS_YAML=personas/rf_research_squad.yaml ORACLE_PORT=5124 \
  python3 scientists/app_oracle.py > logs/rf_research_oracle.log 2>&1 &
sleep 2

echo "🧠 Squad (2 scientists)..."
    echo "  -> tesla"
    LAB_ID=rf_research PERSONAS_YAML=personas/rf_research_squad.yaml python3 "scientists/forges/rf_research/app_tesla.py" > "logs/rf_research_tesla.log" 2>&1 &
    sleep 0.2
    echo "  -> shannon"
    LAB_ID=rf_research PERSONAS_YAML=personas/rf_research_squad.yaml python3 "scientists/forges/rf_research/app_shannon.py" > "logs/rf_research_shannon.log" 2>&1 &
    sleep 0.2

echo "✅ rf_research online."
echo "   Oracle :5124  ·  Lab :5135  ·  Vault: data/labs/rf_research/"
echo ""
echo "   export LAB_ID=rf_research"
echo "   export PERSONAS_YAML=personas/rf_research_squad.yaml"
echo "   python3 run_chimera.py"
