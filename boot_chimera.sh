#!/usr/bin/env bash
# ==============================================================================
# PROJECT CHIMERA - IGNITION SWITCH (Unix/macOS/Linux)
# Boots all agents, the lab, and drops into the Commander Console.
# For Windows: use "python run_chimera.py" (V4 multi-platform CLI).
# Cross-platform primary entry: python run_chimera.py --chat | --web | etc.
# Docker also available (see Dockerfile + docker-compose.yml).
# ==============================================================================

echo ""
echo "  ╔══════════════════════════════════════════════════════════════════════╗"
echo "  ║   ⚗️  PROJECT CHIMERA — IGNITION SEQUENCE                             ║"
echo "  ║   GetAiLab · Multi-Agent Research Laboratory                          ║"
echo "  ╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Use project-local Python 3.11 via pyenv when .python-version exists (see setup_python.sh)
if [[ -f .python-version ]] && command -v pyenv >/dev/null 2>&1; then
    export PATH="${HOME}/.pyenv/bin:${HOME}/.pyenv/shims:${PATH}"
    eval "$(pyenv init -)" 2>/dev/null || true
    echo "🐍 Python: $(python3 --version 2>/dev/null) ($(command -v python3))"
fi

# Prefer project .venv when present (Install-GetAiLab-* / bootstrap_env.py)
if [[ -f .venv/bin/python ]]; then
    PYTHON=".venv/bin/python"
elif [[ -f .venv/Scripts/python.exe ]]; then
    PYTHON=".venv/Scripts/python.exe"
else
    PYTHON="python3"
fi
echo "🐍 Runtime: $($PYTHON --version 2>/dev/null) ($PYTHON)"

echo "🧹 Clearing out any old ghost processes..."
pkill -f "python3.*app_" || true
pkill -f "python.*app_" || true
sleep 1

# Ensure API Key is loaded
if [ -f .env ]; then
    echo "🔑 Loading environment from .env..."
    set -a
    source .env
    set +a
fi

# LLM provider alert — shows what the squad will actually use
echo ""
echo "🧠 LLM BACKEND CHECK"
"$PYTHON" << 'PYEOF'
import os
import sys

try:
    from dotenv import load_dotenv
    load_dotenv(".env")
except Exception:
    pass

from llm.adapter import get_env_provider_config, create_default_adapter

cfg = get_env_provider_config()
explicit = os.getenv("LLM_PROVIDER", "").strip() or "(not set — defaulting to ollama)"
provider = cfg.get("provider", "ollama")
model = cfg.get("model") or "(provider default)"
code = cfg.get("code_model") or "(provider default)"
vision = cfg.get("vision_model") or "(provider default)"
endpoint = cfg.get("endpoint") or "(provider default)"

print(f"  LLM_PROVIDER in .env : {explicit}")
print(f"  Resolved backend     : {provider}")
print(f"  Chat model           : {model}")
print(f"  Code model           : {code}")
print(f"  Vision model         : {vision}")
if endpoint and endpoint != "(provider default)":
    print(f"  Endpoint             : {endpoint}")

adapter = create_default_adapter()
info = adapter.get_info()
ready = adapter.is_ready()
status = "READY" if ready else "NOT REACHABLE"
print(f"  Health               : {status}")
print(f"  Vision support       : {'yes' if adapter.supports_vision() else 'no'}")

if not ready:
    if provider == "ollama":
        print()
        print("  ⚠️  Ollama not reachable. Start it: ollama serve")
        print("     Or set LLM_PROVIDER=openai|google|anthropic in .env")
    elif provider in ("google", "openai", "anthropic"):
        key_env = {"google": "GOOGLE_API_KEY", "openai": "OPENAI_API_KEY", "anthropic": "ANTHROPIC_API_KEY"}.get(provider, "API key")
        if not cfg.get("api_key"):
            print()
            print(f"  ⚠️  No {key_env} found. Add it to .env or switch LLM_PROVIDER=ollama")
    print("  See .env.example for full configuration options.")
elif provider == "ollama" and not os.getenv("LLM_PROVIDER"):
    print()
    print("  ℹ️  Using local Ollama (default). Set LLM_PROVIDER=google etc. to use a cloud API.")
print()
PYEOF

# Create a logs directory so we aren't flying blind
mkdir -p logs
echo "📁 Background logs will be saved to the /logs directory."

echo "⚙️  Booting the Live Research Lab..."
"$PYTHON" lab/app_lab.py > logs/app_lab.log 2>&1 &
sleep 2

echo "🔮 Booting Oracle (Agora Database)..."
"$PYTHON" scientists/app_oracle.py > logs/app_oracle.log 2>&1 &
sleep 2

echo "🧠 Booting the Scientist Squad (personas from chimera_squad.yaml via loader)..."
for script in scientists/app_*.py; do
    if [[ "$script" != *"app_oracle.py"* ]]; then
        agent_name=$(basename "$script" .py)
        echo "  -> Starting $agent_name"
        "$PYTHON" "$script" > "logs/${agent_name}.log" 2>&1 &
    fi
done

echo "📚 Library vault: data/labs/chimera/ (auto-archive on loop synthesis)"
echo "✅ All systems nominal. Lab, Oracle, and squad online."
echo ""
echo "  ┌──────────────────────────────────────────────────────────────────────┐"
echo "  │  Services:  Lab :5035  ·  Oracle :5024  ·  Scientists :5025-5040      │"
echo "  │  Dashboard: http://localhost:5035                                    │"
echo "  │  Next: Commander Console — pick loop, explore, beef-up, or chat      │"
echo "  └──────────────────────────────────────────────────────────────────────┘"
echo ""
sleep 1

# Launch the Commander Console
echo "🚀 Launching Commander Console..."
"$PYTHON" run_chimera.py