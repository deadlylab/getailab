#!/usr/bin/env python3
"""
GetAiLab — cross-platform the example lab service boot.

Starts lab, oracle, and scientist squad in background with logs/.
"""
from __future__ import annotations

import argparse
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / "logs"
SCIENTISTS_DIR = ROOT / "scientists"


def _python() -> str:
    if sys.platform == "win32":
        venv = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv = ROOT / ".venv" / "bin" / "python"
    if venv.is_file():
        return str(venv)
    return sys.executable


def _load_env() -> None:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        example = ROOT / ".env.example"
        if example.is_file():
            import shutil
            shutil.copy(example, env_path)
            print("⚠️  Created .env from .env.example")
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except Exception:
        pass


def _banner():
    print()
    print("  ╔══════════════════════════════════════════════════════════════════╗")
    print("  ║   GetAiLab · the example lab Ignition                                     ║")
    print(f"  ║   {platform.system()} · Python {_python()}".ljust(69) + "║")
    print("  ╚══════════════════════════════════════════════════════════════════╝")
    print()


def stop_old_processes() -> None:
    print("🧹 Stopping prior GetAiLab agent processes...")
    patterns = ("app_lab.py", "app_oracle.py", "app_albert", "app_bohr", "app_heisenberg",
                "app_alan", "app_brian", "app_carl", "app_neil", "app_roger", "app_emmy",
                "app_andrew", "app_tesla", "forges/")
    if sys.platform == "win32":
        try:
            ps = (
                "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                "Where-Object { $_.CommandLine -match 'app_lab|app_oracle|scientists/app_' } | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                cwd=ROOT,
                capture_output=True,
            )
        except Exception:
            pass
    else:
        for pat in ("python3.*app_lab", "python3.*app_oracle", "python3.*scientists/app_",
                    "python.*app_lab", "python.*app_oracle"):
            subprocess.run(["pkill", "-f", pat], cwd=ROOT, capture_output=True)
    time.sleep(1)


def start_process(script: Path, log_name: str, extra_env: dict | None = None) -> None:
    LOGS.mkdir(parents=True, exist_ok=True)
    log_path = LOGS / log_name
    env = os.environ.copy()
    env.setdefault("LAB_ID", "example")
    if extra_env:
        env.update(extra_env)
    py = _python()
    out = open(log_path, "w", encoding="utf-8")
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    subprocess.Popen(
        [py, str(script)],
        cwd=ROOT,
        env=env,
        stdout=out,
        stderr=subprocess.STDOUT,
        creationflags=flags,
    )
    print(f"  → {script.name}  (log: logs/{log_name})")


def boot_squad() -> None:
    py = _python()
    print("🧠 LLM backend check...")
    subprocess.run([py, "-c", """
import os
try:
    from dotenv import load_dotenv
    load_dotenv('.env')
except Exception:
    pass
from llm.adapter import get_env_provider_config, create_default_adapter
cfg = get_env_provider_config()
print(f"  Provider: {cfg.get('provider')}  Model: {cfg.get('model')}")
a = create_default_adapter()
print(f"  Health: {'READY' if a.is_ready() else 'NOT REACHABLE'}")
"""], cwd=ROOT)

    print("⚙️  Lab sandbox...")
    start_process(ROOT / "lab" / "app_lab.py", "app_lab.log",
                  {"LAB_PORT": os.getenv("LAB_PORT", "5035"),
                   "ORACLE_URL": os.getenv("ORACLE_URL", "http://localhost:5024")})
    time.sleep(2)

    print("🔮 Oracle...")
    start_process(ROOT / "scientists" / "app_oracle.py", "app_oracle.log")
    time.sleep(2)

    print("🧠 Scientist squad...")
    for script in sorted(SCIENTISTS_DIR.glob("app_*.py")):
        if script.name == "app_oracle.py":
            continue
        start_process(script, f"{script.stem}.log")
        time.sleep(0.15)

    lab_port = os.getenv("LAB_PORT", "5035")
    oracle_port = os.getenv("ORACLE_URL", "http://localhost:5024").split(":")[-1].rstrip("/")
    print()
    print("✅ the example lab online.")
    print(f"   Dashboard : http://localhost:{lab_port}")
    print(f"   Oracle    : http://localhost:{oracle_port}")
    print("   Logs      : logs/")
    print()


def check_only() -> int:
    import urllib.request
    ok = True
    for name, url in (
        ("Lab", f"http://127.0.0.1:{os.getenv('LAB_PORT', '5035')}/health"),
        ("Oracle", f"http://127.0.0.1:5024/health"),
    ):
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                print(f"  {name}: {'OK' if r.status == 200 else r.status}")
        except Exception as e:
            print(f"  {name}: DOWN ({e})")
            ok = False
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--no-stop", action="store_true")
    parser.add_argument("--no-console", action="store_true", help="Boot only; do not launch run_chimera.py")
    args = parser.parse_args()

    os.chdir(ROOT)
    _load_env()

    if args.check_only:
        return check_only()

    _banner()
    if not args.no_stop:
        stop_old_processes()
    boot_squad()

    if args.no_console:
        return 0

    print("🚀 Launching Commander Console (Ctrl+C exits console; services keep running)...")
    print()
    py = _python()
    try:
        subprocess.run([py, str(ROOT / "run_chimera.py")], cwd=ROOT)
    except KeyboardInterrupt:
        print("\nConsole closed. Background services still running. Use boot script again or stop manually.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())