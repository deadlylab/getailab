#!/usr/bin/env bash
# ==============================================================================
# Install Python 3.11 for GetAiLab (side-by-side with system Python 3.13)
#
# Does NOT replace Kali's system python3 — only this project uses 3.11 via pyenv.
#
# Usage:
#   ./setup_python.sh                  # install 3.11 + pip deps
#   ./setup_python.sh --install-deps   # also run sudo apt for compile deps
# ==============================================================================

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYVER="${GETAILAB_PYTHON:-3.11.15}"
INSTALL_DEPS=false

for arg in "$@"; do
    case "$arg" in
        --install-deps) INSTALL_DEPS=true ;;
        -h|--help)
            echo "Usage: ./setup_python.sh [--install-deps]"
            exit 0
            ;;
    esac
done

die() { echo "❌ $*" >&2; exit 1; }

# Resolve apt package name — Kali/Debian names vary slightly across releases.
apt_pkg_available() {
    apt-cache show "$1" &>/dev/null
}

resolve_build_packages() {
    local resolved=()
    local wanted=(
        build-essential
        libssl-dev
        zlib1g-dev
        libbz2-dev
        libsqlite3-dev
        libffi-dev
        liblzma-dev
    )
    for pkg in "${wanted[@]}"; do
        if apt_pkg_available "$pkg"; then
            resolved+=("$pkg")
        else
            echo "⚠️  Not in apt cache: $pkg (skipping)"
        fi
    done

    # readline headers — required for pyenv Python line-editing
    if apt_pkg_available "libreadline-dev"; then
        resolved+=("libreadline-dev")
    elif apt_pkg_available "libreadline-gplv3-dev"; then
        resolved+=("libreadline-gplv3-dev")
    elif apt_pkg_available "libeditreadline-dev"; then
        echo "⚠️  Using libeditreadline-dev shim instead of libreadline-dev"
        resolved+=("libeditreadline-dev")
    else
        echo "⚠️  No readline -dev package found — pyenv build may fail on readline module"
    fi

    echo "${resolved[@]}"
}

install_build_deps() {
    echo "📦 Installing pyenv compile dependencies (sudo)..."
    if ! command -v apt-get >/dev/null 2>&1; then
        die "apt-get not found — install build deps manually for pyenv"
    fi
    sudo apt-get update
    # shellcheck disable=SC2046
    sudo apt-get install -y $(resolve_build_packages)
    echo "✅ Build deps installed"
}

echo "🐍 GetAiLab Python setup (target: $PYVER)"
echo "   System python: $(python3 --version 2>/dev/null || echo 'unknown')"
echo ""

if ! command -v pyenv >/dev/null 2>&1; then
    die "pyenv not found. Install: https://github.com/pyenv/pyenv#installation"
fi

export PATH="${HOME}/.pyenv/bin:${HOME}/.pyenv/shims:${PATH}"
if command -v pyenv init >/dev/null 2>&1; then
    eval "$(pyenv init -)"
fi

if $INSTALL_DEPS; then
    install_build_deps
else
    echo "📦 Build deps (run once if pyenv install fails):"
    echo "   ./setup_python.sh --install-deps"
    echo ""
    echo "   Or manually:"
    echo "   sudo apt update"
    # shellcheck disable=SC2046
    echo "   sudo apt install -y $(resolve_build_packages)"
    echo ""
fi

if ! pyenv versions --bare 2>/dev/null | grep -qx "$PYVER"; then
    echo "⬇️  Installing Python $PYVER via pyenv (may take a few minutes)..."
    if ! pyenv install -s "$PYVER"; then
        echo ""
        echo "❌ pyenv install failed."
        echo ""
        if ! $INSTALL_DEPS; then
            echo "   Try: ./setup_python.sh --install-deps"
        else
            echo "   If libreadline-dev was missing:"
            echo "     sudo apt update"
            echo "     sudo apt install libreadline-dev"
            echo "   Ensure /etc/apt/sources.list has Kali main repo enabled."
            echo "   Or use Docker instead: docker compose squad"
        fi
        exit 1
    fi
else
    echo "✅ Python $PYVER already installed in pyenv"
fi

echo "$PYVER" > .python-version
pyenv local "$PYVER"
pyenv rehash

LOCAL_PY="$(pyenv which python)"
echo ""
echo "✅ Project Python: $($LOCAL_PY --version)"
echo "   Path: $LOCAL_PY"
echo ""

echo "📚 Installing pip dependencies..."
"$LOCAL_PY" -m pip install --upgrade pip
"$LOCAL_PY" -m pip install -r lab/requirements.txt
"$LOCAL_PY" -m pip install -r scientists/requirements.txt

echo ""
echo "🎭 Optional: Playwright for Sauron web vision"
"$LOCAL_PY" -m playwright install chromium 2>/dev/null || echo "   (skip if not needed yet)"
echo ""
echo "✅ Done. In this directory, python3 → $PYVER via pyenv."
echo ""
echo "   Verify:  python3 --version"
echo "   Ollama:   ollama serve   (keep running)"
echo "   Boot:     ./boot_example.sh"
echo ""
echo "   Local loops are slow (large prompts) — default 600s timeout per scientist."
echo "   System python3 elsewhere is unchanged — Kali stays on 3.13."