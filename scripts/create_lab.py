#!/usr/bin/env python3
"""
GetAiLab Lab Forge — merged from uni_lab.py wizard + the example lab engine.

Generates a custom research lab into the engine tree (and optionally the
commercial products root).

Profiles:
  canvas   — thin personas, fast custom squad (uni_lab style)
  research — full vault + tickets + library + rich YAML personas

Destinations:
  product  — commercial SKU under GETAILAB_PRODUCTS_ROOT (default)
             vault + personas live in getailab-products/<id>/; engine gets symlinks
  engine   — vault only under github/data/labs/<id>/ (example / public starter)
  private  — founder R&D under GETAILAB_PRIVATE/labs (Chimera-class only)

Usage:
    python3 scripts/create_lab.py
    python3 scripts/create_lab.py --lab-id university --product --profile research --non-interactive ...
    python3 scripts/create_lab.py --lab-id toy --engine --non-interactive ...
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
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
from getailab.forge_defaults import (  # noqa: E402
    canvas_oracle_prompt,
    canvas_system_prompt,
    enrich_squad_yaml_meta,
    research_oracle_prompt,
    research_system_prompt,
)

# Commercial product root — never put client SKUs in getailab-private/labs by default
PRODUCTS_ROOT = Path(
    os.environ.get("GETAILAB_PRODUCTS_ROOT")
    or os.environ.get("GETAILAB_PRODUCTS")
    or "/home/deadly/x/getailab-products"
)
PRIVATE_ROOT = Path(
    os.environ.get("GETAILAB_PRIVATE")
    or "/home/deadly/x/getailab-private"
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
    try:
        shown = path.relative_to(PROJECT_ROOT)
    except ValueError:
        shown = path
    print(f"  [+] {shown}")


def build_squad_yaml(
    lab_id: str,
    display_name: str,
    agenda: str,
    squad: Dict[str, Dict[str, Any]],
    profile: str,
) -> dict:
    """Build squad YAML. Research profile gets Chimera-depth + ai_dev outcome laws."""
    oracle_port = int(squad.get("_oracle_port", 5024))
    scientist_names = [n for n in squad.keys() if not str(n).startswith("_")]
    peers = ", ".join(scientist_names) if scientist_names else "your squad peers"

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
        implement_focus = data.get("implement_focus") or (
            (persona[:200] if persona else "data analysis and simulation")
            + " | emit RESULT PASS/FAIL; prefer product/ landings; import don't rewrite"
        )
        if data.get("system_prompt"):
            system_prompt = data["system_prompt"]
        elif profile == "canvas":
            system_prompt = canvas_system_prompt(
                name=name, role=display_role, persona=persona, agenda=agenda
            )
        else:
            system_prompt = research_system_prompt(
                name=name,
                role=display_role,
                persona=persona,
                agenda=agenda,
                lab_id=lab_id,
                peers=peers,
            )
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
        # Chimera-compatible optional fields (research density)
        if profile == "research":
            entry.setdefault(
                "contribution_to_loops",
                data.get("contribution_to_loops")
                or f"Primary {display_role} lens for lab {lab_id}. Produces testable claims and artifacts.",
            )
            entry.setdefault(
                "example_interactions",
                data.get("example_interactions")
                or [
                    "Show the baseline and the metric — or it is theatre.",
                    "Import the existing product package; rewrites are process FAIL.",
                    "RESULT FAIL with sys.exit(1) is honest when the claim dies.",
                ],
            )
        members.append(entry)

    if profile == "canvas":
        oracle_prompt = canvas_oracle_prompt(agenda=agenda)
    else:
        oracle_prompt = research_oracle_prompt(
            agenda=agenda, lab_id=lab_id, squad_names=scientist_names
        )
    members.append({
        "name": "oracle",
        "port": oracle_port,
        "role": "orchestrator",
        "display_role": "Process Orchestrator & Consensus Weaver",
        "expertise": [
            "synthesis",
            "loop coordination",
            "SHIP/NO-SHIP decisions",
            "plain-text next problems",
            "anti-circle enforcement",
        ],
        "implement_focus": (
            "Consensus artefact + three paste-ready next problems (no ###, no stars). "
            "Owners only from this lab's squad. Name product paths and smoke commands."
        ),
        "system_prompt": oracle_prompt,
        "contribution_to_loops": (
            "Closes loops with audit-grade consensus; clean next problems; "
            "rejects hollow PASS and rewrite culture."
        ),
        "example_interactions": [
            "Scoreboard first: quote RESULT lines and artifact paths.",
            "Next problem: plain text only — no markdown headers or stars.",
            "Leads must be this lab's scientist names only.",
        ],
    })

    yaml_data = {
        "version": "2.0" if profile == "research" else "1.0",
        "project": f"GetAiLab — {display_name}",
        "squad_name": display_name,
        "research_agenda": agenda,
        "build_profile": profile,
        "lab_id": lab_id,
        "squad": members,
    }
    return enrich_squad_yaml_meta(
        yaml_data,
        profile=profile,
        lab_id=lab_id,
        display_name=display_name,
        agenda=agenda,
    )


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
# Base .env often pins LAB_ID=chimera — set lab identity AFTER sourcing it.
cd "$(dirname "$0")"
set -e

if [[ -f .env ]]; then
    set -a; source .env; set +a
fi
# example lab uses .env.example_lab so we never clobber install template .env.example
_LAB_ENV=".env.{lab_id}"
if [[ "{lab_id}" == "example" ]]; then
    _LAB_ENV=".env.example_lab"
fi
if [[ -f "$_LAB_ENV" ]]; then
    set -a; source "$_LAB_ENV"; set +a
fi
# Lab identity always wins (belt + braces even if lab env file missing)
export LAB_ID="{lab_id}"
export PERSONAS_YAML="personas/{lab_id}_squad.yaml"
export ORACLE_PORT={oracle_port}
export LAB_PORT={lab_port}
export ORACLE_URL="http://localhost:{oracle_port}"
export LAB_URL="http://localhost:{lab_port}"

echo "🧪 LAB_ID=$LAB_ID  PERSONAS_YAML=$PERSONAS_YAML  Oracle :$ORACLE_PORT  Lab :$LAB_PORT"
echo "   machine APIs open: /execute /literature /vision /web  (dashboard HTML still gated)"

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
echo "   Prefer:  ./run_{lab_id}.sh --status"
echo "   Manual:  set -a; source .env; source $_LAB_ENV; set +a && python3 run_lab.py"
echo "   Gate:    dashboard HTML may be passworded; /execute + /literature stay open (shared app_lab)."
'''


def lab_env_filename(lab_id: str) -> str:
    """Lab identity env file. Never clobber install template ``.env.example``."""
    if lab_id == "example":
        return ".env.example_lab"
    return f".env.{lab_id}"


def _env_snippet(lab_id: str, oracle_port: int, lab_port: int) -> str:
    note = ""
    if lab_id == "example":
        note = (
            "# NOTE: file is .env.example_lab (not .env.example) so the install "
            "template stays intact.\n"
        )
    return f'''# Forged lab: {lab_id}
# Source AFTER base .env so LAB_ID is not stolen by another lab pin.
{note}LAB_ID={lab_id}
PERSONAS_YAML=personas/{lab_id}_squad.yaml
ORACLE_PORT={oracle_port}
LAB_PORT={lab_port}
ORACLE_URL=http://localhost:{oracle_port}
LAB_URL=http://localhost:{lab_port}
JOB_TICKETS_DB=data/labs/{lab_id}/job_tickets.db
# Interactive Commander menu after synthesis (ai_dev dial-in default)
# Leave empty so run_lab pauses for 1/2/3/o/d/p/t/c/q
GETAILAB_LOOP_ONCE=
GETAILAB_HANDOFF_AUTO=
'''


def _run_script(lab_id: str, oracle_port: int, lab_port: int, scientist_names: Optional[List[str]] = None) -> str:
    """Commander wrapper — layers lab env after base .env so another LAB_ID cannot steal the loop."""
    names = " ".join(scientist_names or [])
    squad_hint = f'echo "   expected squad: {names}"\n' if names else ""
    env_file = lab_env_filename(lab_id)
    personas = (
        "personas/chimera_squad.yaml"
        if lab_id in ("chimera", "chimera_clone")
        else f"personas/{lab_id}_squad.yaml"
    )
    return f'''#!/usr/bin/env bash
# Commander for lab: {lab_id}
# Always layers {env_file} AFTER base .env so another LAB_ID pin cannot steal the loop.
# Lab sandbox machine routes (/execute, /literature, /vision, /web) stay open under the
# dashboard password gate — see lab/app_lab.py _GATE_OPEN_PREFIXES (all labs share app_lab).
set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a; source .env; set +a
fi
if [[ ! -f {env_file} ]]; then
  echo "❌ missing {env_file} — forge first (python3 scripts/create_lab.py)"
  exit 1
fi
set -a; source {env_file}; set +a

# Belt + braces — never inherit another lab from the parent shell
export LAB_ID={lab_id}
export PERSONAS_YAML={personas}
export ORACLE_PORT="${{ORACLE_PORT:-{oracle_port}}}"
export LAB_PORT="${{LAB_PORT:-{lab_port}}}"
export ORACLE_URL="${{ORACLE_URL:-http://localhost:{oracle_port}}}"
export LAB_URL="${{LAB_URL:-http://localhost:{lab_port}}}"
export JOB_TICKETS_DB="${{JOB_TICKETS_DB:-data/labs/{lab_id}/job_tickets.db}}"

# ai_dev dial-in default: pause after Oracle for Commander menu (1/2/3/o/d/p/t/c/q)
# Only force one-shot when user exports FORCE_LAB_LOOP_ONCE=1
if [[ "${{FORCE_LAB_LOOP_ONCE:-}}" != "1" ]]; then
  unset GETAILAB_LOOP_ONCE
  unset GETAILAB_HANDOFF_AUTO
  export GETAILAB_LOOP_ONCE=
  export GETAILAB_HANDOFF_AUTO=
fi

echo "🧪 run_{lab_id} · LAB_ID=$LAB_ID · Oracle $ORACLE_URL · Lab $LAB_URL"
echo "   after synthesis: 1/2/3 · o · d · p · t · c · q  (LOOP_ONCE cleared unless FORCE_LAB_LOOP_ONCE=1)"
{squad_hint}exec python3 run_lab.py "$@"
'''


def _symlink(link: Path, target: Path) -> None:
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        if link.is_dir() and not link.is_symlink():
            shutil.rmtree(link)
        else:
            link.unlink()
    link.symlink_to(target)
    print(f"  [link] {link.relative_to(PROJECT_ROOT)} → {target}")


def _seed_product_pack(lab_id: str, display_name: str, agenda: str, version: str = "0.1.0-draft") -> Path:
    """Minimal commercial pack skeleton under getailab-products/<lab_id>/."""
    root = PRODUCTS_ROOT / lab_id
    pack = root / "pack"
    for sub in (
        "pack/sample_loop",
        "pack/acceptance",
        "release",
        "personas",
        "vault",
    ):
        (root / sub).mkdir(parents=True, exist_ok=True)
    product_yaml = {
        "sku": lab_id,
        "display_name": display_name,
        "version": version,
        "lab_id": lab_id,
        "scientist_count": 5,
        "session_preset": "research_open",
        "deployment": "self_hosted",
        "data_residency": "buyer_environment",
        "llm_policy": "buyer_controlled",
        "build_profile": "research",
        "pack_status": "drafting",
        "research_agenda": agenda,
        "non_goals": [
            "clinical_decision_support",
            "public_multi_tenant_saas",
            "compliance_certification_claims",
        ],
    }
    _write(root / "PRODUCT.yaml", yaml.dump(product_yaml, default_flow_style=False, sort_keys=False))
    readme = pack / "README.md"
    if not readme.is_file():
        _write(
            readme,
            f"# {display_name} pack\n\n"
            f"See `getailab-private/business/commercial/CLIENT_PACKAGE_STANDARD.md`.\n"
            f"Fill INSTALL, PROCUREMENT_ONEPAGER, SECURITY_POSTURE, ACCEPTANCE.\n",
        )
    return root


def forge_lab(
    lab_id: str,
    display_name: str,
    agenda: str,
    squad: Dict[str, Dict[str, Any]],
    profile: str = "research",
    destination: str = "product",
) -> Path:
    """Generate all artifacts for a new lab. Returns project root.

    destination:
      product — commercial (default): getailab-products/<id>/ + engine symlinks
      engine  — github/data/labs only (public example style)
      private — getailab-private/labs (founder R&D only)
    """
    if destination not in ("product", "engine", "private"):
        raise ValueError(f"destination must be product|engine|private, got {destination!r}")
    if lab_id in ("chimera", "chimera_clone", "old_mate") and destination == "product":
        print("  ⚠️  R&D lab_id forced to destination=private")
        destination = "private"

    oracle_port, scientist_ports, lab_port = allocate_ports(len(squad))
    squad["_oracle_port"] = oracle_port

    ordered = list(squad.items())
    scientist_cfg: Dict[str, Dict[str, Any]] = {}
    for (name, data), port in zip(ordered, scientist_ports):
        if name.startswith("_"):
            continue
        scientist_cfg[name] = {**data, "port": port}

    print(f"\n🔥 FORGING LAB: {lab_id} ({profile}, destination={destination})")
    print("=" * 55)

    sci_names = list(scientist_cfg.keys())
    yaml_data = build_squad_yaml(
        lab_id, display_name, agenda, {**scientist_cfg, "_oracle_port": oracle_port}, profile
    )
    lab_yaml = {
        "lab_id": lab_id,
        "display_name": display_name,
        "research_agenda": agenda,
        "build_profile": profile,
        "personas_yaml": f"personas/{lab_id}_squad.yaml",
        "oracle_port": oracle_port,
        "lab_port": lab_port,
        "oracle_app": "scientists/app_oracle.py",
        "destination": destination,
        "scientists": {
            name: {
                "port": data["port"],
                "app": f"scientists/forges/{lab_id}/app_{name}.py",
            }
            for name, data in scientist_cfg.items()
        },
    }

    if destination == "product":
        PRODUCTS_ROOT.mkdir(parents=True, exist_ok=True)
        prod_root = _seed_product_pack(lab_id, display_name, agenda)
        vault_root = prod_root / "vault"
        # Build vault tree under products
        for sub in ("config", "artifacts", "codex", "merkle", "signatures", "keys", "reports"):
            (vault_root / sub).mkdir(parents=True, exist_ok=True)
        for name in sci_names:
            (vault_root / "scientists" / name / "book" / "pages").mkdir(parents=True, exist_ok=True)
        personas_real = prod_root / "personas" / f"{lab_id}_squad.yaml"
        _write(personas_real, _dump_squad_yaml(yaml_data))
        _write(vault_root / "config" / "lab.yaml", yaml.dump(lab_yaml, default_flow_style=False, sort_keys=False))
        # Engine sees vault + personas via symlink (never private/labs)
        _symlink(PROJECT_ROOT / "data" / "labs" / lab_id, vault_root)
        _symlink(PROJECT_ROOT / "personas" / f"{lab_id}_squad.yaml", personas_real)
        print(f"  [product] {prod_root}")
    elif destination == "private":
        priv_vault = PRIVATE_ROOT / "labs" / lab_id
        for sub in ("config", "artifacts", "codex", "merkle", "signatures", "keys", "reports"):
            (priv_vault / sub).mkdir(parents=True, exist_ok=True)
        for name in sci_names:
            (priv_vault / "scientists" / name / "book" / "pages").mkdir(parents=True, exist_ok=True)
        priv_persona = PRIVATE_ROOT / "personas" / f"{lab_id}_squad.yaml"
        priv_persona.parent.mkdir(parents=True, exist_ok=True)
        _write(priv_persona, _dump_squad_yaml(yaml_data))
        _write(priv_vault / "config" / "lab.yaml", yaml.dump(lab_yaml, default_flow_style=False, sort_keys=False))
        _symlink(PROJECT_ROOT / "data" / "labs" / lab_id, priv_vault)
        _symlink(PROJECT_ROOT / "personas" / f"{lab_id}_squad.yaml", priv_persona)
        print(f"  [private R&D] {priv_vault}")
    else:
        ensure_vault_structure(lab_id, sci_names)
        personas_path = PROJECT_ROOT / "personas" / f"{lab_id}_squad.yaml"
        _write(personas_path, _dump_squad_yaml(yaml_data))
        _write(
            PROJECT_ROOT / "data" / "labs" / lab_id / "config" / "lab.yaml",
            yaml.dump(lab_yaml, default_flow_style=False, sort_keys=False),
        )

    forge_dir = forge_apps_dir(lab_id)
    for name, data in scientist_cfg.items():
        _write(forge_dir / f"app_{name}.py", _scientist_app_template(lab_id, name, data["port"]), executable=True)

    env_name = lab_env_filename(lab_id)
    _write(PROJECT_ROOT / f"boot_{lab_id}.sh", _boot_script(lab_id, oracle_port, lab_port, scientist_cfg), executable=True)
    _write(PROJECT_ROOT / f"stop_{lab_id}.sh", _stop_script(lab_id), executable=True)
    _write(PROJECT_ROOT / f"run_{lab_id}.sh", _run_script(lab_id, oracle_port, lab_port, sci_names), executable=True)
    _write(PROJECT_ROOT / env_name, _env_snippet(lab_id, oracle_port, lab_port))

    print("\n" + "=" * 55)
    print(f"✅ LAB FORGED: {display_name}")
    print(f"   destination: {destination}")
    print(f"   Oracle  :{oracle_port}")
    print(f"   Lab     :{lab_port}")
    for name, data in scientist_cfg.items():
        print(f"   {name:12} :{data['port']}  ({data.get('role', '')})")
    print()
    print("Next:")
    print(f"  ./boot_{lab_id}.sh")
    print(f"  ./run_{lab_id}.sh --status")
    print(f"  ./run_{lab_id}.sh --problem \"...\"")
    print(f"  ./stop_{lab_id}.sh   # shutdown")
    print(f"  Env file: {env_name}")
    if destination == "product":
        print(f"  Product:  {PRODUCTS_ROOT / lab_id}")
        print("  Doctrine: getailab-private/business/commercial/")
    print("  Note: dashboard password gates HTML only; /execute + /literature stay open (all labs).")
    print("=" * 55)
    return PROJECT_ROOT


def _stop_script(lab_id: str) -> str:
    env_file = lab_env_filename(lab_id)
    return f'''#!/usr/bin/env bash
# Stop forged lab: {lab_id}
cd "$(dirname "$0")"
set +e
echo "🛑 Stopping {lab_id}..."

if [[ -f "{env_file}" ]]; then
    set -a; source "{env_file}"; set +a
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
    print("Use:  export LAB_ID=<id>  &&  source .env.<id>  &&  python3 run_lab.py")


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
    dest = parser.add_mutually_exclusive_group()
    dest.add_argument(
        "--product",
        action="store_true",
        help="Commercial SKU under GETAILAB_PRODUCTS_ROOT (default for new forges)",
    )
    dest.add_argument(
        "--engine",
        action="store_true",
        help="Vault only under github/data/labs (public/example style)",
    )
    dest.add_argument(
        "--private",
        action="store_true",
        help="Founder R&D under getailab-private/labs (Chimera-class)",
    )
    args = parser.parse_args()

    if args.list_labs:
        list_labs_command()
        return

    if args.private:
        destination = "private"
    elif args.engine:
        destination = "engine"
    else:
        # default commercial — product (even without --product flag when non-interactive)
        destination = "product"

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
            destination=destination,
        )
        return

    interactive_wizard()


if __name__ == "__main__":
    main()