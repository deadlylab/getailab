#!/usr/bin/env bash
# Boot forged lab: environmental
cd "$(dirname "$0")"
set -e

export LAB_ID="environmental"
export PERSONAS_YAML="personas/environmental_squad.yaml"
export ORACLE_PORT=5144
export LAB_PORT=5155
export ORACLE_URL="http://localhost:5144"
export LAB_URL="http://localhost:5155"

if [[ -f .env ]]; then
    set -a; source .env; set +a
fi
if [[ -f .env.environmental ]]; then
    set -a; source .env.environmental; set +a
fi

echo "🛑 Stopping prior environmental agents (this lab only)..."
pkill -f "scientists/forges/environmental/" 2>/dev/null || true
pkill -f "LAB_ID=environmental.*app_oracle" 2>/dev/null || true
pkill -f "LAB_ID=environmental.*app_lab" 2>/dev/null || true
fuser -k 5144/tcp 2>/dev/null || true
fuser -k 5155/tcp 2>/dev/null || true
sleep 1

mkdir -p logs
echo "⚙️  Lab sandbox :5155..."
LAB_ID=environmental LAB_PORT=5155 ORACLE_URL=http://localhost:5144 \
  python3 lab/app_lab.py > logs/environmental_lab.log 2>&1 &
sleep 2

echo "🔮 Oracle :5144..."
LAB_ID=environmental PERSONAS_YAML=personas/environmental_squad.yaml ORACLE_PORT=5144 \
  python3 scientists/app_oracle.py > logs/environmental_oracle.log 2>&1 &
sleep 2

echo "🧠 Squad (3 scientists)..."
    echo "  -> edmond_halley"
    LAB_ID=environmental PERSONAS_YAML=personas/environmental_squad.yaml python3 "scientists/forges/environmental/app_edmond_halley.py" > "logs/environmental_edmond_halley.log" 2>&1 &
    sleep 0.2
    echo "  -> other_scientific_achievements_beyond_weather_halley_made_significant_contributions_to_various_fields"
    LAB_ID=environmental PERSONAS_YAML=personas/environmental_squad.yaml python3 "scientists/forges/environmental/app_other_scientific_achievements_beyond_weather_halley_made_significant_contributions_to_various_fields.py" > "logs/environmental_other_scientific_achievements_beyond_weather_halley_made_significant_contributions_to_various_fields.log" 2>&1 &
    sleep 0.2
    echo "  -> navigation_in_1701_he_published_the_first_magnetic_declination_charts_isogonic_lines_for_the_atlantic_and_pacific_oceans_to_aid_maritime_navigation"
    LAB_ID=environmental PERSONAS_YAML=personas/environmental_squad.yaml python3 "scientists/forges/environmental/app_navigation_in_1701_he_published_the_first_magnetic_declination_charts_isogonic_lines_for_the_atlantic_and_pacific_oceans_to_aid_maritime_navigation.py" > "logs/environmental_navigation_in_1701_he_published_the_first_magnetic_declination_charts_isogonic_lines_for_the_atlantic_and_pacific_oceans_to_aid_maritime_navigation.log" 2>&1 &
    sleep 0.2

echo "✅ environmental online."
echo "   Oracle :5144  ·  Lab :5155  ·  Vault: data/labs/environmental/"
echo ""
echo "   export LAB_ID=environmental"
echo "   export PERSONAS_YAML=personas/environmental_squad.yaml"
echo "   python3 run_chimera.py"
