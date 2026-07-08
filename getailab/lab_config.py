"""
Lab configuration — multi-lab support for GetAiLab / Project Chimera.

Chimera remains the default reference lab. Forged labs live under
data/labs/<lab_id>/config/lab.yaml with scientist apps in scientists/forges/<lab_id>/.
"""

from __future__ import annotations

import json
import os
import socket
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_LABS = PROJECT_ROOT / "data" / "labs"
PERSONAS_DIR = PROJECT_ROOT / "personas"

# Chimera reference ports (do not collide when allocating new labs)
CHIMERA_ORACLE_PORT = 5024
CHIMERA_LAB_PORT = 5035
CHIMERA_SCIENTIST_PORTS = {
    "albert": 5025,
    "andrew": 5026,
    "alan": 5027,
    "carl": 5028,
    "emmy": 5029,
    "tesla": 5030,
    "brian": 5032,
    "neil": 5034,
    "roger": 5038,
    "bohr": 5039,
    "heisenberg": 5040,
}


def get_project_root() -> Path:
    return PROJECT_ROOT


def get_lab_id() -> str:
    return os.getenv("LAB_ID", "chimera").strip() or "chimera"


def is_chimera_lab(lab_id: Optional[str] = None) -> bool:
    return (lab_id or get_lab_id()) == "chimera"


def lab_vault_path(lab_id: Optional[str] = None) -> Path:
    """Library vault root — always data/labs/<lab_id>/ (Chimera included)."""
    return DATA_LABS / (lab_id or get_lab_id())


def lab_reports_dir(lab_id: Optional[str] = None) -> Path:
    """
    Loop report markdown search path.
    Chimera: project root + docs/loops (legacy).
    Forged labs: data/labs/<id>/reports/ only — never Chimera's loop_*.md files.
    """
    lid = lab_id or get_lab_id()
    if is_chimera_lab(lid):
        return PROJECT_ROOT
    return DATA_LABS / lid / "reports"


def resolve_lab_paths(lab_id: Optional[str] = None) -> Dict[str, Any]:
    """Canonical per-lab filesystem roots — use everywhere to avoid cross-department bleed."""
    lid = lab_id or get_lab_id()
    reports = lab_reports_dir(lid)
    report_search_dirs = [reports]
    if is_chimera_lab(lid):
        report_search_dirs.append(PROJECT_ROOT / "docs" / "loops")
    return {
        "lab_id": lid,
        "vault": str(lab_vault_path(lid)),
        "artifacts": str(lab_artifacts_dir(lid)),
        "results_db": str(lab_results_db_path(lid)),
        "agora_db": str(agora_db_path(lid)),
        "reports_dir": str(reports),
        "report_search_dirs": [str(p) for p in report_search_dirs],
        "is_chimera": is_chimera_lab(lid),
    }


def lab_config_path(lab_id: Optional[str] = None) -> Path:
    lid = lab_id or get_lab_id()
    return DATA_LABS / lid / "config" / "lab.yaml"


def personas_yaml_path(lab_id: Optional[str] = None) -> Path:
    explicit = os.getenv("PERSONAS_YAML", "").strip()
    if explicit:
        p = Path(explicit)
        return p if p.is_absolute() else PROJECT_ROOT / p
    lid = lab_id or get_lab_id()
    if lid == "chimera":
        return PERSONAS_DIR / "chimera_squad.yaml"
    return PERSONAS_DIR / f"{lid}_squad.yaml"


def _port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except OSError:
        return False


def _load_yaml_file(path: Path) -> Dict[str, Any]:
    if not path.is_file() or yaml is None:
        return {}
    with open(path, "r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    return data if isinstance(data, dict) else {}


def _chimera_default_config() -> Dict[str, Any]:
    scientists = {
        name: {"port": port, "app": f"scientists/app_{name}.py"}
        for name, port in CHIMERA_SCIENTIST_PORTS.items()
    }
    return {
        "lab_id": "chimera",
        "display_name": "Project Chimera — Quantum Research Division",
        "research_agenda": "Quantum cognition, landscape engine, dialectic research",
        "build_profile": "reference",
        "personas_yaml": "personas/chimera_squad.yaml",
        "oracle_port": CHIMERA_ORACLE_PORT,
        "lab_port": CHIMERA_LAB_PORT,
        "oracle_app": "scientists/app_oracle.py",
        "scientists": scientists,
    }


def load_lab_config(lab_id: Optional[str] = None) -> Dict[str, Any]:
    """Load lab.yaml for lab_id, or Chimera defaults."""
    lid = lab_id or get_lab_id()
    path = lab_config_path(lid)
    if path.is_file():
        cfg = _load_yaml_file(path)
        cfg.setdefault("lab_id", lid)
        return cfg
    if lid == "chimera":
        return _chimera_default_config()
    return {"lab_id": lid}


def get_scientists_dict(lab_id: Optional[str] = None) -> Dict[str, int]:
    """Name → port map for active lab (excludes oracle)."""
    cfg = load_lab_config(lab_id)
    scientists = cfg.get("scientists") or {}
    out: Dict[str, int] = {}
    for name, spec in scientists.items():
        if name.lower() == "oracle":
            continue
        if isinstance(spec, dict):
            out[name.lower()] = int(spec.get("port", 0))
        elif isinstance(spec, int):
            out[name.lower()] = spec
    if out:
        return out
    if (lab_id or get_lab_id()) == "chimera":
        return dict(CHIMERA_SCIENTIST_PORTS)
    return {}


def get_service_urls(lab_id: Optional[str] = None) -> Tuple[str, str]:
    cfg = load_lab_config(lab_id)
    oracle_port = int(cfg.get("oracle_port", CHIMERA_ORACLE_PORT))
    lab_port = int(cfg.get("lab_port", CHIMERA_LAB_PORT))
    oracle_url = os.getenv("ORACLE_URL", f"http://localhost:{oracle_port}").rstrip("/")
    lab_url = os.getenv("LAB_URL", f"http://localhost:{lab_port}").rstrip("/")
    return oracle_url, lab_url


def list_forged_labs() -> List[Dict[str, Any]]:
    """All labs with config/lab.yaml under data/labs/."""
    labs: List[Dict[str, Any]] = []
    if not DATA_LABS.is_dir():
        return labs
    for child in sorted(DATA_LABS.iterdir()):
        if not child.is_dir():
            continue
        cfg_path = child / "config" / "lab.yaml"
        if cfg_path.is_file():
            cfg = _load_yaml_file(cfg_path)
            cfg.setdefault("lab_id", child.name)
            labs.append(cfg)
    return labs


def scan_used_ports() -> set:
    """Ports reserved in any lab config plus Chimera defaults."""
    used = {CHIMERA_ORACLE_PORT, CHIMERA_LAB_PORT, *CHIMERA_SCIENTIST_PORTS.values()}
    for lab in list_forged_labs():
        used.add(int(lab.get("oracle_port", 0)))
        used.add(int(lab.get("lab_port", 0)))
        for spec in (lab.get("scientists") or {}).values():
            if isinstance(spec, dict):
                used.add(int(spec.get("port", 0)))
    return {p for p in used if p > 0}


def port_listening(port: int) -> bool:
    """True if something is accepting connections on 127.0.0.1:port."""
    return _port_open(port)


def lab_port_map(lab_id: Optional[str] = None) -> Dict[str, int]:
    """Named ports for a lab (oracle, lab, scientist names)."""
    cfg = load_lab_config(lab_id)
    lid = lab_id or cfg.get("lab_id", "chimera")
    out: Dict[str, int] = {
        "oracle": int(cfg.get("oracle_port", CHIMERA_ORACLE_PORT)),
        "lab": int(cfg.get("lab_port", CHIMERA_LAB_PORT)),
    }
    for name, spec in (cfg.get("scientists") or {}).items():
        if name.lower() == "oracle":
            continue
        if isinstance(spec, dict):
            out[name.lower()] = int(spec.get("port", 0))
        elif isinstance(spec, int):
            out[name.lower()] = spec
    return {k: v for k, v in out.items() if v > 0}


def enumerate_all_labs() -> List[Dict[str, Any]]:
    """Chimera + every forged lab with live port status."""
    labs: List[Dict[str, Any]] = []
    chimera = _chimera_default_config()
    chimera["vault"] = str(DATA_LABS / "chimera")
    chimera["boot_script"] = "boot_chimera.sh"
    ports = lab_port_map("chimera")
    chimera["ports"] = ports
    chimera["oracle_live"] = port_listening(ports["oracle"])
    chimera["lab_live"] = port_listening(ports["lab"])
    chimera["any_live"] = chimera["oracle_live"] or chimera["lab_live"] or any(
        port_listening(p) for k, p in ports.items() if k not in ("oracle", "lab")
    )
    labs.append(chimera)

    for cfg in list_forged_labs():
        lid = cfg.get("lab_id", "")
        if not lid or lid == "chimera":
            continue
        entry = dict(cfg)
        entry.setdefault("vault", str(DATA_LABS / lid))
        boot = PROJECT_ROOT / f"boot_{lid}.sh"
        entry["boot_script"] = f"boot_{lid}.sh" if boot.is_file() else None
        ports = lab_port_map(lid)
        entry["ports"] = ports
        entry["oracle_live"] = port_listening(ports.get("oracle", 0))
        entry["lab_live"] = port_listening(ports.get("lab", 0))
        entry["any_live"] = entry["oracle_live"] or entry["lab_live"] or any(
            port_listening(p) for k, p in ports.items() if k not in ("oracle", "lab")
        )
        labs.append(entry)
    return labs


def preview_port_block(num_scientists: int) -> Dict[str, Any]:
    """Show the next free port block allocate_ports() would assign."""
    oracle, scientist_ports, lab_port = allocate_ports(num_scientists)
    return {
        "oracle_port": oracle,
        "lab_port": lab_port,
        "scientist_ports": scientist_ports,
        "scientist_count": num_scientists,
    }


def allocate_ports(num_scientists: int) -> Tuple[int, List[int], int]:
    """
    Find a non-colliding port block for a new lab.
    Block layout: oracle, scientist×N, gap, lab sandbox.
    """
    used = scan_used_ports()
    for base in range(5124, 5900, 20):
        oracle = base
        scientist_ports = [base + 1 + i for i in range(num_scientists)]
        lab_port = base + 11
        candidates = [oracle, lab_port, *scientist_ports]
        if any(p in used for p in candidates):
            continue
        if any(_port_open(p) for p in candidates):
            continue
        return oracle, scientist_ports, lab_port
    raise RuntimeError("No free port block found (5124–5900). Stop other labs or free ports.")


def forge_apps_dir(lab_id: str) -> Path:
    return PROJECT_ROOT / "scientists" / "forges" / lab_id


def agora_db_path(lab_id: Optional[str] = None) -> Path:
    """Per-lab loop DB — Chimera uses project-root chimera_lab.db; forged labs use vault agora.db."""
    lid = lab_id or get_lab_id()
    if lid == "chimera":
        return PROJECT_ROOT / "chimera_lab.db"
    return DATA_LABS / lid / "agora.db"


def lab_results_db_path(lab_id: Optional[str] = None) -> Path:
    """Per-lab sandbox execution DB (lab_experiments). Chimera keeps lab/lab_results.db."""
    lid = lab_id or get_lab_id()
    if lid == "chimera":
        return PROJECT_ROOT / "lab" / "lab_results.db"
    return DATA_LABS / lid / "lab_results.db"


def lab_artifacts_dir(lab_id: Optional[str] = None) -> Path:
    """Per-lab experiment workspace. Chimera keeps lab/artifacts/."""
    lid = lab_id or get_lab_id()
    if lid == "chimera":
        return PROJECT_ROOT / "lab" / "artifacts"
    return DATA_LABS / lid / "artifacts"


def ensure_lab_results_db(lab_id: Optional[str] = None) -> Path:
    """Create lab_experiments table in the active lab's results DB."""
    import sqlite3

    path = lab_results_db_path(lab_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=10)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS lab_experiments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loop_id TEXT,
            agent_name TEXT,
            experiment_name TEXT,
            code TEXT,
            stdout TEXT,
            stderr TEXT,
            success BOOLEAN,
            execution_time_ms INTEGER,
            artifacts_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()
    return path


def ensure_scientist_vault(lab_id: str, scientist_names: List[str]) -> None:
    """Empty book/skills dirs for each squad member (isolated from other labs)."""
    for name in scientist_names:
        n = name.lower().strip()
        if not n or n == "oracle":
            continue
        book = DATA_LABS / lab_id / "scientists" / n / "book"
        for sub in ("pages", "skills"):
            (book / sub).mkdir(parents=True, exist_ok=True)
        manifest = book / "manifest.json"
        if not manifest.exists():
            manifest.write_text(
                json.dumps({"scientist": n, "lab_id": lab_id, "pages": [], "skills": []}, indent=2) + "\n",
                encoding="utf-8",
            )


def ensure_vault_structure(lab_id: str, scientist_names: Optional[List[str]] = None) -> Path:
    base = DATA_LABS / lab_id
    for sub in ("config", "scientists", "codex/book/pages", "artifacts", "reports", "merkle", "keys", "signatures"):
        (base / sub).mkdir(parents=True, exist_ok=True)
    manifest = base / "manifest.json"
    if not manifest.exists():
        manifest.write_text('{"loops": []}\n', encoding="utf-8")
    if lab_id != "chimera":
        ensure_lab_results_db(lab_id)
    if scientist_names:
        ensure_scientist_vault(lab_id, scientist_names)
    return base