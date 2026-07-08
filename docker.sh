#!/usr/bin/env bash
# GetAiLab — Docker helper (example lab)
#
# Usage:
#   ./docker.sh build          # build image
#   ./docker.sh up             # full example lab (oracle + lab + 2 scientists)
#   ./docker.sh minimal        # dashboard + oracle only
#   ./docker.sh down           # stop stack
#   ./docker.sh clean          # stop + remove orphans
#   ./docker.sh status         # probe health endpoints
#   ./docker.sh logs [svc]     # tail logs (default: lab)
#   ./docker.sh cli            # interactive Commander chat
#   ./docker.sh loop           # full dialectic loop in container
#
# Dashboard: http://localhost:${LAB_HOST_PORT:-5135}

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

COMPOSE="docker compose"
IMAGE="getailab:latest"

die() { echo "❌ $*" >&2; exit 1; }

require_docker() {
    command -v docker >/dev/null 2>&1 || die "docker not found — install Docker first."
    $COMPOSE version >/dev/null 2>&1 || die "docker compose not available."
}

load_env() {
    if [[ ! -f .env ]]; then
        echo "⚠️  No .env — copying from .env.example"
        cp .env.example .env
    fi
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
}

ports() {
    LAB_PORT="${LAB_HOST_PORT:-5135}"
    ORACLE_PORT="${ORACLE_HOST_PORT:-5124}"
    RESEARCHER_PORT="${RESEARCHER_HOST_PORT:-5125}"
    CRITIC_PORT="${CRITIC_HOST_PORT:-5126}"
}

check_llm_from_docker() {
    local provider="${LLM_PROVIDER:-ollama}"
    provider="${provider,,}"
    if [[ -n "$provider" && "$provider" != "ollama" && "$provider" != "auto" ]]; then
        echo "🧠 LLM: cloud provider ($provider) — skipping Ollama Docker check"
        return 0
    fi

    local endpoint="${LLM_ENDPOINT:-http://host.docker.internal:11434}"
    echo "🧠 Checking LLM from inside Docker ($endpoint) ..."

    if docker run --rm --add-host=host.docker.internal:host-gateway getailab:latest \
        curl -sf --connect-timeout 4 "${endpoint%/}/api/tags" >/dev/null 2>&1; then
        echo "✅ Ollama reachable from containers"
        return 0
    fi

    echo ""
    echo "❌ LLM NOT REACHABLE from Docker — loops will fail."
    echo ""
    echo "   Fix: ./scripts/ollama_for_docker.sh"
    echo "   Or:  set LLM_PROVIDER=openai (etc.) in .env"
    echo "   Or:  ./boot_example.sh for native localhost Ollama"
    echo ""
    die "Start Ollama for Docker first."
}

probe() {
    local url="$1" label="$2"
    if curl -sf "$url" >/dev/null 2>&1; then
        echo "  ✅ $label  $url"
    else
        echo "  ❌ $label  $url (offline)"
    fi
}

cmd_build() {
    echo "🔨 Building $IMAGE ..."
    $COMPOSE build
    echo "✅ Image ready: $IMAGE"
}

cmd_up() {
    load_env
    ports
    check_llm_from_docker
    echo "🚀 Starting example lab (oracle + lab + researcher + critic) ..."
    $COMPOSE up -d oracle lab researcher critic
    echo ""
    echo "✅ Dashboard:  http://localhost:${LAB_PORT}"
    echo "   Oracle:     http://localhost:${ORACLE_PORT}"
    echo "   Scientists: :${RESEARCHER_PORT} researcher · :${CRITIC_PORT} critic"
    echo "   Status:     ./docker.sh status"
    echo "   Loop:       ./docker.sh loop"
}

cmd_minimal() {
    load_env
    ports
    echo "🚀 Starting minimal stack (oracle + lab) ..."
    $COMPOSE up -d oracle lab
    echo "✅ Dashboard: http://localhost:${LAB_PORT}"
}

cmd_down() {
    echo "🛑 Stopping GetAiLab containers ..."
    $COMPOSE --profile cli down --remove-orphans
    echo "✅ Stack stopped."
}

cmd_clean() {
    echo "🧹 Stopping stack and pruning orphans ..."
    $COMPOSE --profile cli down -v --remove-orphans
    docker container prune -f >/dev/null 2>&1 || true
    docker network prune -f >/dev/null 2>&1 || true
    echo "✅ Clean slate (host ./data bind-mount preserved)."
}

cmd_status() {
    load_env
    ports
    echo "📡 Example lab health"
    echo "────────────────────────────────────────"
    probe "http://localhost:${LAB_PORT}/health" "Lab"
    probe "http://localhost:${ORACLE_PORT}/health" "Oracle"
    probe "http://localhost:${RESEARCHER_PORT}/health" "Researcher"
    probe "http://localhost:${CRITIC_PORT}/health" "Critic"
    echo ""
    $COMPOSE ps 2>/dev/null || true
    echo ""
    if command -v python3 >/dev/null 2>&1; then
        LAB_ID=example ORACLE_URL="http://localhost:${ORACLE_PORT}" LAB_URL="http://localhost:${LAB_PORT}" \
            python3 run_chimera.py --status 2>/dev/null | head -20 || true
    fi
}

cmd_logs() {
    $COMPOSE logs -f --tail=100 "${1:-lab}"
}

cmd_cli() {
    load_env
    $COMPOSE up -d oracle lab researcher critic
    echo "💬 Commander chat (Ctrl+C to exit) ..."
    $COMPOSE --profile cli run --rm -it cli
}

cmd_loop() {
    load_env
    check_llm_from_docker
    $COMPOSE up -d oracle lab researcher critic
    sleep 3
    echo "🔄 Dialectic loop in container ..."
    $COMPOSE --profile cli run --rm -it loop
}

usage() {
    sed -n '3,14p' "$0" | sed 's/^# \{0,1\}//'
    echo ""
    echo "Commands: build | up | minimal | down | clean | status | logs | cli | loop"
}

main() {
    require_docker
    local cmd="${1:-}"
    shift || true
    case "$cmd" in
        build)   cmd_build ;;
        up)      cmd_up ;;
        minimal) cmd_minimal ;;
        down)    cmd_down ;;
        clean)   cmd_clean ;;
        status)  cmd_status ;;
        logs)    cmd_logs "${1:-lab}" ;;
        cli)     cmd_cli ;;
        loop)    cmd_loop ;;
        ""|help|-h|--help) usage ;;
        *) die "Unknown: $cmd (try: ./docker.sh help)" ;;
    esac
}

main "$@"