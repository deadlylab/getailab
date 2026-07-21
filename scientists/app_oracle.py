#!/usr/bin/env python3
"""
CryptO'Brien Pty Ltd — Oracle Agent
Port: 5024 | GetAiLab
Role: Loop orchestration, synthesis, and no-idea problem generation
"""
import os
import re
import sys
import sqlite3
import random
from flask import request, jsonify
from llm.adapter import create_default_adapter

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from base_agent import create_agent_app, run_agent  # type: ignore
from personas.loader import build_agent_config, get_persona

try:
    from getailab.lab_config import agora_db_path, get_lab_id, load_lab_config
    _LAB_ID = get_lab_id()
    DB_PATH = os.getenv('AGORA_DB', str(agora_db_path(_LAB_ID)))
    _cfg = load_lab_config(_LAB_ID)
    _oracle_port = int(os.getenv('ORACLE_PORT', _cfg.get('oracle_port', 5124)))
except Exception:
    _LAB_ID = os.getenv('LAB_ID', 'example').strip() or 'example'
    DB_PATH = os.getenv(
        'AGORA_DB',
        os.path.join(os.getcwd(), 'data', 'labs', _LAB_ID, 'agora.db'),
    )
    _oracle_port = int(os.getenv('ORACLE_PORT', '5124'))
os.makedirs(os.path.dirname(DB_PATH) or '.', exist_ok=True)

# Library — auto-archive every completed loop to data/labs/<lab_id>/
GETAILAB_LIBRARY_ENABLED = True
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from getailab.library.service import archive_completed_loop
except Exception as _lib_import_err:
    GETAILAB_LIBRARY_ENABLED = False
    print(f"[GetAiLabLibrary] Import failed, archive disabled: {_lib_import_err}")

    def archive_completed_loop(loop_id, problem, synthesis, **k):
        print(f"[GetAiLabLibrary] (disabled) Would archive loop {loop_id}")
        return {}

def _init_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute("""
        CREATE TABLE IF NOT EXISTS agora_loops (
            loop_id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            problem_statement TEXT NOT NULL,
            consensus_artefact TEXT
        )
    """)
    conn.commit()
    conn.close()

_init_db()

_base_oracle = build_agent_config('oracle', overrides={'port': _oracle_port})
AGENT_CONFIG = {
    'name': _base_oracle['name'],
    'port': _base_oracle['port'],
    'role': _base_oracle['role'],
    'display_role': _base_oracle['display_role'],
    'expertise': _base_oracle.get('expertise', []),
    'implement_focus': _base_oracle.get('implement_focus', ''),
    'system_prompt': _base_oracle['system_prompt'],
    'contribution_to_loops': _base_oracle.get('contribution_to_loops', ''),
}

app = create_agent_app(AGENT_CONFIG)
oracle_adapter = create_default_adapter()

@app.route('/initiate_loop', methods=['POST'])
def initiate_loop():
    stmt = request.json.get('problem_statement', 'Default research statement')
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('INSERT INTO agora_loops (problem_statement) VALUES (?)', (stmt,))
    loop_id = cur.lastrowid
    conn.commit()
    conn.close()
    return jsonify({'loop_id': loop_id, 'status': 'initiated'}), 201

@app.route('/synthesize', methods=['POST'])
def synthesize():
    loop_id = request.json.get('loop_id')
    raw_data = request.json.get('raw_data', '')
    # Authoritative problem from agora (if available) — keeps synthesis on THIS loop
    problem_stmt = ""
    try:
        _conn = sqlite3.connect(DB_PATH, timeout=5)
        _row = _conn.execute(
            "SELECT problem_statement FROM agora_loops WHERE loop_id = ?",
            (loop_id,),
        ).fetchone()
        _conn.close()
        if _row and _row[0]:
            problem_stmt = str(_row[0])
    except Exception:
        problem_stmt = str(request.json.get("problem_statement") or "")
    try:
        from getailab.loop_focus import oracle_synthesis_addon, get_loop_mode
        mode_note = oracle_synthesis_addon()
        mode = get_loop_mode()
    except Exception:
        mode_note, mode = "", "research"
    prompt = (
        f"Synthesize this raw experiment data into a final Consensus Artefact "
        f"for lab '{_LAB_ID}' loop_id={loop_id} (loop_mode={mode}).\n"
        + mode_note
        + f"\nAUTHORITATIVE LOOP ID: {loop_id}\n"
        f"You MUST title the artefact with this exact loop number "
        f"(e.g. 'Loop {loop_id} Synthesis'). NEVER invent a different loop number "
        f"(do not write Loop 16/26 when this is loop {loop_id}).\n"
        f"\nTHIS LOOP'S PROBLEM STATEMENT:\n{(problem_stmt or '(see raw data)')[:3000]}\n"
        "\nRULES:\n"
        "- Ground claims ONLY in the RAW DATA below for THIS loop.\n"
        "- Do not rewrite history from older loops as if they were this loop's results.\n"
        "- If you mention prior loops, label them clearly as prior context, not this loop's scoreboard.\n"
        "- Prefer concrete paths under product/ and artifacts/ when present.\n"
        "- Preserve dissent and RESULT PASS/FAIL honestly.\n"
        + "\nRAW DATA:\n"
        + raw_data
    )
    
    try:
        synthesis_text = oracle_adapter.generate(
            prompt=prompt,
            system_prompt=(
                "You are Oracle synthesizing a research loop. Output markdown prose only. "
                "Never emit <tool_call>, shell commands, or JSON tool blocks. "
                "Preserve dissent. Prefer concrete next engineering steps when experiments produced artifacts. "
                f"This is loop_id={loop_id} — use that number in the title; never misnumber the loop."
            ),
        )
        try:
            from llm.sanitize import sanitize_prose
            synthesis_text, syn_ok = sanitize_prose(synthesis_text, min_chars=100)
            if not syn_ok:
                return jsonify({'loop_id': loop_id, 'error': 'Synthesis contained tool-call artifacts'}), 500
        except Exception:
            pass
    except Exception as e:
        print(f"[ERROR] Oracle Synthesis API Failure: {e}")
        return jsonify({'loop_id': loop_id, 'error': f'API Failure: {str(e)}'}), 500
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE agora_loops SET consensus_artefact = ? WHERE loop_id = ?", (synthesis_text, loop_id))
    # Fetch authoritative problem for provenance (fixes scope, ensures exact match to agora_loops)
    prob_row = conn.execute("SELECT problem_statement FROM agora_loops WHERE loop_id = ?", (loop_id,)).fetchone()
    problem_for_archive = prob_row[0] if prob_row and prob_row[0] else (raw_data[:280] if raw_data else "Problem from loop context")
    conn.commit()
    conn.close()

    # AUTO-ADD TO GETAILAB LIBRARY
    # Every completed loop is archived as structured pages (hypotheses, code, results, artifacts, synthesis)
    # with metadata and checksums for provenance and audit. This is the doccontrol integration.
    # The loop is not considered complete until it is persisted in the library.
    archive_result = {}
    if GETAILAB_LIBRARY_ENABLED:
        try:
            archive_result = archive_completed_loop(
                loop_id=loop_id,
                problem=problem_for_archive,
                synthesis=synthesis_text,
                raw_data=raw_data,
            )
            print(
                f"[GetAiLabLibrary] Loop {loop_id} archived: "
                f"{archive_result.get('pages_written', 0)} pages, "
                f"{archive_result.get('artifacts', 0)} artifacts"
            )
        except Exception as _lib_e:
            print(f"[GetAiLabLibrary] Non-fatal: auto-archive for loop {loop_id} skipped: {_lib_e}")

    return jsonify({
        'loop_id': loop_id,
        'synthesis': synthesis_text,
        'library_archived': bool(archive_result),
        'library_summary': archive_result,
    })

@app.route('/synthesize_reviews', methods=['POST'])
def synthesize_reviews():
    """Synthesize multi-scientist document reviews into recommended research paths."""
    data = request.get_json(silent=True) or {}
    review_id = data.get('review_id', '')
    working_question = data.get('working_question', '')
    materials_summary = data.get('materials_summary', '')
    raw_reviews = data.get('raw_reviews', '') or data.get('reviews', '')

    if not raw_reviews.strip():
        return jsonify({'error': 'raw_reviews is required'}), 400

    prompt = f"""You are Oracle — guardian synthesizer for a multi-agent research lab.

Scientists have independently reviewed uploaded material. Synthesize their perspectives into
actionable guidance for the researcher.

REVIEW SESSION: {review_id or 'unspecified'}
"""
    if working_question:
        prompt += f"\nWORKING QUESTION:\n{working_question}\n"
    if materials_summary:
        prompt += f"\nMATERIAL SUMMARY:\n{materials_summary[:4000]}\n"

    prompt += f"""
SCIENTIST REVIEWS:
{raw_reviews[:120000]}

Produce a Consensus Review Artefact with these sections:

## Executive Summary
(2-4 sentences — what the squad collectively learned)

## Convergent Findings
(Where multiple scientists agree — high-confidence takeaways)

## Productive Tensions
(Where perspectives diverge — name the scientists and what is at stake)

## Recommended Research Paths
(Numbered list of 3-6 concrete next investigations, each with:
- path title
- rationale (1-2 sentences)
- suggested lead scientist(s)
- suggested method: review / hypothesis loop / experiment / simulation)

## Working Question Assessment
(If a working question was provided: is it well-posed, too broad, or ready for a dialectic loop?
Offer 1-2 refined problem-statement candidates suitable for `run_lab.py --problem`.)

## Suggested Next Command
(One line the researcher can paste — e.g. a refined problem statement or `python3 scripts/collaborative_review.py --files ...`)
"""

    try:
        synthesis_text = oracle_adapter.generate(prompt=prompt)
    except Exception as e:
        print(f"[ERROR] Oracle Review Synthesis Failure: {e}")
        return jsonify({'error': f'API Failure: {str(e)}'}), 500

    archive_result = {}
    if GETAILAB_LIBRARY_ENABLED:
        try:
            from getailab.library.service import archive_collaborative_review
            archive_result = archive_collaborative_review(
                review_id=review_id or f"review-{int(__import__('time').time())}",
                working_question=working_question,
                materials_summary=materials_summary,
                raw_reviews=raw_reviews,
                synthesis=synthesis_text,
            )
        except Exception as _lib_e:
            print(f"[GetAiLabLibrary] Non-fatal: review archive skipped: {_lib_e}")

    return jsonify({
        'review_id': review_id,
        'synthesis': synthesis_text,
        'library_archived': bool(archive_result),
        'library_summary': archive_result,
    })


def _extract_json_object(text: str) -> dict:
    """Best-effort JSON parse from Oracle output (raw or fenced)."""
    import json as _json
    raw = (text or "").strip()
    if not raw:
        return {}
    for candidate in (raw,):
        try:
            return _json.loads(candidate)
        except Exception:
            pass
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL | re.I)
    if match:
        try:
            return _json.loads(match.group(1))
        except Exception:
            pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return _json.loads(raw[start : end + 1])
        except Exception:
            pass
    return {}


def _fallback_directions(synthesis: str, problem_statement: str = "") -> dict:
    """Structured fallback when the model does not return parseable JSON."""
    seed = (problem_statement or synthesis or "the prior loop")[:220]
    return {
        "directions": [
            {
                "id": 1,
                "title": "Deepen the consensus thread",
                "problem_statement": (
                    f"What rigorous extensions follow from the synthesis of loop work on: {seed}?"
                ),
                "rationale": "Build directly on what the squad already agreed.",
                "lead_scientists": [],
            },
            {
                "id": 2,
                "title": "Stress-test the weakest link",
                "problem_statement": (
                    f"Which assumption in the synthesis about '{seed}' fails under adversarial scrutiny, "
                    "and how should we test it?"
                ),
                "rationale": "Challenge the fragile parts before scaling the idea.",
                "lead_scientists": [],
            },
            {
                "id": 3,
                "title": "Bridge to implementation",
                "problem_statement": (
                    f"What minimal experiment would falsify or validate the main claim from: {seed}?"
                ),
                "rationale": "Move from synthesis toward measurable lab evidence.",
                "lead_scientists": [],
            },
        ],
        "oracle_pick": 1,
        "oracle_rationale": "Extending the consensus thread is the safest next step.",
    }


def _squad_scientist_names() -> list:
    """Active lab scientists only (exclude oracle). Never hardcode Chimera names.

    Prefer PERSONAS_YAML / lab squad via get_squad_names(); fall back to lab_config
    scientists map; last resort ai_dev-style default so leads never leak foreign squads.
    """
    names: list = []
    try:
        from personas.loader import get_squad_names
        names = [n for n in (get_squad_names() or []) if n and str(n).lower() != "oracle"]
    except Exception:
        names = []
    if not names:
        try:
            from getailab.lab_config import load_lab_config, get_lab_id
            cfg = load_lab_config(get_lab_id())
            sci = cfg.get("scientists") or {}
            names = [str(k).lower() for k in sci.keys() if str(k).lower() != "oracle"]
        except Exception:
            names = []
    if not names:
        names = ["hinton", "bengio", "lecun", "hopfield", "linus"]
    # de-dupe preserve order
    seen = set()
    out = []
    for n in names:
        k = str(n).strip().lower()
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


def _sanitize_leads(raw_leads, allowed: list | None = None) -> list:
    """Keep only names that belong to this lab's squad (max 3)."""
    allowed = allowed if allowed is not None else _squad_scientist_names()
    allow = {a.lower() for a in allowed}
    cleaned = []
    for x in raw_leads or []:
        name = str(x).strip().lower()
        if name in allow and name not in cleaned:
            cleaned.append(name)
        if len(cleaned) >= 3:
            break
    return cleaned


def _clean_direction_text(text: str, *, is_title: bool = False) -> str:
    """Strip menu/report markdown junk so next-loop problems stay clean."""
    s = str(text or "").strip()
    # drop leading markdown headers / list markers / stars from UI paste
    s = re.sub(r"^#{1,6}\s*", "", s)
    s = re.sub(r"^\d+[\.)]\s*", "", s)
    s = re.sub(r"[★☆✦]\s*", "", s)
    s = s.replace("**", "").strip()
    if is_title:
        # one line, no trailing period spam
        s = s.split("\n")[0].strip().strip(".").strip()
        if len(s) > 80:
            s = s[:77] + "…"
    else:
        # problem_statement: plain prose only
        s = re.sub(r"\n{3,}", "\n\n", s).strip()
        if s.startswith("###") or s.startswith("##"):
            s = re.sub(r"^#+\s*", "", s)
    return s


def _default_leads_for_index(i: int, squad: list) -> list:
    """Stable lead assignment when model returns empty/foreign names."""
    if not squad:
        return []
    # rotate pairs through the squad
    a = squad[(i - 1) % len(squad)]
    b = squad[i % len(squad)]
    return [a] if a == b else [a, b]


def generate_next_directions(
    synthesis: str,
    *,
    problem_statement: str = "",
    user_comment: str = "",
    loop_id: str | int | None = None,
) -> dict:
    """Return three research directions + Oracle's preferred pick."""
    try:
        from getailab.loop_focus import oracle_directions_addon, get_loop_mode
        dir_addon = oracle_directions_addon()
        mode = get_loop_mode()
    except Exception:
        dir_addon, mode = "", "research"
    squad = _squad_scientist_names()
    squad_csv = ", ".join(squad)
    example_leads = squad[:2] if len(squad) >= 2 else (squad or ["hinton"])
    lid = str(loop_id) if loop_id is not None else "?"
    prompt = f"""You are Oracle for multi-agent research lab '{_LAB_ID}' (loop_mode={mode}).

THIS LOOP ID: {lid}
Active squad (ONLY these names may appear as lead_scientists): {squad_csv}

A dialectic loop just completed. Propose exactly THREE distinct next research directions
that CONTINUE THIS LOOP'S THREAD — not random older topics.

{dir_addon}

ORIGINAL PROBLEM (this loop):
{problem_statement[:3000] if problem_statement else '(not provided)'}

SYNTHESIS (this loop's consensus artefact only):
{synthesis[:12000]}

RESEARCHER NOTES (optional — may be empty):
{user_comment[:2000] if user_comment else '(none)'}

Return ONLY valid JSON (no markdown prose outside the JSON):
{{
  "directions": [
    {{
      "id": 1,
      "title": "Short direction name (5-10 words, no markdown, no stars)",
      "problem_statement": "One clear plain-text problem for the next loop (1-3 sentences). NO markdown headers, NO leading numbers, NO star characters.",
      "rationale": "Why this direction matters now (1 sentence)",
      "lead_scientists": {example_leads!r}
    }},
    {{ "id": 2, ... }},
    {{ "id": 3, ... }}
  ],
  "oracle_pick": 1,
  "oracle_rationale": "One sentence explaining which direction you recommend and why"
}}

Rules:
- Three directions must be genuinely different (not minor rephrasings).
- problem_statement must be paste-ready as the NEXT loop problem (plain sentences only).
- Do NOT prefix problem_statement with '###', '1.', or '★'.
- Ground directions in THIS problem + synthesis. Do not suddenly switch to unrelated prior threads
  (e.g. do not invent SpectralNorm energy work unless this loop's synthesis actually about that).
- oracle_pick must be integer 1, 2, or 3.
- lead_scientists: 1-3 names ONLY from: {squad_csv}
- NEVER invent foreign lab names (albert, bohr, heisenberg, emmy, alan, andrew, chimera).
- id fields must be integers 1, 2, 3.
"""
    try:
        raw = oracle_adapter.generate(prompt=prompt)
        parsed = _extract_json_object(raw)
        directions = parsed.get("directions") or []
        if len(directions) < 3:
            raise ValueError("expected 3 directions")
        cleaned = []
        for i, d in enumerate(directions[:3], start=1):
            leads = _sanitize_leads(d.get("lead_scientists") or [], squad)
            if not leads:
                leads = _default_leads_for_index(i, squad)
            title = _clean_direction_text(d.get("title") or f"Direction {i}", is_title=True)
            stmt = _clean_direction_text(d.get("problem_statement") or "", is_title=False)
            if not stmt:
                stmt = title  # last resort, already cleaned
            cleaned.append({
                "id": i,  # always int — UI star match depends on this
                "title": title or f"Direction {i}",
                "problem_statement": stmt,
                "rationale": _clean_direction_text(d.get("rationale") or "", is_title=False),
                "lead_scientists": leads,
            })
        try:
            pick = int(parsed.get("oracle_pick") or 1)
        except (TypeError, ValueError):
            pick = 1
        if pick not in (1, 2, 3):
            pick = 1
        rationale = str(parsed.get("oracle_rationale") or "").strip()
        return {
            "directions": cleaned,
            "oracle_pick": pick,
            "oracle_rationale": rationale,
        }
    except Exception as e:
        print(f"[MUSE] next-directions fallback: {e}")
        return _fallback_directions(synthesis, problem_statement)


@app.route('/recommend_next', methods=['POST'])
def recommend_next():
    data = request.get_json(silent=True) or {}
    synthesis = data.get('synthesis', '')
    user_comment = data.get('user_comment', '')
    problem_statement = data.get('problem_statement', '')
    loop_id = data.get('loop_id')

    try:
        result = generate_next_directions(
            synthesis,
            problem_statement=problem_statement,
            user_comment=user_comment,
            loop_id=loop_id,
        )
    except Exception as e:
        print(f"[ERROR] Oracle Recommendation API Failure: {e}")
        return jsonify({'error': f'API Failure: {str(e)}'}), 500

    directions = result.get("directions", [])
    try:
        pick = int(result.get("oracle_pick") or 1)
    except (TypeError, ValueError):
        pick = 1
    pick = pick if pick in (1, 2, 3) else 1
    chosen = directions[pick - 1] if directions else {}
    recommendation_text = chosen.get("problem_statement") or result.get("oracle_rationale") or ""

    return jsonify({
        'recommendation': recommendation_text,
        'directions': directions,
        'oracle_pick': pick,
        'oracle_rationale': result.get("oracle_rationale", ""),
        'loop_id': loop_id,
    })


CATEGORIES = [
    "surprise", "foundations", "frontiers", "interdisciplinary", "applied",
    "theoretical", "historical", "everyday", "personal", "library_fork"
]

def _get_persona_lens(name: str) -> str:
    try:
        p = get_persona(name)
        role = p.get("role", name)
        disp = p.get("display_role", role)
        expertise = ", ".join(p.get("expertise", [])[:3])
        return f"{disp}. Core: {expertise}."
    except Exception:
        return f"Researcher specializing in {name}."

# Built from active lab squad (PERSONAS_YAML / lab_config) — not Chimera hardcodes.
PERSONA_LENSES = {k: _get_persona_lens(k) for k in _squad_scientist_names()}

def _sample_library_resonances(limit=4):
    """Pull real past problems from the Agora/Library for resonance."""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=5)
        rows = conn.execute(
            "SELECT problem_statement FROM agora_loops WHERE problem_statement IS NOT NULL ORDER BY loop_id DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [r[0][:220] for r in rows if r[0]]
    except Exception:
        return [
            "Structural limitations of agentic frameworks in complex domains.",
            "Trade-offs between formal deduction and intuitive insight.",
            "How do prior artifacts and syntheses influence new research directions?",
            "Emergence of robust understanding from multi-perspective analysis."
        ]

def generate_starter_problem(category="surprise", family_note="", persona_hint=None):
    """Core auto-generator. Uses Oracle model + Library + persona wisdom.
    Cleaned of cosmo / sandwich / landscape framing."""
    resonances = _sample_library_resonances()
    resonance_text = "\n".join(f"- {r}" for r in resonances[:3])

    persona_name = persona_hint or random.choice(list(PERSONA_LENSES.keys()))
    persona_desc = _get_persona_lens(persona_name)

    cat_guidance = {
        "foundations": "Focus on core assumptions, definitions, or first principles in a domain.",
        "frontiers": "Open problems, edge cases, or areas where current methods break down.",
        "interdisciplinary": "Connections between fields that are not usually combined.",
        "applied": "Practical problems where rigorous analysis can produce measurable improvement.",
        "theoretical": "Abstract questions that reward clear modeling and careful reasoning.",
        "historical": "How past approaches succeeded or failed, and what can be learned.",
        "everyday": "Seemingly simple phenomena that reveal deeper structure on examination.",
        "personal": "Lightly incorporate the provided family_note if relevant.",
        "library_fork": "Build upon or evolve one of the historical problems from the Library.",
        "surprise": "Any high-rigor, open question likely to benefit from multi-perspective analysis."
    }.get(category, "Craft a clear, open, high-rigor research problem statement.")

    family_infusion = f"\nPersonal context note: {family_note}" if family_note else ""

    prompt = f"""You are a research Muse for a multi-agent lab.

A user needs a good starting research problem. 

CATEGORY: {category}
GUIDANCE: {cat_guidance}
{family_infusion}

PERSONA LENS: {persona_name} — {persona_desc}

LIBRARY RESONANCES (echo or build upon these past problems):
{resonance_text}

TASK: Write ONE clear, specific, high-rigor PROBLEM STATEMENT (1-3 sentences). It should:
- Be suitable for a team of specialized researchers to attack from multiple angles.
- Be open enough to allow hypotheses, code experiments, and review.
- Be precise enough to produce useful artifacts and synthesis.
- Avoid vague or purely philosophical framing.

Return ONLY the problem statement text."""

    try:
        problem_text = oracle_adapter.generate(prompt=prompt)
        problem_text = (problem_text or "").strip().strip('"').strip("'")
        if not problem_text or len(problem_text) < 20:
            raise ValueError("Weak generation")
    except Exception as e:
        print(f"[MUSE] LLM generation fallback engaged: {e}")
        fallbacks = [
            "What are the key trade-offs when designing agent teams for problems that require both formal reasoning and creative hypothesis generation?",
            "How can structured multi-perspective review improve the reliability of experimental results in open-ended research domains?",
            "What mechanisms allow a research loop to productively build on its own previous artifacts without simply repeating prior work?",
        ]
        problem_text = random.choice(fallbacks)
        if family_note:
            problem_text += f" (Consider context: {family_note[:80]})"

    muse_note = f"Generated via the No-Idea Portal in the {category} category. Lens: {persona_name}. Library echoes: {len(resonances)}."
    if family_note:
        muse_note += " Personal context incorporated."

    return {
        "problem_statement": problem_text,
        "category": category,
        "persona_hint": persona_name,
        "muse_note": muse_note,
        "library_resonances_sampled": len(resonances),
        "family_infused": bool(family_note)
    }

@app.route('/generate_problem', methods=['POST', 'GET'])
def generate_problem():
    """Public endpoint for CLI Commander Console and Web UI No-Idea flow.
    POST body: {"category": "...", "family_note": "...", "persona_hint": "optional"}
    Returns ready-to-ignite problem + metadata. Integrates personas + Library."""
    data = request.get_json(silent=True) or request.args.to_dict() or {}
    category = data.get('category', 'surprise')
    if category not in CATEGORIES:
        category = 'surprise'
    family_note = data.get('family_note', '') or data.get('family', '')
    persona_hint = data.get('persona_hint')

    result = generate_starter_problem(category=category, family_note=family_note, persona_hint=persona_hint)
    return jsonify(result), 200

if __name__ == '__main__':
    run_agent(app, AGENT_CONFIG)