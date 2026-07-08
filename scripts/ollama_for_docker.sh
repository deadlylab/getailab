#!/usr/bin/env bash
# ==============================================================================
# Restart Ollama so Docker containers can reach it via host.docker.internal
#
# Default Ollama binds 127.0.0.1 only — containers cannot connect.
# OLLAMA_HOST=0.0.0.0 listens on all interfaces (still only your LAN/docker bridge).
#
# Usage: ./scripts/ollama_for_docker.sh
# ==============================================================================

set -euo pipefail

echo "🧠 Configuring Ollama for Docker access (OLLAMA_HOST=0.0.0.0:11434)..."

if command -v systemctl >/dev/null 2>&1 && systemctl is-active ollama >/dev/null 2>&1; then
    echo "   Detected systemd ollama service — creating drop-in override..."
    sudo mkdir -p /etc/systemd/system/ollama.service.d
    printf '%s\n' '[Service]' 'Environment="OLLAMA_HOST=0.0.0.0:11434"' | sudo tee /etc/systemd/system/ollama.service.d/override.conf >/dev/null
    sudo systemctl daemon-reload
    sudo systemctl restart ollama
    echo "   Restarted via systemd."
else
    echo "   Stopping any running ollama process..."
    pkill -x ollama 2>/dev/null || true
    sleep 1
    export OLLAMA_HOST=0.0.0.0:11434
    echo "   Starting: OLLAMA_HOST=$OLLAMA_HOST ollama serve"
    nohup ollama serve > /tmp/ollama-docker.log 2>&1 &
    sleep 2
fi

echo ""
echo "   Host check:"
if curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
    echo "   ✅ localhost:11434 OK"
else
    echo "   ❌ localhost:11434 failed — check /tmp/ollama-docker.log or journalctl -u ollama"
    exit 1
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    if docker run --rm --add-host=host.docker.internal:host-gateway curlimages/curl:8.5.0 \
        -sf --connect-timeout 3 http://host.docker.internal:11434/api/tags >/dev/null 2>&1; then
        echo "   ✅ host.docker.internal:11434 OK from Docker"
    else
        echo "   ⚠️  Docker still cannot reach Ollama — check firewall or Docker network"
    fi
fi

echo ""
echo "✅ Ollama ready for docker compose loop"