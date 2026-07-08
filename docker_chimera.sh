#!/usr/bin/env bash
# ==============================================================================
# PROJECT CHIMERA — DOCKER IGNITION
# Build and run GetAiLab in containers (alternative to boot_chimera.sh).
#
# Usage:
#   ./docker_chimera.sh build          # build image only
#   ./docker_chimera.sh up             # lab + oracle (dashboard)
#   ./docker_chimera.sh squad          # lab + oracle + all 10 scientists
#   ./docker_chimera.sh down           # stop stack, remove orphans
#   ./docker_chimera.sh clean          # down + prune unused volumes/networks
#   ./docker_chimera.sh status         # health check all running services
#   ./docker_chimera.sh logs [service] # tail logs (default: lab)
#   ./docker_chimera.sh cli            # interactive chat CLI in container
#   ./docker_chimera.sh loop           # full dialectic loop (squad must be up)
#
# Dashboard: http://localhost:${LAB_HOST_PORT:-5035}
# ==============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

COMPOSE="docker compose"
IMAGE="getailab:latest"
LAB_PORT="${LAB_HOST_PORT:-5035}"
ORACLE_PORT="${ORACLE_HOST_PORT:-5024}"

die() { echo "❌ $*" >&2; exit 1; }

require_docker() {
    command -v docker >/dev/null 2>&1 || die "docker not found — install Docker first."
    $COMPOSE version >/dev/null 2>&1 || die "docker compose not available."
}

require_env() {
    if [[ ! -f .env ]]; then
        echo "⚠️  No .env found — copying from .env.example"
        cp .env.example .env
        echo "   Edit .env before production use (API keys, models, etc.)"
    fi
    set -a
    # shellcheck disable=SC1091
    source .env
    set +a
    LAB_PORT="${LAB_HOST_PORT:-5035}"
    ORACLE_PORT="${ORACLE_HOST_PORT:-5024}"
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
    echo "❌ LLM NOT REACHABLE from Docker — loops will fail with connection errors."
    echo ""
    echo "   Cause: host Ollama usually binds 127.0.0.1 only."
    echo "   Containers use host.docker.internal and cannot hit loopback-only services."
    echo ""
    echo "   Fix (recommended):"
    echo "     ./scripts/ollama_for_docker.sh"
    echo ""
    echo "   Or manually:"
    echo "     pkill ollama; OLLAMA_HOST=0.0.0.0 ollama serve"
    echo ""
    echo "   Alternatives:"
    echo "     ./boot_chimera.sh          # native — uses localhost Ollama directly"
    echo "     Set LLM_PROVIDER=openai + API key in .env"
    echo ""
    die "Aborting — start Ollama for Docker first."
}

cmd_build() {
    echo "🔨 Building $IMAGE ..."
    $COMPOSE build
    echo "✅ Image ready: $IMAGE"
}

cmd_up() {
    require_env
    echo "🚀 Starting lab + oracle ..."
    $COMPOSE up -d lab oracle
    echo ""
    echo "✅ Dashboard: http://localhost:${LAB_PORT}"
    echo "   Oracle:    http://localhost:${ORACLE_PORT}"
    echo "   Logs:      ./docker_chimera.sh logs"
    echo "   Full squad: ./docker_chimera.sh squad"
}

cmd_squad() {
    require_env
    check_llm_from_docker
    echo "🚀 Starting full scientist squad ..."
    $COMPOSE --profile squad up -d
    echo ""
    echo "✅ All services up (lab + oracle + 10 scientists)"
    echo "   Dashboard: http://localhost:${LAB_PORT}"
    echo "   Status:    ./docker_chimera.sh status"
    echo "   Loop:      ./docker_chimera.sh loop"
}

cmd_down() {
    echo "🛑 Stopping GetAiLab containers ..."
    $COMPOSE --profile squad --profile cli down --remove-orphans
    echo "✅ Stack stopped."
}

cmd_clean() {
    echo "🧹 Stopping stack and pruning orphans ..."
    $COMPOSE --profile squad --profile cli down -v --remove-orphans
    docker container prune -f >/dev/null 2>&1 || true
    docker network prune -f >/dev/null 2>&1 || true
    echo "✅ Clean slate (containers + orphans removed)."
    echo "   Note: host ./data and ./chimera_lab.db are bind-mounted, not deleted."
}

cmd_status() {
    require_env
    echo "📡 Service health"
    echo "────────────────────────────────────────"
    for url in \
        "http://localhost:${LAB_PORT}/health|Lab" \
        "http://localhost:${ORACLE_PORT}/health|Oracle"; do
        IFS='|' read -r endpoint label <<< "$url"
        if curl -sf "$endpoint" >/dev/null 2>&1; then
            echo "  ✅ $label  $endpoint"
        else
            echo "  ❌ $label  $endpoint (offline)"
        fi
    done
    for port in 5025 5026 5027 5028 5029 5030 5032 5034 5038 5039 5040; do
        if curl -sf "http://localhost:${port}/health" >/dev/null 2>&1; then
            echo "  ✅ Scientist :${port}"
        fi
    done
    echo ""
    $COMPOSE ps 2>/dev/null || true
}

cmd_logs() {
    local service="${1:-lab}"
    $COMPOSE logs -f --tail=100 "$service"
}

cmd_cli() {
    require_env
    echo "💬 Launching CLI chat (Ctrl+C to exit) ..."
    # -it required for backspace/arrow keys and readline editing inside the container
    $COMPOSE --profile cli run --rm -it cli
}

cmd_loop() {
    require_env
    check_llm_from_docker
    echo "🔄 Launching dialectic loop in container ..."
    echo "   (requires squad profile — starting if needed)"
    $COMPOSE --profile squad up -d
    sleep 3
    $COMPOSE --profile squad --profile cli run --rm -it loop
}

usage() {
    sed -n '6,17p' "$0" | sed 's/^# \{0,1\}//'
    echo ""
    echo "Commands: build | up | squad | down | clean | status | logs | cli | loop"
}

main() {
    require_docker
    local cmd="${1:-}"
    shift || true

    case "$cmd" in
        build)  cmd_build ;;
        up)     cmd_up ;;
        squad)  cmd_squad ;;
        down)   cmd_down ;;
        clean)  cmd_clean ;;
        status) cmd_status ;;
        logs)   cmd_logs "${1:-lab}" ;;
        cli)    cmd_cli ;;
        loop)   cmd_loop ;;
        ""|help|-h|--help) usage ;;
        *) die "Unknown command: $cmd (try: ./docker_chimera.sh help)" ;;
    esac
}

main "$@"