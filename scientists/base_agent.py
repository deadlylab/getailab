import os
import sys
import json
import hashlib
import re
import sqlite3
from datetime import datetime
from typing import Dict, Any
from flask import Flask, request, jsonify
from flask_cors import CORS
from llm.adapter import get_env_provider_config, LLMAdapter

# Load personas from single source (chimera_squad.yaml or your own).
# Clean: no debate rules, no sub-agent inheritance forced.
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from personas.loader import build_agent_config, get_persona
    HAS_LOADER = True
except Exception as _e:
    HAS_LOADER = False
    print("WARNING: personas.loader not available. Falling back to inline config (non-production).")

def extract_python_code(raw: str) -> str:
    """Pull runnable Python from LLM output (fences, preamble, truncation)."""
    text = (raw or "").strip()
    if not text:
        return ""

    for pattern in (
        r"```python\s*(.*?)\s*```",
        r"```py\s*(.*?)\s*```",
        r"```\s*(.*?)\s*```",
    ):
        match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if match:
            text = match.group(1).strip()
            break
    else:
        # Truncated response — opening fence without close
        for opener in (r"```python\s*", r"```py\s*", r"```\s*"):
            match = re.search(opener + r"(.*)", text, re.DOTALL | re.IGNORECASE)
            if match:
                text = match.group(1).strip()
                break

    lines = []
    for line in text.splitlines():
        if re.match(r"^EXPERIMENT_NAME\s*:", line, re.IGNORECASE):
            continue
        if line.strip() in ("```python", "```py", "```"):
            continue
        lines.append(line)
    text = "\n".join(lines).strip()
    text = re.sub(r"```\s*$", "", text).strip()
    return text


class LLMClient:
    def __init__(self, model_name: str = "", code_model_name: str = ""):
        config = get_env_provider_config()
        if model_name:
            config['model'] = model_name
        if code_model_name:
            config['code_model'] = code_model_name
        self.adapter = LLMAdapter(config)

    def generate(self, prompt: str, system_prompt: str = "", use_code_model: bool = False):
        try:
            text = self.adapter.generate(prompt=prompt, system_prompt=system_prompt, use_code_model=use_code_model)
            return type('obj', (object,), {'text': text})
        except Exception as e:
            return type('obj', (object,), {'text': "ERROR: " + str(e)})

# ==============================================================================
# CLEAN BASE AGENT
# Stripped of recursive sub-agent hierarchy, biological gating, debate heat, and cosmo framing.
# Core: persona-driven agent with basic lab tools. Sub-delegation can be re-added later if needed
# for the clean lab scope (no sub-of-subs required for v1).
# ==============================================================================

# No SUB_AGENT_REGISTRY or spawn/delegate functions in this clean version.

def _load_scientist_book(agent_name: str):
    """Load this agent's research book. Fails open if library unavailable."""
    try:
        from getailab.library import get_scientist_book
        lab_id = os.getenv("LAB_ID", "chimera")
        return get_scientist_book(agent_name, lab_id=lab_id)
    except Exception as exc:
        print(f"[BASE] ScientistBook unavailable for {agent_name}: {exc}")
        return None


def _pull_book_context(
    agent_name: str,
    problem_statement: str,
    *,
    query_extra: str = "",
    loop_id=None,
    limit: int = 5,
) -> tuple:
    """Retrieve prior research from this scientist's book for prompt injection."""
    book = _load_scientist_book(agent_name)
    if not book or book.page_count() == 0:
        return "", []

    exclude_loop_id = None
    if loop_id is not None:
        try:
            exclude_loop_id = int(loop_id)
        except (TypeError, ValueError):
            pass

    try:
        ctx = book.get_research_context(
            query=query_extra or problem_statement,
            problem_statement=problem_statement,
            limit=limit,
            exclude_loop_id=exclude_loop_id,
        )
        context_text = ctx.get("context_text", "")
        if agent_name.lower() == "albert" and context_text:
            from personas.loader import sanitize_albert_persona_labels
            context_text = sanitize_albert_persona_labels(context_text)
        return context_text, ctx.get("sources", [])
    except Exception as exc:
        print(f"[BASE] Book context pull failed for {agent_name}: {exc}")
        return "", []


def _pull_skills_context(
    agent_name: str,
    query: str,
    *,
    loop_id=None,
    limit: int = 5,
) -> tuple:
    """Retrieve reusable skills from this scientist's book."""
    book = _load_scientist_book(agent_name)
    if not book or book.skill_count() == 0:
        return "", []

    exclude_loop_id = None
    if loop_id is not None:
        try:
            exclude_loop_id = int(loop_id)
        except (TypeError, ValueError):
            pass

    try:
        ctx = book.get_skills_context(
            query,
            limit=limit,
            exclude_loop_id=exclude_loop_id,
        )
        return ctx.get("context_text", ""), ctx.get("sources", [])
    except Exception as exc:
        print(f"[BASE] Skills pull failed for {agent_name}: {exc}")
        return "", []


def create_agent_app(config: dict) -> Flask:
    app = Flask(config['name'])
    CORS(app)

    agent_name = os.getenv('AGENT_NAME', config['name'])
    agent_port = int(os.getenv('AGENT_PORT', config['port']))
    lab_url = os.getenv('LAB_URL', 'http://localhost:5035').rstrip('/')
    
    # --- The Lab Manual (Injected into every agent) ---
    import os as _os
    _project_root = _os.path.dirname(_os.path.dirname(_os.path.abspath(__file__)))
    _sauron_cli = _os.path.join(_project_root, "sauron_vision.py")
    lab_capabilities = f"""
LAB INFRASTRUCTURE MANUAL:
1. PERSISTENT WORKSPACE: You are executing in a dedicated directory. ALWAYS save data as .csv, .json, or .png. Other agents will see these files in future loops.
2. SAURON VISION: You can access visual web data via '{lab_url}/vision/extract (or CLI: python3 {_sauron_cli} --url URL "Query")' (POST json: {{'url': '...', 'query': '...'}}) for visual/JSON extraction. Works cross-platform on Windows, macOS, Linux.
3. WEB READER: Access raw markdown of any URL via '{lab_url}/web/read' (POST json: {{'url': '...'}}).
4. LITERATURE SEARCH: Ground hypotheses in published work via '{lab_url}/literature/search' (POST json: {{'query': 'your search terms'}}). Searches PubMed, arXiv, and Semantic Scholar. Returns titles, abstracts, and URLs. Cite specific papers when you use them.
5. LIBRARIES: You have access to numpy, scipy, matplotlib, pandas, pyarrow, and sympy. Use them for high-rigor proofs.
6. GETAILABLIBRARY: Completed work (hypotheses, code, results, artifacts) gets registered with doccontrol for provenance, checksums, and audit. The loop is not final until it's in the library.
7. OUTPUT FORMAT: You have NO shell/terminal tools in this service. Never emit <tool_call>, tool_response, run_command, or JSON tool invocations. Write hypotheses and reviews as markdown prose. Write experiments only inside ```python fences.
"""
    
    system_prompt = config['system_prompt'] + "\n\n" + lab_capabilities
    implement_focus = config.get('implement_focus', '')

    # Production revival (loader-driven personas)
    if HAS_LOADER:
        try:
            revived = build_agent_config(config.get('name', agent_name))
            config = {**config, **revived}
            print(f"[BASE+LOADER] Loaded persona for {agent_name} from single-source YAML.")
        except Exception as _e:
            print(f"[BASE+LOADER] Auto-revive skipped for {agent_name}: {_e}")

    model = LLMClient(os.getenv("LLM_MODEL", ""))
    think_model = LLMClient(os.getenv("LLM_MODEL_THINK", ""))
    code_model = LLMClient(code_model_name=os.getenv("LLM_MODEL_CODE", ""))

    @app.route('/health', methods=['GET'])
    def health_check():
        llm_info = think_model.adapter.get_info()
        book = _load_scientist_book(agent_name)
        book_info = {
            "available": book is not None,
            "pages": book.page_count() if book else 0,
            "skills": book.skill_count() if book else 0,
            "loops": book.loops_contributed() if book else [],
        }
        return jsonify({
            'agent': agent_name,
            'port': agent_port,
            'role': config['role'],
            'status': 'healthy',
            'llm': llm_info,
            'tools': ['sauron_vision', 'literature_search', 'artifact_vault', 'scientist_book', 'skills'],
            'book': book_info,
        }), 200

    @app.route('/hypothesis', methods=['POST'])
    def generate_hypothesis():
        data = request.get_json() or {}
        problem = str(data.get('problem_statement', ''))
        loop_id = data.get('loop_id')

        book_ctx, book_sources = _pull_book_context(
            agent_name,
            problem,
            loop_id=loop_id,
            limit=5,
        )
        skills_ctx, skill_sources = _pull_skills_context(
            agent_name,
            problem,
            loop_id=loop_id,
            limit=3,
        )

        parts = ["PROBLEM: " + problem]
        if data.get('context'):
            parts.append("LATEST LAB DATA/CONTEXT: " + str(data['context']))
        if book_ctx:
            parts.append(
                "YOUR PRIOR RESEARCH (from your book — build on this, do not repeat blindly):\n"
                + book_ctx
            )
        if skills_ctx:
            parts.append(
                "REUSABLE PATTERNS FROM YOUR PRIOR EXPERIMENTS:\n" + skills_ctx
            )

        prompt = "\n\n".join(parts) + (
            "\n\nBased on your role, your prior research above, and the available Lab tools, "
            "provide a high-rigor hypothesis as markdown prose only. "
            "Do NOT call shell tools or emit <tool_call> blocks — use the lab sandbox in Phase 2 for code."
        )
        response = think_model.generate(system_prompt + "\n\n" + prompt)
        if response.text.strip().startswith("ERROR:"):
            return jsonify({
                'agent': agent_name,
                'error': response.text,
                'hypothesis': None,
            }), 503

        try:
            from llm.sanitize import sanitize_prose
            hyp_text, hyp_ok = sanitize_prose(response.text, min_chars=150)
        except Exception:
            hyp_text, hyp_ok = response.text, True
        if not hyp_ok:
            return jsonify({
                'agent': agent_name,
                'error': 'ERROR: Model emitted tool-call artifacts instead of a hypothesis. Retry or switch model.',
                'hypothesis': None,
            }), 503

        return jsonify({
            'agent': agent_name,
            'hypothesis': hyp_text,
            'book_context_used': bool(book_ctx),
            'book_sources': book_sources,
            'skills_context_used': bool(skills_ctx),
            'skill_sources': skill_sources,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    @app.route('/review', methods=['POST'])
    def review_materials():
        """Collaborative review — lighter than a full loop; structured findings per scientist."""
        data = request.get_json() or {}
        materials = str(data.get('materials', '') or data.get('content', ''))
        working_question = str(data.get('working_question', '') or data.get('problem_statement', ''))
        review_id = data.get('review_id', '')
        title = str(data.get('title', 'Uploaded materials'))

        query = f"{working_question} {title} {materials[:500]}"
        book_ctx, book_sources = _pull_book_context(
            agent_name,
            query,
            limit=4,
        )
        skills_ctx, skill_sources = _pull_skills_context(
            agent_name,
            query,
            limit=2,
        )

        parts = [
            "COLLABORATIVE REVIEW — report structured findings from your disciplinary lens.",
            f"MATERIAL TITLE: {title}",
        ]
        if review_id:
            parts.append(f"REVIEW SESSION: {review_id}")
        if working_question:
            parts.append(
                "WORKING QUESTION (assess relevance; suggest refinements if warranted):\n"
                + working_question
            )
        if materials:
            parts.append("MATERIALS TO REVIEW:\n" + materials[:45000])
        if book_ctx:
            parts.append(
                "YOUR PRIOR RESEARCH (connect new material to what you already know):\n"
                + book_ctx
            )
        if skills_ctx:
            parts.append("REUSABLE PATTERNS FROM YOUR PRIOR WORK:\n" + skills_ctx)

        parts.append(
            "Respond in this structure:\n"
            "## Key Findings\n"
            "(What the material establishes or reveals from your expertise)\n\n"
            "## Concerns & Gaps\n"
            "(Errors, missing rigor, unstated assumptions, conflicts with known results)\n\n"
            "## Opportunities\n"
            "(Concrete research directions your lens unlocks)\n\n"
            "## Working Question Fit\n"
            "(How this material bears on the working question, or 'N/A' if none was given)"
        )

        prompt = "\n\n".join(parts)
        response = think_model.generate(system_prompt + "\n\n" + prompt)
        if response.text.strip().startswith("ERROR:"):
            return jsonify({
                'agent': agent_name,
                'error': response.text,
                'review': None,
            }), 503

        return jsonify({
            'agent': agent_name,
            'review': response.text,
            'review_id': review_id,
            'working_question': working_question or None,
            'book_context_used': bool(book_ctx),
            'book_sources': book_sources,
            'skills_context_used': bool(skills_ctx),
            'skill_sources': skill_sources,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    @app.route('/implement', methods=['POST'])
    def implement():
        data = request.get_json() or {}
        synthesis = data.get('synthesis', '')
        hypothesis = data.get('hypothesis', '')
        problem = str(data.get('problem_statement', ''))
        loop_id = data.get('loop_id')

        # Lighter context for code gen — hypothesis already carries the argument
        book_ctx, book_sources = _pull_book_context(
            agent_name,
            problem,
            query_extra=hypothesis,
            loop_id=loop_id,
            limit=2,
        )
        skills_ctx, skill_sources = _pull_skills_context(
            agent_name,
            f"{problem} {hypothesis}",
            loop_id=loop_id,
            limit=2,
        )

        backticks = "```"
        prompt_parts = [
            "IMPLEMENTATION PHASE — keep the script SHORT and RUNNABLE.",
            "HYPOTHESIS: " + hypothesis,
        ]
        if problem:
            prompt_parts.append("ORIGINAL PROBLEM: " + problem[:1200])
        if synthesis:
            prompt_parts.append("ORACLE SYNTHESIS CONTEXT: " + synthesis[:800])
        if book_ctx:
            prompt_parts.append(
                "PRIOR PATTERNS (reuse sparingly):\n" + book_ctx[:2000]
            )
        if skills_ctx:
            prompt_parts.append(
                "SKILL HINTS:\n" + skills_ctx[:1200]
            )
        prompt_parts.append(
            "TASK: Write a minimal Python script (~40–80 lines). "
            "Must be syntactically complete — close all brackets, strings, and fences. "
            "Save at least one .csv or .json to disk. No external APIs unless essential. "
            f"Focus: {implement_focus}\n"
            "Return ONLY:\nEXPERIMENT_NAME: <short_name>\n"
            + backticks + "python\n<complete runnable code>\n" + backticks
        )
        prompt = "\n\n".join(prompt_parts)

        def _gen_code(user_prompt: str):
            resp = code_model.generate(system_prompt + "\n\n" + user_prompt, use_code_model=True)
            if resp.text.strip().startswith("ERROR:"):
                return None, resp.text, None
            extracted = extract_python_code(resp.text)
            return extracted, resp.text, resp

        code, raw_text, _ = _gen_code(prompt)
        if code is None:
            return jsonify({
                'agent': agent_name,
                'error': raw_text,
                'code': None,
                'experiment_name': None,
            }), 503

        syntax_err = None
        try:
            compile(code, f"exp_{agent_name}.py", "exec")
        except SyntaxError as exc:
            syntax_err = exc

        if syntax_err:
            retry_prompt = (
                prompt
                + f"\n\nRETRY — previous code failed at line {syntax_err.lineno}: {syntax_err.msg}. "
                "Return ONE shorter, complete script (~50 lines max). "
                "Only the EXPERIMENT_NAME line and a single ```python block. No markdown prose."
            )
            code2, raw2, _ = _gen_code(retry_prompt)
            if code2:
                code, raw_text = code2, raw2
                try:
                    compile(code, f"exp_{agent_name}.py", "exec")
                    syntax_err = None
                except SyntaxError as exc2:
                    syntax_err = exc2

        name_match = re.search(r'EXPERIMENT_NAME:\s*(\S+)', raw_text or "")
        experiment_name = name_match.group(1) if name_match else 'unnamed_experiment'

        return jsonify({
            'agent': agent_name,
            'code': code,
            'experiment_name': experiment_name,
            'book_context_used': bool(book_ctx),
            'book_sources': book_sources,
            'skills_context_used': bool(skills_ctx),
            'skill_sources': skill_sources,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    app.agent_name = agent_name
    app.agent_port = agent_port
    return app

def run_agent(app: Flask, config: dict):
    print("Starting " + app.agent_name + " on port " + str(app.agent_port))
    print("Lab Capabilities: Sauron Vision & Artifact Vault Enabled")
    app.run(host='0.0.0.0', port=app.agent_port, debug=False)