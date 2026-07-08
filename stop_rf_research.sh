#!/usr/bin/env bash
# Stop forged lab: rf_research
cd "$(dirname "$0")"
set +e
echo "🛑 Stopping rf_research..."

if [[ -f ".env.rf_research" ]]; then
    set -a; source ".env.rf_research"; set +a
fi

pkill -f "scientists/forges/rf_research/" 2>/dev/null
pkill -f "LAB_ID=rf_research.*app_oracle" 2>/dev/null
pkill -f "LAB_ID=rf_research.*app_lab" 2>/dev/null

if [[ -n "${LAB_PORT:-}" ]]; then
    fuser -k "${LAB_PORT}/tcp" 2>/dev/null
fi
if [[ -n "${ORACLE_PORT:-}" ]]; then
    fuser -k "${ORACLE_PORT}/tcp" 2>/dev/null
fi

echo "✅ rf_research stopped."