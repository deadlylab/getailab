"""
Loop focus modes — bias dialectic toward development vs open research fluff.

Env:
  GETAILAB_LOOP_MODE=research|build|audit   (default: research)
  GETAILAB_DEV_FOCUS=1                      (alias for build)

Or lab.yaml:  loop_mode: build
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def _from_lab_yaml() -> Optional[str]:
    try:
        from getailab.lab_config import get_lab_id, load_lab_config

        cfg = load_lab_config(get_lab_id()) or {}
        mode = (cfg.get("loop_mode") or cfg.get("focus") or "").strip().lower()
        return mode or None
    except Exception:
        return None


def get_loop_mode() -> str:
    if os.getenv("GETAILAB_DEV_FOCUS", "").strip().lower() in ("1", "true", "yes", "on"):
        return "build"
    env = (os.getenv("GETAILAB_LOOP_MODE") or "").strip().lower()
    if env in ("research", "build", "audit", "dev", "product"):
        return "build" if env in ("dev", "product") else env
    yaml_mode = _from_lab_yaml()
    if yaml_mode in ("research", "build", "audit", "dev", "product"):
        return "build" if yaml_mode in ("dev", "product") else yaml_mode
    # Sensible defaults by lab_id
    try:
        from getailab.lab_config import get_lab_id

        lid = get_lab_id()
        if lid in ("dev_shed",):
            return "build"
        if lid in ("old_mate",):
            return "audit"
        if lid in ("mad_lab", "soundwave"):
            return "build"  # security/OSINT still want runnable demos
    except Exception:
        pass
    return "research"


def hypothesis_focus_addon() -> str:
    mode = get_loop_mode()
    if mode == "build":
        return (
            "\n\nFOCUS MODE: BUILD (anti-fluff)\n"
            "- Prefer ENGINEERING hypotheses over metaphysical essays.\n"
            "- Cap speculative physics metaphors (Orch-OR, cosmic fine-tuning, pure Jung) "
            "unless the problem explicitly asks for them — one short paragraph max if used.\n"
            "- MUST include: (1) a concrete module or interface name, "
            "(2) inputs/outputs, (3) ONE falsifiable prediction with a measurable metric, "
            "(4) what file(s) the Phase-2 script will write.\n"
            "- Prefer short hyps (300–600 words) that a coder could implement today.\n"
            "- Good: 'TPI module returns commutator matrix CSV; accuracy delta ≥X% on chain length N'.\n"
            "- Bad: multi-page manifold manifesto with no module boundary.\n"
        )
    if mode == "audit":
        return (
            "\n\nFOCUS MODE: AUDIT\n"
            "- PASS/FAIL with evidence paths. Prefer deterministic checks over philosophy.\n"
            "- Name severity, file paths, and fix options.\n"
        )
    return (
        "\n\nFOCUS MODE: RESEARCH (default)\n"
        "- Deep dialectic allowed, but still require at least one falsifiable prediction "
        "and name what Phase-2 will measure.\n"
    )


def implement_focus_addon() -> str:
    mode = get_loop_mode()
    if mode == "build":
        return (
            "\nFOCUS MODE: BUILD — IMPLEMENT HARD RULES\n"
            "- Script must be SHORT (≤80 lines) and RUN to completion.\n"
            "- MUST write ≥1 real artifact: .csv or .json (plot.png optional).\n"
            "- Prefer testing a MODULE/API contract (function in/out) over cosmic simulation.\n"
            "- If simulating tools, use a small discrete table (Read/Edit/Bash), not continuous manifolds.\n"
            "- No external network APIs unless required.\n"
            "- Print a one-line RESULT: PASS/FAIL + metric at the end.\n"
            "- Forbidden fluff: multi-page comments about consciousness; long unused sympy geometry.\n"
        )
    if mode == "audit":
        return (
            "\nFOCUS MODE: AUDIT — emit checks that print PASS/FAIL and write findings.json.\n"
        )
    return (
        "\nKeep script short and runnable; write at least one .csv/.json artifact.\n"
    )


def oracle_synthesis_addon() -> str:
    mode = get_loop_mode()
    if mode == "build":
        return (
            "\nFOCUS MODE: BUILD\n"
            "Prioritize: (1) what to implement next as a module, (2) metrics that failed/passed, "
            "(3) kill speculative threads that produced no artifacts. "
            "At least one recommended path must be a concrete engineering deliverable "
            "(file/module name + acceptance test).\n"
        )
    if mode == "audit":
        return "\nFOCUS MODE: AUDIT — severity-ordered remediation plan with file paths.\n"
    return ""


def oracle_directions_addon() -> str:
    mode = get_loop_mode()
    if mode == "build":
        return (
            "\nFOCUS MODE: BUILD — all three directions must be implementable in one loop. "
            "Titles like 'Implement X module' preferred over 'Explore the nature of Y'. "
            "problem_statement must name a measurable deliverable (CSV/API/test).\n"
            "Default oracle_pick toward the most engineering-ready direction.\n"
        )
    return ""


def problem_banner() -> str:
    mode = get_loop_mode()
    return f"[loop_mode={mode}] "
