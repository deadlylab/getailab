#!/usr/bin/env bash
# Quick LLM connectivity check for native + Docker paths
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ -f .python-version ]] && command -v pyenv >/dev/null 2>&1; then
  export PATH="${HOME}/.pyenv/bin:${HOME}/.pyenv/shims:${PATH}"
  eval "$(pyenv init -)" 2>/dev/null || true
fi

echo "=== Ollama (host) ==="
if curl -sf --connect-timeout 3 http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "✅ localhost:11434"
  ss -tlnp 2>/dev/null | grep 11434 || true
else
  echo "❌ localhost:11434 — run: ollama serve"
fi

echo ""
echo "=== Ollama (Docker path) ==="
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  if docker run --rm --add-host=host.docker.internal:host-gateway getailab:latest \
      curl -sf --connect-timeout 3 http://host.docker.internal:11434/api/tags >/dev/null 2>&1; then
    echo "✅ host.docker.internal:11434 from container"
  else
    echo "❌ Docker cannot reach Ollama — run: ./scripts/ollama_for_docker.sh"
  fi
else
  echo "(docker not available — skip)"
fi

echo ""
echo "=== Python adapter (.env) ==="
python3 <<'PY'
import os
try:
    from dotenv import load_dotenv
    load_dotenv(".env")
except Exception:
    pass
from llm.adapter import create_default_adapter, get_env_provider_config
cfg = get_env_provider_config()
a = create_default_adapter()
info = a.get_info()
print(f"provider: {cfg.get('provider', 'ollama')}")
print(f"endpoint: {info.get('endpoint')}")
print(f"ready: {a.is_ready()}")
PY