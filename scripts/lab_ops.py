#!/usr/bin/env python3
"""Per-lab boot/stop — port-scoped, does not kill other running labs."""
from __future__ import annotations

import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent


def _python() -> str:
    if sys.platform == "win32":
        venv = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv = ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def _load_dotenv() -> None:
    for name in (".env",):
        p = ROOT / name
        if p.is_file():
            try:
                from dotenv import load_dotenv
                load_dotenv(p)
            except Exception:
                pass
    lid = os.getenv("LAB_ID", "").strip()
    if lid:
        lp = ROOT / f".env.{lid}"
        if lp.is_file():
            try:
                from dotenv import load_dotenv
                load_dotenv(lp)
            except Exception:
                pass


def _kill_port(port: int) -> None:
    if port <= 0:
        return
    if sys.platform == "win32":
        try:
            ps = (
                f"$c = Get-NetTCPConnection -LocalPort {port} -ErrorAction SilentlyContinue; "
                f"$c | ForEach-Object {{ Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }}"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], cwd=ROOT, capture_output=True)
        except Exception:
            pass
    else:
        subprocess.run(["fuser", "-k", f"{port}/tcp"], cwd=ROOT, capture_output=True)


def _pkill(pattern: str) -> None:
    if sys.platform == "win32":
        try:
            ps = (
                "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                f"Where-Object {{ $_.CommandLine -match '{pattern}' }} | "
                "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
            )
            subprocess.run(["powershell", "-NoProfile", "-Command", ps], cwd=ROOT, capture_output=True)
        except Exception:
            pass
    else:
        subprocess.run(["pkill", "-f", pattern], cwd=ROOT, capture_output=True)


def get_lab_runtime_config(lab_id: str) -> Dict[str, Any]:
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from getailab.lab_config import _chimera_default_config, load_lab_config, lab_port_map, personas_yaml_path

    if lab_id == "example":
        cfg = _chimera_default_config()
    else:
        cfg = load_lab_config(lab_id)
    ports = lab_port_map(lab_id)
    scientists = cfg.get("scientists") or {}
    return {
        "lab_id": lab_id,
        "display_name": cfg.get("display_name", lab_id),
        "oracle_port": int(cfg.get("oracle_port", ports.get("oracle", 5024))),
        "lab_port": int(cfg.get("lab_port", ports.get("lab", 5035))),
        "personas_yaml": str(personas_yaml_path(lab_id).relative_to(ROOT)),
        "scientists": scientists,
        "ports": ports,
    }


def stop_lab(lab_id: str, verbose: bool = True) -> None:
    """Stop only this lab's listeners (by port) — other labs keep running."""
    cfg = get_lab_runtime_config(lab_id)
    if verbose:
        print(f"🛑 Stopping lab: {lab_id} (port-scoped — other labs untouched)")

    for port in sorted(set(cfg["ports"].values())):
        if port > 0:
            _kill_port(port)

    # Port kill is primary — other labs on different ports stay up.
    if lab_id != "example":
        _pkill(f"scientists/forges/{lab_id}/")
        _pkill(f"LAB_ID={lab_id}.*app_oracle")
        _pkill(f"LAB_ID={lab_id}.*app_lab")

    time.sleep(1)
    if verbose:
        print(f"✅ {lab_id} stopped (or was not running)")


def _start_bg(cmd: List[str], log_name: str, env: Dict[str, str]) -> None:
    logs = ROOT / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    log_path = logs / log_name
    full_env = os.environ.copy()
    full_env.update(env)
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.CREATE_NEW_PROCESS_GROUP  # type: ignore[attr-defined]
    with open(log_path, "w", encoding="utf-8") as out:
        subprocess.Popen(cmd, cwd=ROOT, env=full_env, stdout=out, stderr=subprocess.STDOUT, creationflags=flags)
    print(f"  → {' '.join(cmd[-2:])}  log: logs/{log_name}")


def boot_lab(lab_id: str, *, restart: bool = True, verbose: bool = True) -> Dict[str, Any]:
    """Boot a single lab on its configured ports."""
    _load_dotenv()
    cfg = get_lab_runtime_config(lab_id)
    py = _python()

    if verbose:
        print()
        print("  ╔══════════════════════════════════════════════════════════════════╗")
        print(f"  ║   Booting: {cfg['display_name'][:50]:<50} ║")
        print(f"  ║   Lab :{cfg['lab_port']}  Oracle :{cfg['oracle_port']:<37} ║")
        print("  ╚══════════════════════════════════════════════════════════════════╝")
        print()

    if restart:
        stop_lab(lab_id, verbose=verbose)

    base_env = {
        "LAB_ID": lab_id,
        "LAB_PORT": str(cfg["lab_port"]),
        "ORACLE_PORT": str(cfg["oracle_port"]),
        "ORACLE_URL": f"http://localhost:{cfg['oracle_port']}",
        "LAB_URL": f"http://localhost:{cfg['lab_port']}",
        "PERSONAS_YAML": cfg["personas_yaml"],
    }

    print("⚙️  Lab sandbox...")
    _start_bg(
        [py, str(ROOT / "lab" / "app_lab.py")],
        f"{lab_id}_lab.log" if lab_id != "example" else "app_lab.log",
        base_env,
    )
    time.sleep(2)

    print("🔮 Oracle...")
    _start_bg(
        [py, str(ROOT / "scientists" / "app_oracle.py")],
        f"{lab_id}_oracle.log" if lab_id != "example" else "app_oracle.log",
        base_env,
    )
    time.sleep(2)

    print("🧠 Squad...")
    scientists = cfg["scientists"]
    if lab_id == "example":
        for script in sorted((ROOT / "scientists").glob("app_*.py")):
            if script.name == "app_oracle.py":
                continue
            _start_bg([py, str(script)], f"{script.stem}.log", base_env)
            time.sleep(0.12)
    else:
        forge = ROOT / "scientists" / "forges" / lab_id
        for name in sorted(scientists.keys()):
            if name.lower() == "oracle":
                continue
            script = forge / f"app_{name.lower()}.py"
            if not script.is_file():
                print(f"  ⚠️  Missing {script.relative_to(ROOT)}")
                continue
            _start_bg([py, str(script)], f"{lab_id}_{name.lower()}.log", base_env)
            time.sleep(0.12)

    vault = ROOT / "data" / "labs" / lab_id
    print()
    print(f"✅ {lab_id} online.")
    print(f"   Dashboard : http://localhost:{cfg['lab_port']}")
    print(f"   Oracle    : http://localhost:{cfg['oracle_port']}")
    print(f"   Vault     : {vault}")
    print()
    return cfg


def run_commander(lab_id: str) -> int:
    _load_dotenv()
    cfg = get_lab_runtime_config(lab_id)
    env = os.environ.copy()
    env.update({
        "LAB_ID": lab_id,
        "LAB_PORT": str(cfg["lab_port"]),
        "ORACLE_URL": f"http://localhost:{cfg['oracle_port']}",
        "LAB_URL": f"http://localhost:{cfg['lab_port']}",
        "PERSONAS_YAML": cfg["personas_yaml"],
    })
    print("🚀 Commander Console (Ctrl+C exits — lab keeps running)")
    print()
    try:
        return subprocess.run([_python(), str(ROOT / "run_chimera.py")], cwd=ROOT, env=env).returncode or 0
    except KeyboardInterrupt:
        print("\nConsole closed. Lab still running.")
        return 0