#!/usr/bin/env python3
"""
GetAiLab — cross-platform environment bootstrap.

Creates .venv, installs requirements, seeds .env, checks LLM backend.
Used by Install-GetAiLab-* launch packs (Linux / macOS / Windows).
"""
from __future__ import annotations

import argparse
import os
import platform
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"


def _py() -> str:
    if sys.platform == "win32":
        venv_py = VENV_DIR / "Scripts" / "python.exe"
    else:
        venv_py = VENV_DIR / "bin" / "python"
    if venv_py.is_file():
        return str(venv_py)
    return sys.executable


def _banner():
    print()
    print("  ╔══════════════════════════════════════════════════════════════════╗")
    print("  ║   GetAiLab · Environment Setup                                    ║")
    print(f"  ║   OS: {platform.system()} {platform.release():<44} ║")
    print("  ╚══════════════════════════════════════════════════════════════════╝")
    print()


def _prompt(msg: str, default: str = "y") -> bool:
    if os.environ.get("GETAILAB_NONINTERACTIVE", "").strip() in ("1", "true", "yes"):
        return default.lower() in ("y", "yes", "1", "true")
    try:
        ans = input(f"{msg} [{'Y/n' if default.lower() == 'y' else 'y/N'}]: ").strip().lower()
    except EOFError:
        return default.lower() in ("y", "yes")
    if not ans:
        return default.lower() in ("y", "yes")
    return ans in ("y", "yes", "1")


def _find_python() -> str:
    candidates = []
    if sys.platform == "win32":
        for exe in ("py -3.11", "py -3.12", "py -3", "python", "python3"):
            candidates.append(exe.split())
    else:
        for exe in ("python3.11", "python3.12", "python3", "python"):
            candidates.append([exe])
    for cmd in candidates:
        try:
            r = subprocess.run(
                cmd + ["-c", "import sys; print(sys.version_info[:2])"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if r.returncode != 0:
                continue
            major, minor = map(int, r.stdout.strip().strip("()").split(",")[0:2])
            if (major, minor) >= (3, 10):
                return cmd[0] if len(cmd) == 1 else " ".join(cmd)
        except Exception:
            continue
    return sys.executable


def _run(cmd: list, **kwargs) -> int:
    print(f"  → {' '.join(cmd)}")
    return subprocess.run(cmd, cwd=ROOT, **kwargs).returncode


def ensure_venv(python_cmd: str) -> None:
    if VENV_DIR.is_dir() and _prompt("Virtualenv .venv exists. Reuse it?", "y"):
        print("✅ Using existing .venv")
        return
    if VENV_DIR.is_dir() and not _prompt("Recreate .venv from scratch?", "n"):
        return
    if VENV_DIR.is_dir():
        shutil.rmtree(VENV_DIR)
    base = python_cmd.split()
    print(f"📦 Creating virtualenv with {python_cmd} ...")
    if _run(base + ["-m", "venv", str(VENV_DIR)]) != 0:
        print()
        print("❌ venv creation failed.")
        if sys.platform == "linux":
            print("   Try (will ask for sudo password):")
            print("     sudo apt update")
            print("     sudo apt install -y python3-venv python3-pip")
        elif sys.platform == "darwin":
            print("   Install Python 3.11+ from https://www.python.org/downloads/macos/")
            print("   Or: brew install python@3.11")
        else:
            print("   Install Python 3.11+ from https://www.python.org/downloads/windows/")
            print("   Ensure 'Add Python to PATH' was checked during install.")
        sys.exit(1)
    print("✅ .venv created")


def pip_install() -> None:
    py = _py()
    print("📚 Upgrading pip...")
    _run([py, "-m", "pip", "install", "--upgrade", "pip"], check=False)
    for req in ("lab/requirements.txt", "scientists/requirements.txt"):
        path = ROOT / req
        if not path.is_file():
            print(f"⚠️  Missing {req}")
            continue
        print(f"📚 Installing {req} ...")
        if _run([py, "-m", "pip", "install", "-r", str(path)]) != 0:
            print(f"❌ pip install failed for {req}")
            sys.exit(1)
    print("✅ Python dependencies installed")


def ensure_env_file() -> None:
    if ENV_FILE.is_file():
        print("✅ .env already exists (not overwritten)")
        return
    if not ENV_EXAMPLE.is_file():
        print("⚠️  No .env.example — skipping env seed")
        return
    shutil.copy(ENV_EXAMPLE, ENV_FILE)
    print("✅ Created .env from .env.example")
    print("   Edit .env to set LLM_MODEL, API keys, or forged lab LAB_ID.")


def ensure_dirs() -> None:
    for rel in ("logs", "data/labs/example", "lab/artifacts"):
        (ROOT / rel).mkdir(parents=True, exist_ok=True)
    print("✅ Workspace directories ready")


def check_ollama() -> None:
    endpoint = os.getenv("LLM_ENDPOINT", "http://localhost:11434")
    url = endpoint.rstrip("/") + "/api/tags"
    print(f"🧠 Checking LLM backend ({endpoint})...")
    try:
        with urllib.request.urlopen(url, timeout=3) as r:
            if r.status == 200:
                print("✅ Ollama reachable")
                return
    except Exception:
        pass
    print("⚠️  Ollama not reachable at", endpoint)
    print("   Start it in another terminal:")
    if sys.platform == "win32":
        print("     ollama serve")
    else:
        print("     ollama serve")
    print("   Or set LLM_PROVIDER=openai|google|anthropic in .env with an API key.")
    print("   Pull loop model: ollama pull minimax-m2.5:cloud")


def optional_playwright() -> None:
    if not _prompt("Install Playwright Chromium for Sauron web vision?", "n"):
        print("   (Skip — run later: .venv python -m playwright install chromium)")
        return
    py = _py()
    _run([py, "-m", "playwright", "install", "chromium"])


def print_next_steps() -> None:
    plat = sys.platform
    print()
    print("  ┌────────────────────────────────────────────────────────────────────┐")
    print("  │  Setup complete                                                     │")
    if plat == "win32":
        print("  │  Boot:  double-click Boot-GetAiLab-Windows.bat                     │")
        print("  │     or: .\\Boot-GetAiLab-Windows.ps1                               │")
    elif plat == "darwin":
        print("  │  Boot:  double-click Boot-GetAiLab-Mac.command                       │")
    else:
        print("  │  Boot:  ./Boot-GetAiLab-Linux.sh                                   │")
    print("  │  Doctor: python scripts/boot_services.py --check-only              │")
    print("  │  Dashboard: http://localhost:5035                                  │")
    print("  └────────────────────────────────────────────────────────────────────┘")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="GetAiLab environment bootstrap")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--skip-playwright", action="store_true")
    args = parser.parse_args()
    if args.non_interactive:
        os.environ["GETAILAB_NONINTERACTIVE"] = "1"

    os.chdir(ROOT)
    _banner()

    if sys.version_info < (3, 10):
        print(f"❌ Python 3.10+ required (found {sys.version})")
        return 1

    python_cmd = _find_python()
    print(f"🐍 Bootstrap Python: {python_cmd}")
    ensure_venv(python_cmd)
    pip_install()
    ensure_env_file()
    ensure_dirs()

    try:
        from dotenv import load_dotenv
        load_dotenv(ENV_FILE)
    except Exception:
        pass
    check_ollama()

    if not args.skip_playwright:
        optional_playwright()

    print_next_steps()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())