#!/usr/bin/env python3
"""
GetAiLab Lab Forge — merged from uni_lab.py wizard + the example lab engine.

Generates a custom research lab into getailab_live (no forked mini-codebase).

Profiles:
  canvas   — thin personas, fast custom squad (uni_lab style)
  research — full vault + tickets + library + rich YAML personas

Usage:
    python3 scripts/create_lab.py
    python3 scripts/create_lab.py --lab-id cyber_lab --profile research --non-interactive ...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import stat
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from getailab.lab_config import (  # noqa: E402
    PROJECT_ROOT,
    allocate_ports,
    ensure_scientist_vault,
    ensure_vault_structure,
    forge_apps_dir,
    list_forged_labs,
    personas_yaml_path,
)

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install PyYAML")
    sys.exit(1)


class _LiteralStr(str):
    """Force multiline YAML block scalars for system_prompt fields."""


def _literal_str_representer(dumper, data):
    return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")


yaml.add_representer(_LiteralStr, _literal_str_representer)


def _dump_squad_yaml(data: dict) -> str:
    """Emit readable squad YAML with pipe-style system_prompt blocks."""
    out = dict(data)
    squad = []
    for member in out.get("squad", []):
        m = dict(member)
        sp = m.get("system_prompt")
        if isinstance(sp, str) and "\n" in sp:
            m["system_prompt"] = _LiteralStr(sp.strip() + "\n")
        squad.append(m)
    out["squad"] = squad
    return yaml.dump(out, default_flow_style=False, sort_keys=False, allow_unicode=True, width=1000)


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", name.lower().strip())
    return s.strip("_") or "custom_lab"


def _write(path: Path, content: str, *, executable: bool = False):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content.strip() + "\n", encoding="utf-8")
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IEXEC)
    print(f"  [+] {path.relative_to(PROJECT_ROOT)}")


def _canvas_system_prompt(name: str, role: str, persona: str, agenda: str) -> str:
    return (
        f"You are {name.title()}, a specialist on the {role} team.\n"
        f"Research agenda: {agenda}\n"
        f"Your focus: {persona}\n"
        "Work with precision. Demand testable predictions and artifacts (.csv, .json, .png). "
        "Argue your corner with rigor. Build on prior context when provided."
    )


def _research_system_prompt(name: str, role: str, persona: str, agenda: str) -> str:
    return (
        f"You are {name.title()} — {role}.\n\n"
        f"LAB RESEARCH AGENDA:\n{agenda}\n\n"
        f"DOMAIN FOCUS:\n{persona}\n\n"
        "You are part of a multi-agent dialectic research lab (GetAiLab).\n"
        "Phase 1: Formulate a high-rigor, testable hypothesis for the problem.\n"
        "Phase 2: Write executable Python that produces auditable artifacts on disk.\n"
        "Call out weak reasoning. Prefer simulations, data analysis, and measurable outputs.\n"
        "Your prior research book may be injected — build on it, do not blindly repeat."
    )


def _oracle_prompt(agenda: str, profile: str) -> str:
    if profile == "canvas":
        return (
            f"You are Oracle, process orchestrator for this research canvas.\n"
            f"Agenda: {agenda}\n"
            "Synthesize hypotheses with lab results. Cross-reference ARTIFACTS and stdout."
        )
    return (
        f"You are Oracle — guardian synthesizer for GetAiLab.\n"
        f"Research agenda: {agenda}\n"
        "Synthesize the dialectic loop: cross-reference scientist hypotheses with "
        "sandbox execution results and generated artifacts. Produce a consensus artefact "
        "that identifies convergences, contradictions, and the strongest next experiment."
    )


def build_squad_yaml(
    lab_id: str,
    display_name: str,
    agenda: str,
    squad: Dict[str, Dict[str, Any]],
    profile: str,
) -> dict:
    prompt_fn = _canvas_system_prompt if profile == "canvas" else _research_system_prompt
    oracle_port = int(squad.get("_oracle_port", 5024))
    members = []
    for name, data in squad.items():
        if name.startswith("_"):
            continue
        role = data.get("role", "researcher")
        persona = data.get("persona", role)
        display_role = data.get("display_role") or role
        role_slug = data.get("_role_slug") or _slug(role)[:40] or "researcher"
        expertise = data.get("expertise")
        if not expertise:
            expertise = [persona] if persona else []
        implement_focus = data.get("implement_focus") or (persona[:200] if persona else "data analysis and simulation")
        system_prompt = data.get("system_prompt") or prompt_fn(name, display_role, persona, agenda)
        entry: Dict[str, Any] = {
            "name": name,
            "port": data["port"],
            "role": role_slug,
            "display_role": display_role,
            "expertise": expertise,
            "implement_focus": implement_focus,
            "system_prompt": system_prompt,
        }
        if data.get("full_name"):
            entry["full_name"] = data["full_name"]
        members.append(entry)
    members.append({
        "name": "oracle",
        "port": oracle_port,
        "role": "orchestrator",
        "display_role": "Process Orchestrator",
        "expertise": ["synthesis", "loop coordination"],
        "implement_focus": "synthesis and next-step recommendation",
        "system_prompt": _oracle_prompt(agenda, profile),
    })
    return {
        "version": "1.0",
        "project": f"GetAiLab — {display_name}",
        "squad_name": display_name,
        "research_agenda": agenda,
        "build_profile": profile,
        "lab_id": lab_id,
        "squad": members,
    }


def _scientist_app_template(lab_id: str, name: str, port: int) -> str:
    return f'''#!/usr/bin/env python3
"""Forged scientist: {name} · lab {lab_id}"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path[:0] = [ROOT, os.path.join(ROOT, "scientists")]

os.environ.setdefault("LAB_ID", "{lab_id}")
os.environ.setdefault("PERSONAS_YAML", "personas/{lab_id}_squad.yaml")

from base_agent import create_agent_app, run_agent
from personas.loader import build_agent_config

AGENT_CONFIG = build_agent_config("{name}", overrides={{"port": {port}}})
app = create_agent_app(AGENT_CONFIG)

if __name__ == "__main__":
    run_agent(app, AGENT_CONFIG)
'''


def _boot_script(lab_id: str, oracle_port: int, lab_port: int, scientists: Dict[str, Dict]) -> str:
    lines = []
    for name in scientists:
        script = f"scientists/forges/{lab_id}/app_{name}.py"
        lines.append(f'echo "  -> {name}"')
        lines.append(
            f'LAB_ID={lab_id} PERSONAS_YAML=personas/{lab_id}_squad.yaml '
            f'python3 "{script}" > "logs/{lab_id}_{name}.log" 2>&1 &'
        )
        lines.append("sleep 0.2")
    apps = "\n".join(f"    {ln}" for ln in lines)
    return f'''#!/usr/bin/env bash
# Boot forged lab: {lab_id}
cd "$(dirname "$0")"
set -e

export LAB_ID="{lab_id}"
export PERSONAS_YAML="personas/{lab_id}_squad.yaml"
export ORACLE_PORT={oracle_port}
export LAB_PORT={lab_port}
export ORACLE_URL="http://localhost:{oracle_port}"
export LAB_URL="http://localhost:{lab_port}"

if [[ -f .env ]]; then
    set -a; source .env; set +a
fi
if [[ -f .env.{lab_id} ]]; then
    set -a; source .env.{lab_id}; set +a
fi

echo "🛑 Stopping prior {lab_id} agents (this lab only)..."
pkill -f "scientists/forges/{lab_id}/" 2>/dev/null || true
pkill -f "LAB_ID={lab_id}.*app_oracle" 2>/dev/null || true
pkill -f "LAB_ID={lab_id}.*app_lab" 2>/dev/null || true
fuser -k {oracle_port}/tcp 2>/dev/null || true
fuser -k {lab_port}/tcp 2>/dev/null || true
sleep 1

mkdir -p logs
echo "⚙️  Lab sandbox :{lab_port}..."
LAB_ID={lab_id} LAB_PORT={lab_port} ORACLE_URL=http://localhost:{oracle_port} \\
  python3 lab/app_lab.py > logs/{lab_id}_lab.log 2>&1 &
sleep 2

echo "🔮 Oracle :{oracle_port}..."
LAB_ID={lab_id} PERSONAS_YAML=personas/{lab_id}_squad.yaml ORACLE_PORT={oracle_port} \\
  python3 scientists/app_oracle.py > logs/{lab_id}_oracle.log 2>&1 &
sleep 2

echo "🧠 Squad ({len(scientists)} scientists)..."
{apps}

echo "✅ {lab_id} online."
echo "   Oracle :{oracle_port}  ·  Lab :{lab_port}  ·  Vault: data/labs/{lab_id}/"
echo ""
echo "   export LAB_ID={lab_id}"
echo "   export PERSONAS_YAML=personas/{lab_id}_squad.yaml"
echo "   python3 run_chimera.py"
'''


def _env_snippet(lab_id: str, oracle_port: int, lab_port: int) -> str:
    return f'''# Forged lab: {lab_id}
LAB_ID={lab_id}
PERSONAS_YAML=personas/{lab_id}_squad.yaml
ORACLE_PORT={oracle_port}
LAB_PORT={lab_port}
ORACLE_URL=http://localhost:{oracle_port}
LAB_URL=http://localhost:{lab_port}
JOB_TICKETS_DB=data/labs/{lab_id}/job_tickets.db
'''


def forge_lab(
    lab_id: str,
    display_name: str,
    agenda: str,
    squad: Dict[str, Dict[str, Any]],
    profile: str = "research",
) -> Path:
    """Generate all artifacts for a new lab. Returns project root."""
    oracle_port, scientist_ports, lab_port = allocate_ports(len(squad))
    squad["_oracle_port"] = oracle_port

    ordered = list(squad.items())
    scientist_cfg: Dict[str, Dict[str, Any]] = {}
    for (name, data), port in zip(ordered, scientist_ports):
        if name.startswith("_"):
            continue
        scientist_cfg[name] = {**data, "port": port}

    print(f"\n🔥 FORGING LAB: {lab_id} ({profile})")
    print("=" * 55)

    ensure_vault_structure(lab_id, list(scientist_cfg.keys()))
    yaml_data = build_squad_yaml(lab_id, display_name, agenda, {**scientist_cfg, "_oracle_port": oracle_port}, profile)
    personas_path = PROJECT_ROOT / "personas" / f"{lab_id}_squad.yaml"
    _write(personas_path, _dump_squad_yaml(yaml_data))

    lab_yaml = {
        "lab_id": lab_id,
        "display_name": display_name,
        "research_agenda": agenda,
        "build_profile": profile,
        "personas_yaml": f"personas/{lab_id}_squad.yaml",
        "oracle_port": oracle_port,
        "lab_port": lab_port,
        "oracle_app": "scientists/app_oracle.py",
        "scientists": {
            name: {
                "port": data["port"],
                "app": f"scientists/forges/{lab_id}/app_{name}.py",
            }
            for name, data in scientist_cfg.items()
        },
    }
    _write(
        PROJECT_ROOT / "data" / "labs" / lab_id / "config" / "lab.yaml",
        yaml.dump(lab_yaml, default_flow_style=False, sort_keys=False),
    )

    forge_dir = forge_apps_dir(lab_id)
    for name, data in scientist_cfg.items():
        _write(forge_dir / f"app_{name}.py", _scientist_app_template(lab_id, name, data["port"]), executable=True)

    _write(PROJECT_ROOT / f"boot_{lab_id}.sh", _boot_script(lab_id, oracle_port, lab_port, scientist_cfg), executable=True)
    _write(PROJECT_ROOT / f"stop_{lab_id}.sh", _stop_script(lab_id), executable=True)
    _write(PROJECT_ROOT / f".env.{lab_id}", _env_snippet(lab_id, oracle_port, lab_port))

    print("\n" + "=" * 55)
    print(f"✅ LAB FORGED: {display_name}")
    print(f"   Oracle  :{oracle_port}")
    print(f"   Lab     :{lab_port}")
    for name, data in scientist_cfg.items():
        print(f"   {name:12} :{data['port']}  ({data.get('role', '')})")
    print()
    print("Next:")
    print(f"  ./boot_{lab_id}.sh")
    print(f"  source .env.{lab_id} && python3 run_chimera.py --status")
    print(f"  ./stop_{lab_id}.sh   # shutdown")
    print("=" * 55)
    return PROJECT_ROOT


def _stop_script(lab_id: str) -> str:
    return f'''#!/usr/bin/env bash
# Stop forged lab: {lab_id}
cd "$(dirname "$0")"
set +e
echo "🛑 Stopping {lab_id}..."

if [[ -f ".env.{lab_id}" ]]; then
    set -a; source ".env.{lab_id}"; set +a
fi

pkill -f "scientists/forges/{lab_id}/" 2>/dev/null
pkill -f "LAB_ID={lab_id}.*app_oracle" 2>/dev/null
pkill -f "LAB_ID={lab_id}.*app_lab" 2>/dev/null

if [[ -n "${{LAB_PORT:-}}" ]]; then
    fuser -k "${{LAB_PORT}}/tcp" 2>/dev/null
fi
if [[ -n "${{ORACLE_PORT:-}}" ]]; then
    fuser -k "${{ORACLE_PORT}}/tcp" 2>/dev/null
fi

echo "✅ {lab_id} stopped."
'''


def list_labs_command() -> None:
    """Print the example lab + all forged labs."""
    print("=" * 60)
    print("GETAILAB LABS")
    print("=" * 60)
    print(f"  example (reference)  Oracle :5024  Lab :5035  boot: ./boot_example.sh")
    for cfg in list_forged_labs():
        if cfg.get("lab_id") == "example":
            continue
        lid = cfg.get("lab_id", "?")
        name = cfg.get("display_name", lid)
        op = cfg.get("oracle_port", "?")
        lp = cfg.get("lab_port", "?")
        n = len(cfg.get("scientists") or {})
        boot = PROJECT_ROOT / f"boot_{lid}.sh"
        boot_hint = f"./boot_{lid}.sh" if boot.is_file() else "(no boot script)"
        print(f"  {lid:16} {name[:28]:28}  Oracle :{op}  Lab :{lp}  ({n} scientists)  {boot_hint}")
    print("=" * 60)
    print("Use:  export LAB_ID=<id>  &&  source .env.<id>  &&  python3 run_chimera.py")


def interactive_wizard() -> None:
    print("=" * 60)
    print("🔥 GETAILAB LAB FORGE — build your research division")
    print("=" * 60)

    mode = input(
        "\nSetup mode:\n"
        "  1. Persona Builder (recommended — auto-research + rich prompts)\n"
        "  2. Quick forge (manual fields only)\n"
        "Mode [1/2] (default 1): "
    ).strip() or "1"
    if mode in ("1", "persona", "builder", "p"):
        scripts_dir = Path(__file__).resolve().parent
        if str(scripts_dir) not in sys.path:
            sys.path.insert(0, str(scripts_dir))
        from persona_builder import interactive_forge_wizard
        interactive_forge_wizard()
        return

    raw_id = input("Lab ID (e.g. cyber_lab, biotech_research): ").strip()
    lab_id = _slug(raw_id) if raw_id else "custom_lab"
    if lab_id == "example":
        print("  ⚠️  'example' is the sacred reference lab — pick another ID.")
        lab_id = "custom_lab"

    display_name = input("Display name (e.g. Cyber Threat Research Division): ").strip()
    if not display_name:
        display_name = lab_id.replace("_", " ").title()

    agenda = input("Core research agenda: ").strip() or "General systems and AI research"

    print("\nBuild profile:")
    print("  1. research  — full GetAiLab stack (vault, books, tickets)")
    print("  2. canvas    — thin personas, fast custom squad (uni_lab style)")
    prof_raw = input("Profile [1/2] (default 1): ").strip() or "1"
    profile = "canvas" if prof_raw in ("2", "canvas") else "research"

    while True:
        try:
            num = int(input("\nHow many scientists? (1–10): ").strip() or "3")
            if 1 <= num <= 10:
                break
            print("  Enter 1–10.")
        except ValueError:
            print("  Invalid number.")

    squad: Dict[str, Dict[str, Any]] = {}
    for i in range(num):
        print(f"\n--- Scientist {i + 1} ---")
        name = _slug(input("Name (e.g. tesla, rosalind): ").strip() or f"agent_{i + 1}")
        role = input("Role (e.g. RF Security Analyst): ").strip() or "Research Scientist"
        persona = input("Focus / persona: ").strip() or role
        squad[name] = {"role": role, "persona": persona}

    print("\n" + "=" * 60)
    print(f"  Lab:     {lab_id}")
    print(f"  Profile: {profile}")
    print(f"  Squad:   {', '.join(squad)}")
    print("  Ports auto-allocated (won't clash with the example lab 5024–5040)")
    print("=" * 60)
    input("Press ENTER to forge...")
    forge_lab(lab_id, display_name, agenda, squad, profile)


def main():
    parser = argparse.ArgumentParser(description="Forge a custom GetAiLab research division")
    parser.add_argument("--lab-id", help="Lab identifier (snake_case)")
    parser.add_argument("--display-name", default="")
    parser.add_argument("--agenda", default="General research")
    parser.add_argument("--profile", choices=("research", "canvas"), default="research")
    parser.add_argument("--scientists-json", help='JSON dict: {"tesla":{"role":"...","persona":"..."}}')
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--list-labs", action="store_true", help="Show the example lab + forged labs")
    args = parser.parse_args()

    if args.list_labs:
        list_labs_command()
        return

    if args.lab_id and (args.non_interactive or args.scientists_json):
        squad = json.loads(args.scientists_json) if args.scientists_json else {
            "alpha": {"role": "Lead Researcher", "persona": "Systems analysis"},
            "beta": {"role": "Data Scientist", "persona": "Statistical modeling"},
        }
        forge_lab(
            _slug(args.lab_id),
            args.display_name or args.lab_id.replace("_", " ").title(),
            args.agenda,
            squad,
            args.profile,
        )
        return

    interactive_wizard()


if __name__ == "__main__":
    main()