#!/usr/bin/env bash
# ==============================================================================
# PROJECT CHIMERA — SHUTDOWN (native stack)
# Stops all background lab, oracle, and scientist processes started by
# boot_chimera.sh. Does not affect Docker (use ./docker_chimera.sh down).
# ==============================================================================

echo "🛑 Stopping native Chimera agents..."

pkill -f 'python3 lab/app_lab' 2>/dev/null || true
pkill -f 'python3 scientists/app_' 2>/dev/null || true
pkill -f 'python3.*app_' 2>/dev/null || true
sleep 1

if pgrep -af 'app_lab|app_oracle|scientists/app_' >/dev/null 2>&1; then
    echo "⚠️  Some processes may still be running:"
    pgrep -af 'app_lab|app_oracle|scientists/app_' 2>/dev/null || true
    echo "   Try: pkill -9 -f 'python3.*app_'"
    exit 1
fi

if ss -tlnp 2>/dev/null | grep -qE ':50(2[4-9]|3[0-9]|4[0-0])\b'; then
    echo "⚠️  Ports 5024-5040 still in use (may be Docker or another project):"
    ss -tlnp 2>/dev/null | grep -E ':50(2[4-9]|3[0-9]|4[0-0])\b' || true
    echo "   Docker: ./docker_chimera.sh down"
    exit 1
fi

echo "✅ Native stack stopped. Ports 5024-5040 clear."