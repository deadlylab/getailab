#!/usr/bin/env bash
# Stop forged lab: environmental
cd "$(dirname "$0")"
set +e
echo "🛑 Stopping environmental..."

if [[ -f ".env.environmental" ]]; then
    set -a; source ".env.environmental"; set +a
fi

pkill -f "scientists/forges/environmental/" 2>/dev/null
pkill -f "LAB_ID=environmental.*app_oracle" 2>/dev/null
pkill -f "LAB_ID=environmental.*app_lab" 2>/dev/null

if [[ -n "${LAB_PORT:-}" ]]; then
    fuser -k "${LAB_PORT}/tcp" 2>/dev/null
fi
if [[ -n "${ORACLE_PORT:-}" ]]; then
    fuser -k "${ORACLE_PORT}/tcp" 2>/dev/null
fi

echo "✅ environmental stopped."
