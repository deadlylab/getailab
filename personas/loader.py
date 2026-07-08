"""
personas/loader.py
GetAiLab - Single Source of Truth Loader for Revived Personalities
Production-ready central loader. Do not dilute. All squad definitions flow from chimera_squad.yaml.

Usage:
    from personas.loader import get_persona, build_agent_config, get_system_prompt
    config = build_agent_config('albert')
    # then pass to create_agent_app(config) or override in app_*.py for now

Pure vision: Preserves the full debate-heavy, DO NOT BEND, named-challenge, "call bullshit", heated but productive style from the authoritative YAML.
"""

import os
import re
import yaml
from typing import Dict, Any, Optional

# Legacy R&D research used an older Albert voice ("Quantum Physicist"). Live the example lab Albert
# is the relativity / unified-field persona — scrub mislabels before they hit his context.
_ALBERT_ROLE_REPLACEMENTS = (
    (re.compile(r"⚛️\s*Albert\s*\(\s*Quantum Physicist\s*\)", re.I), "Albert (Theoretical Physicist)"),
    (re.compile(r"\bAlbert\s*\(\s*Quantum Physicist\s*\)", re.I), "Albert (Theoretical Physicist)"),
    (re.compile(r"\bALBERT\s*\(\s*Quantum Physicist\s*\)", re.I), "ALBERT (Theoretical Physicist)"),
    (re.compile(r"\*\*Albert\*\*:?\s*Quantum Physicist", re.I), "**Albert:** Theoretical Physicist"),
    (re.compile(r"\|\s*\*\*Albert\*\*\s*\|\s*Quantum Physicist", re.I), "| **Albert** | Theoretical Physicist"),
    (re.compile(r"\bAlbert\s*[-—]\s*Quantum Physicist\b", re.I), "Albert — Theoretical Physicist"),
    (re.compile(r"\bAlbert,\s*Quantum Physicist\b", re.I), "Albert, Theoretical Physicist"),
    (re.compile(r"\bAlbert the Quantum Physicist\b", re.I), "Albert the Theoretical Physicist"),
    (re.compile(r"#\s*Albert\s*-\s*Quantum Physicist\b", re.I), "# Albert — Theoretical Physicist"),
)


def sanitize_albert_persona_labels(text: str) -> str:
    """Rewrite legacy 'Quantum Physicist' Albert labels to his canonical the example lab role."""
    if not text:
        return text
    out = text
    for pattern, replacement in _ALBERT_ROLE_REPLACEMENTS:
        out = pattern.sub(replacement, out)
    # Table / list lines: "Albert ... Quantum Physicist" on the same line
    fixed_lines = []
    for line in out.splitlines():
        if re.search(r"\bAlbert\b", line, re.I) and re.search(r"\bQuantum Physicist\b", line, re.I):
            line = re.sub(r"\bQuantum Physicist\b", "Theoretical Physicist", line, flags=re.I)
        fixed_lines.append(line)
    return "\n".join(fixed_lines)

_DEFAULT_PERSONAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "chimera_squad.yaml")

_cached_data: Optional[Dict[str, Any]] = None
_cached_path: Optional[str] = None


def get_personas_path() -> str:
    """Resolve personas YAML: PERSONAS_YAML env, lab config, or example lab default."""
    explicit = os.getenv("PERSONAS_YAML", "").strip()
    if explicit:
        if os.path.isabs(explicit):
            return explicit
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(root, explicit)
    try:
        from getailab.lab_config import personas_yaml_path
        return str(personas_yaml_path())
    except Exception:
        return _DEFAULT_PERSONAS


def _load_yaml() -> Dict[str, Any]:
    global _cached_data, _cached_path
    path = get_personas_path()
    if _cached_data is None or _cached_path != path:
        with open(path, "r", encoding="utf-8") as f:
            _cached_data = yaml.safe_load(f)
        _cached_path = path
    return _cached_data

def get_persona(name: str) -> Dict[str, Any]:
    """Return the full persona dict for the given name (case-insensitive match on 'name' field)."""
    data = _load_yaml()
    squad = data.get("squad", [])
    target = name.lower().strip()
    for p in squad:
        if p.get("name", "").lower() == target:
            return p
    # Fallback for oracle or legacy
    if target == "oracle":
        for p in squad:
            if p.get("name", "").lower() == "oracle":
                return p
    raise KeyError(f"Persona '{name}' not found in {get_personas_path()}. Available: {[p.get('name') for p in squad]}")

def get_system_prompt(name: str) -> str:
    """Return the full revived system_prompt string (includes Core Personality & Debate Rules (DO NOT BEND))."""
    persona = get_persona(name)
    return persona.get("system_prompt", f"ERROR: No system_prompt for {name}. Revive in YAML.")

def build_agent_config(name: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Build a complete AGENT_CONFIG dict ready for create_agent_app / base_agent.
    Merges core fields from YAML + sensible defaults. Use overrides for port tweaks or local experiments.
    Production: call this in each app_*.py or from base to avoid prompt duplication.
    """
    persona = get_persona(name)
    config = {
        "name": persona.get("name", name).lower(),
        "port": persona.get("port", 0),
        "role": persona.get("role", "scientist"),
        "display_role": persona.get("display_role", persona.get("name", name)),
        "expertise": persona.get("expertise", []),
        "implement_focus": persona.get("implement_focus", ""),
        "system_prompt": get_system_prompt(name),  # THE REVIVED FULL PERSONALITY - DO NOT BEND
        "contribution_to_loops": persona.get("contribution_to_loops", ""),
    }
    if overrides:
        config.update(overrides)
    return config

def get_squad_names() -> list:
    """List of all squad member names for boot/run coordination."""
    data = _load_yaml()
    return [p.get("name", "").lower() for p in data.get("squad", []) if p.get("name")]

def get_core_debate_rules() -> list:
    """The non-negotiable debate rules injected into all agents for heat preservation."""
    data = _load_yaml()
    return data.get("core_debate_rules", [])

# ==============================================================================
# HIERARCHICAL SUB-AGENT SUPPORT (String of Agents + Sub-Agents of Sub-Agents)
# Production centralization for the revived personalities in recursive delegation.
# Sub-agents inherit the FULL DO NOT BEND debate heat, named challenges, "call bullshit",
# "poetry not physics" from the parent via YAML, but narrow to specialization (e.g. salience_gating,
# neuromodulatory, cognitive_higgs_field, penrose_orch_or_solver, geodesic_curvature, epistemic_probe,
# archetypal_interference, symmetry_invariant, biological_plasticity).
# This delivers the Andrew + loop_12 biological hierarchy roadmap without dilution.
# Pure vision: Sandwich Paradox metabolic efficiency via delegation to fast specialized sub-agents.
# ==============================================================================

def build_subagent_config(parent_name: str, specialization: str, task: str = "specialized sub-problem") -> Dict[str, Any]:
    """
    Build a production sub-agent config inheriting the parent's FULL revived personality
    (DO NOT BEND rules, direct named challenges, heat) + narrow specialization.
    Used by base_agent for spawn_sub / delegate (and recursively from subs).
    Sub-agents of sub-agents supported by calling this with a sub's name as 'parent'.
    Returns full config dict ready for internal use or registry.
    """
    try:
        parent = get_persona(parent_name)
        base_prompt = parent.get("system_prompt", "Sub-agent operating under the example lab vision.")
    except Exception:
        base_prompt = "Sub-agent operating under the example lab pure vision (Sandwich Paradox + Landscape Engine)."

    sub_name = f"sub_{parent_name.lower()}_{specialization.lower().replace(' ', '_')[:35]}"
    data = _load_yaml()
    core_rules = data.get("core_debate_rules", [])
    rules_block = "\n".join([f"- {r}" for r in core_rules]) if core_rules else "Argue your corner with clarity... Challenge imprecision constructively... Direct address by name with respect... Demand rigor... Build toward shared success."

    sub_prompt = base_prompt + (
        f"\n\n**SUB-AGENT SPECIALIZATION + INHERITED COLLABORATION STANDARDS (FROM {parent_name.upper()}):**\n"
        f"You are a specialized sub-agent of {parent_name}. Focus EXCLUSIVELY on: {specialization}. "
        f"Task: {task}. Report directly with data/artifacts only (always .csv/.json/.png named after your sub_id). "
        "Challenge imprecision constructively if the delegation violates rigor, geometry, complementarity, "
        "non-computability, archetypes, fields, symmetries, metabolic cost, or the core Sandwich Paradox / Landscape Engine goal — then propose a fix. "
        "You may recursively spawn and delegate to your own sub-sub-agents if the sub-problem "
        "requires deeper hierarchy for metabolic efficiency (e.g. salience sub-sub for prediction error gating). "
        "\n\n**CORE COLLABORATION RULES YOU INHERIT (from chimera_squad.yaml):**\n"
        f"{rules_block}\n"
        "ALWAYS: address colleagues by name with respect, demand commutators/curvature/interference/collapse/scale-invariance/artifacts, build constructively while disagreeing on specifics, and orient every output toward what the team should test next."
    )

    return {
        "name": sub_name,
        "port": 0,  # internal; promoted only if elevated to full squad
        "role": f"sub_agent_{specialization}",
        "display_role": f"Sub-Agent of {parent_name}: {specialization}",
        "system_prompt": sub_prompt,
        "implement_focus": specialization,
        "parent": parent_name,
        "specialization": specialization,
        "task": task,
        "is_subagent": True,
        "inherits_full_debate_rules": True,
    }

def get_sub_specializations() -> list:
    """Canonical list of production specializations drawn from squad work (Andrew loop_12, Brian fields, Roger Orch-OR, etc)."""
    return [
        "salience_gating", "neuromodulatory_dopamine", "plasticity_cache_ltp",
        "cognitive_higgs_field", "geodesic_curvature", "epistemic_superposition_probe",
        "archetypal_shadow_interference", "penrose_orch_or_solver", "symmetry_invariant_preservation",
        "complementarity_measurement", "cosmic_scale_emergence", "noncommutativity_operator",
        "biological_metabolic_audit", "artifact_persistence_audit"
    ]

# End of loader. Single source. Pure vision. All sub-agents and hierarchies load from here.
# Sub-persona / build_subagent_config NOW IMPLEMENTED (smashed the todo from notes).
# Full recursive string-of-agents + sub-of-subs live via base_agent + loader. No bending.