#!/usr/bin/env python3
"""
GetAiLab Interactive Lab Launcher

- List running labs & ports
- Boot an existing lab (port-scoped — won't kill other labs)
- Forge a new lab (auto port allocation)
- Environment setup
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from getailab.lab_config import enumerate_all_labs, preview_port_block  # noqa: E402

sys.path.insert(0, str(ROOT / "scripts"))
from lab_ops import boot_lab, get_lab_runtime_config, run_commander, stop_lab  # noqa: E402


def _python() -> str:
    if sys.platform == "win32":
        venv = ROOT / ".venv" / "Scripts" / "python.exe"
    else:
        venv = ROOT / ".venv" / "bin" / "python"
    return str(venv) if venv.is_file() else sys.executable


def _clear():
    os.system("cls" if sys.platform == "win32" else "clear")


def _banner():
    print()
    print("  ╔══════════════════════════════════════════════════════════════════╗")
    print("  ║   GetAiLab · Interactive Lab Launcher                           ║")
    print("  ║   Boot · Forge · Port-safe multi-lab                              ║")
    print("  ╚══════════════════════════════════════════════════════════════════╝")
    print()


def _status_icon(live: bool) -> str:
    return "🟢 LIVE" if live else "⚫ off"


def list_labs_table() -> list:
    labs = enumerate_all_labs()
    print()
    print("  ID               DISPLAY NAME                  ORACLE   LAB    STATUS")
    print("  " + "─" * 72)
    for lab in labs:
        lid = lab.get("lab_id", "?")[:16]
        name = (lab.get("display_name") or lid)[:28]
        op = lab.get("oracle_port", "?")
        lp = lab.get("lab_port", "?")
        st = _status_icon(lab.get("any_live", False))
        print(f"  {lid:<16} {name:<28} :{op:<5} :{lp:<5} {st}")
    print()
    return labs


def menu_setup_env():
    print("\n📦 Environment setup...")
    py = _python()
    rc = subprocess.run(
        [py, str(ROOT / "scripts" / "bootstrap_env.py")],
        cwd=ROOT,
    ).returncode
    input("\nPress Enter to continue...")
    return rc


def menu_forge_lab():
    print("\n🔥 Lab Forge — create a new research division")
    print("   Ports are scanned automatically (won't clash with running labs).\n")
    try:
        n = int(input("How many scientists (1–10)? [3]: ").strip() or "3")
        n = max(1, min(10, n))
    except ValueError:
        n = 3
    block = preview_port_block(n)
    print(f"\n   Next free port block for {n} scientists:")
    print(f"     Oracle  : {block['oracle_port']}")
    print(f"     Lab     : {block['lab_port']}")
    print(f"     Squad   : {block['scientist_ports']}")
    print()
    confirm = input("Continue to forge wizard? [Y/n]: ").strip().lower()
    if confirm in ("n", "no"):
        return
    subprocess.run([_python(), str(ROOT / "scripts" / "persona_builder.py")], cwd=ROOT)
    input("\nPress Enter to continue...")


def _pick_lab(prompt: str) -> str | None:
    labs = enumerate_all_labs()
    list_labs_table()
    choice = input(prompt).strip()
    if not choice:
        return None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(labs):
            return labs[idx]["lab_id"]
    for lab in labs:
        if lab["lab_id"] == choice or lab["lab_id"].startswith(choice):
            return lab["lab_id"]
    print("❌ Unknown lab")
    return None


def menu_boot_lab():
    lab_id = _pick_lab("Boot which lab? (number or lab_id): ")
    if not lab_id:
        return
    running = [l for l in enumerate_all_labs() if l["lab_id"] == lab_id and l.get("any_live")]
    if running:
        ans = input(f"  {lab_id} has live ports. Restart only this lab? [Y/n]: ").strip().lower()
        if ans in ("n", "no"):
            return
    boot_lab(lab_id, restart=True)
    ans = input("Open Commander Console now? [Y/n]: ").strip().lower()
    if ans not in ("n", "no"):
        run_commander(lab_id)
    else:
        cfg = get_lab_runtime_config(lab_id)
        print(f"\n   export LAB_ID={lab_id}")
        print(f"   source .env.{lab_id} 2>/dev/null || true")
        print(f"   python3 run_chimera.py")
        print(f"   Dashboard: http://localhost:{cfg['lab_port']}\n")
        input("Press Enter to continue...")


def menu_stop_lab():
    lab_id = _pick_lab("Stop which lab? (number or lab_id): ")
    if not lab_id:
        return
    stop_lab(lab_id)
    input("\nPress Enter to continue...")


def menu_console_only():
    lab_id = _pick_lab("Commander console for which lab?: ")
    if not lab_id:
        return
    run_commander(lab_id)


def main() -> int:
    os.chdir(ROOT)
    while True:
        _clear()
        _banner()
        list_labs_table()
        print("  1  Setup environment (venv, deps, .env)")
        print("  2  Boot a lab          (only restarts THAT lab)")
        print("  3  Forge NEW lab       (name + squad + auto ports)")
        print("  4  Stop a lab          (port-scoped — others stay up)")
        print("  5  Commander console   (pick active lab)")
        print("  6  Refresh list")
        print("  0  Exit")
        print()
        choice = input("  Choose: ").strip()

        if choice == "0":
            print("Bye.")
            return 0
        if choice == "1":
            menu_setup_env()
        elif choice == "2":
            menu_boot_lab()
        elif choice == "3":
            menu_forge_lab()
        elif choice == "4":
            menu_stop_lab()
        elif choice == "5":
            menu_console_only()
        elif choice == "6":
            continue
        else:
            input("  Invalid option. Enter...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())