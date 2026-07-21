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

# Load personas from single source (chimera_clone_squad.yaml / chimera_squad.yaml or your own).
# Clean: no debate rules, no sub-agent inheritance forced.
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from personas.loader import build_agent_config, get_persona
    HAS_LOADER = True
except Exception as _e:
    HAS_LOADER = False
    print("WARNING: personas.loader not available. Falling back to inline config (non-production).")

def extract_python_code(raw: str) -> str:
    """Pull runnable Python from LLM output (fences, preamble, truncation).

    Prefers the first ```python / ```py block that *compiles*. Falls back to
    generic fences, then unfenced text. Avoids grabbing ```text / ```json trees
    that often appear in engineering hypotheses (Linus file trees).
    """
    text = (raw or "").strip()
    if not text:
        return ""

    def _clean_block(block: str) -> str:
        lines = []
        for line in (block or "").splitlines():
            if re.match(r"^EXPERIMENT_NAME\s*:", line, re.IGNORECASE):
                continue
            if line.strip() in ("```python", "```py", "```"):
                continue
            lines.append(line)
        out = "\n".join(lines).strip()
        return re.sub(r"```\s*$", "", out).strip()

    def _compiles(src: str) -> bool:
        if not src or len(src) < 8:
            return False
        try:
            compile(src, "<extract>", "exec")
            return True
        except SyntaxError:
            return False

    candidates: list[str] = []
    # Labeled python fences — ```py must NOT match the start of ```python (else leftover "thon")
    for pattern in (
        r"```python\s*(.*?)\s*```",
        r"```py(?!thon)\s*(.*?)\s*```",
    ):
        for match in re.finditer(pattern, text, re.DOTALL | re.IGNORECASE):
            candidates.append(_clean_block(match.group(1)))

    # Generic fences — skip known non-python languages
    for match in re.finditer(r"```([a-zA-Z0-9_+-]*)\s*(.*?)\s*```", text, re.DOTALL):
        lang = (match.group(1) or "").lower()
        if lang in ("text", "json", "yaml", "yml", "bash", "sh", "md", "markdown", "toml", "ini", "csv"):
            continue
        if lang in ("python", "py"):
            continue  # already collected
        candidates.append(_clean_block(match.group(2)))

    # Truncated opening fence without close
    if not candidates:
        for opener in (r"```python\s*", r"```py\s*", r"```\s*"):
            match = re.search(opener + r"(.*)", text, re.DOTALL | re.IGNORECASE)
            if match:
                candidates.append(_clean_block(match.group(1)))
                break

    # Unfenced fallback: strip EXPERIMENT_NAME line
    if not candidates:
        candidates.append(_clean_block(text))

    # Prefer compiling candidate with most lines
    compiling = [c for c in candidates if _compiles(c)]
    if compiling:
        compiling.sort(key=lambda s: (-len(s.splitlines()), -len(s)))
        return compiling[0]

    # Best-effort longest non-empty
    candidates = [c for c in candidates if c]
    if not candidates:
        return ""
    candidates.sort(key=lambda s: (-len(s.splitlines()), -len(s)))
    return candidates[0]


def _strip_md_fences_for_prompt(text: str, max_len: int = 1800) -> str:
    """Hypothesis often embeds ```text file trees — strip fences so code model stays on task."""
    t = text or ""
    t = re.sub(r"```[a-zA-Z0-9_+-]*\n.*?```", "[code/tree omitted]", t, flags=re.DOTALL)
    t = re.sub(r"\n{3,}", "\n\n", t).strip()
    if len(t) > max_len:
        t = t[:max_len] + "\n…[truncated for code gen]"
    return t


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
        lab_id = os.getenv("LAB_ID", "example")
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

        # Lean memory for fat books (Albert etc.) — full vault walks + 12k prompts hang hypothesis
        book_limit = 2 if agent_name.lower() == "albert" else 3
        book_ctx, book_sources = _pull_book_context(
            agent_name,
            problem,
            loop_id=loop_id,
            limit=book_limit,
        )
        skills_ctx, skill_sources = _pull_skills_context(
            agent_name,
            problem,
            loop_id=loop_id,
            limit=2,
        )

        def _build_prompt(include_book: bool, include_skills: bool) -> str:
            parts = ["PROBLEM: " + problem]
            if data.get('context'):
                parts.append("LATEST LAB DATA/CONTEXT: " + str(data['context'])[:4000])
            if include_book and book_ctx:
                parts.append(
                    "YOUR PRIOR RESEARCH (from your book — build on this, do not repeat blindly):\n"
                    + book_ctx
                )
            if include_skills and skills_ctx:
                parts.append(
                    "REUSABLE PATTERNS FROM YOUR PRIOR EXPERIMENTS:\n" + skills_ctx
                )
            try:
                from getailab.loop_focus import hypothesis_focus_addon
                focus_extra = hypothesis_focus_addon()
            except Exception:
                focus_extra = (
                    "\nAim for 400–900 words with at least one falsifiable prediction."
                )
            return "\n\n".join(parts) + (
                "\n\nBased on your role and the available Lab tools, "
                "provide a high-rigor hypothesis as markdown prose only. "
                "Do NOT call shell tools or emit <tool_call> blocks — use the lab sandbox in Phase 2 for code. "
                "Aim for 400–900 words with at least one falsifiable prediction."
                + focus_extra
            )

        prompt = _build_prompt(True, True)
        print(f"[BASE] {agent_name} hypothesis: book_chars={len(book_ctx)} skills_chars={len(skills_ctx)}")
        response = think_model.generate(system_prompt + "\n\n" + prompt)

        # Retry once lean if model barfs, times out, or emits tool sludge
        def _is_bad(text: str) -> bool:
            t = (text or "").strip()
            if not t or t.startswith("ERROR:"):
                return True
            try:
                from llm.sanitize import sanitize_prose
                _, ok = sanitize_prose(t, min_chars=120)
                return not ok
            except Exception:
                return False

        if _is_bad(response.text):
            print(f"[BASE] {agent_name} hypothesis retry without book context...")
            prompt2 = _build_prompt(False, False)
            response = think_model.generate(system_prompt + "\n\n" + prompt2)

        if response.text.strip().startswith("ERROR:"):
            return jsonify({
                'agent': agent_name,
                'error': response.text,
                'hypothesis': None,
            }), 503

        try:
            from llm.sanitize import sanitize_prose
            hyp_text, hyp_ok = sanitize_prose(response.text, min_chars=120)
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

        # Cap hyp earlier and more aggressively (Linus long trees poison code gen)
        _hyp_cap = 1000 if agent_name.lower() == "linus" else 1500
        hyp_for_code = _strip_md_fences_for_prompt(str(hypothesis), max_len=_hyp_cap)
        problem_for_code = _strip_md_fences_for_prompt(problem, max_len=1000)

        # Linus: SPIKE (default single experiment) vs SHIP (script writes product package)
        linus_ship = False
        if agent_name.lower() == "linus":
            _ship_blob = f"{problem}\n{hypothesis}".lower()
            linus_ship = bool(
                re.search(r"\bproject\s*:", _ship_blob)
                or "product/" in _ship_blob
                or re.search(r"\bship\b", _ship_blob)
                or re.search(
                    r"\b(multi[- ]?file|package|packaging|setup\.py|pyproject|__init__\.py)\b",
                    _ship_blob,
                )
            )

        # Lighter context for code gen — hypothesis already carries the argument
        book_ctx, book_sources = _pull_book_context(
            agent_name,
            problem_for_code,
            query_extra=hyp_for_code[:400],
            loop_id=loop_id,
            limit=2,
        )
        skills_ctx, skill_sources = _pull_skills_context(
            agent_name,
            f"{problem_for_code} {hyp_for_code[:400]}",
            loop_id=loop_id,
            limit=2,
        )

        backticks = "```"
        prompt_parts = [
            "IMPLEMENTATION PHASE — keep the script SHORT and RUNNABLE.",
            "HYPOTHESIS (summary for the experiment only):\n" + hyp_for_code,
        ]
        if problem_for_code:
            prompt_parts.append("ORIGINAL PROBLEM: " + problem_for_code)
        if synthesis:
            prompt_parts.append("ORACLE SYNTHESIS CONTEXT: " + str(synthesis)[:600])
        if book_ctx:
            prompt_parts.append(
                "PRIOR PATTERNS (reuse sparingly):\n" + book_ctx[:1200]
            )
        if skills_ctx:
            prompt_parts.append(
                "SKILL HINTS:\n" + skills_ctx[:800]
            )
        try:
            from getailab.loop_focus import implement_focus_addon
            impl_mode = implement_focus_addon()
        except Exception:
            impl_mode = ""

        result_exit_rules = (
            "RESULT / EXIT DISCIPLINE (mandatory):\n"
            "- Print exactly one line: RESULT PASS or RESULT FAIL (no other variants).\n"
            "- On ANY failure path: print RESULT FAIL then sys.exit(1).\n"
            "- On success: print RESULT PASS then optionally sys.exit(0).\n"
            "- NEVER sys.exit(0) after RESULT FAIL. NEVER exit 0 if the experiment failed.\n"
        )
        import_cheatsheet = (
            "IMPORTS / PATHS (allow-list):\n"
            "- numpy, scipy, matplotlib, pandas as pd, sympy; torch CPU ok if needed.\n"
            "- NO tensorflow, NO jax.\n"
            "- matplotlib: call matplotlib.use('Agg') before pyplot import/use.\n"
            "- linregress: from scipy.stats import linregress (NOT scipy.optimize).\n"
            "- Commutators: from sympy.physics.quantum import Commutator "
            "(not from sympy import commutator).\n"
            "- Relative paths only (results.csv, ./out.json, plot.png) — "
            "NEVER /chimera/artifacts or absolute home paths.\n"
            "- Prefer existing product packages when relevant: import "
            "stateful_spectral_norm / lazy_spectral / stability etc. from "
            "PYTHONPATH product root rather than reimplementing from scratch.\n"
            "- CWD is the agent-private artifact dir; exp script path is separate. "
            "Relative opens (results.csv) stay private per agent.\n"
            "- JSON: float()/int()/bool() numpy scalars before json.dump.\n"
            "- os.makedirs(..., exist_ok=True) before writing subdirs.\n"
        )
        response_shape = (
            "RESPONSE SHAPE (strict):\n"
            "- Return ONLY an EXPERIMENT_NAME: <short_name> line + ONE ```python fence.\n"
            "- No directory trees, no bash, no markdown file listings, no multi-fence dumps.\n"
            "- No prose outside the fence. One complete runnable script only.\n"
        )

        if agent_name.lower() == "linus" and linus_ship:
            product_root_hint = (
                "os.environ.get('GETAILAB_PRODUCT_ROOT') or "
                "'/home/deadly/ai_dev/product'"
            )
            mode_block = (
                "MODE: SHIP (Linus product packaging).\n"
                "Write ONE Python script only (not multi-fence file trees). "
                "That script MAY write real modules under a product package using pathlib, "
                f"rooted at {product_root_hint}. "
                "Create package dirs with mkdir(parents=True, exist_ok=True), write modules, "
                "then run a smoke check via subprocess (import/run the package) and "
                "print RESULT PASS/FAIL with sys.exit based on smoke outcome. "
                "Still return only EXPERIMENT_NAME + one ```python fence — the script writes files.\n"
            )
        elif agent_name.lower() == "linus":
            mode_block = (
                "MODE: SPIKE (default).\n"
                "Single experiment script only — do NOT rewrite the product tree. "
                "No multi-file packaging; one runnable experiment in CWD.\n"
            )
        else:
            mode_block = (
                "Do NOT rewrite the whole product tree — one experiment script only.\n"
            )

        task_block = (
            "TASK: Write a minimal Python script (~40–80 lines). "
            "Must be syntactically complete — close all brackets, strings, and fences. "
            "Save at least one .csv or .json to the CURRENT WORKING DIRECTORY "
            "(relative paths). "
            "No external APIs unless essential. "
            f"Focus: {implement_focus}\n"
            + mode_block
            + import_cheatsheet
            + result_exit_rules
            + response_shape
            + impl_mode
            + "Return ONLY:\nEXPERIMENT_NAME: <short_name>\n"
            + backticks + "python\n<complete runnable code>\n" + backticks
        )
        prompt_parts.append(task_block)
        prompt = "\n\n".join(prompt_parts)

        def _empty_extract_response(err_msg: str, raw: str | None):
            """P0: surface raw LLM text so run_lab can stash into ticket notes."""
            raw_s = raw or ""
            err = err_msg or "ERROR: empty code extract"
            # Prefer a clear extract failure label when body was non-empty but unparseable
            if raw_s and not raw_s.startswith("ERROR:"):
                err = err if err.startswith("ERROR:") else f"ERROR: empty code extract — {err}"
            return jsonify({
                'agent': agent_name,
                'error': err[:2000] if isinstance(err, str) else str(err)[:2000],
                'code': None,
                'experiment_name': None,
                'raw_preview': raw_s[:2000],
                'extract_failed': True,
            }), 503

        def _gen_code(user_prompt: str, prefer_code_model: bool = True):
            """Return (code|None, raw_for_preview, resp).

            raw_for_preview always keeps something useful for ticket notes —
            adapter errors, empty replies, or unfenced garbage.
            If code model returns blank, automatically retry once with chat model.
            """
            attempts = []
            if prefer_code_model:
                attempts.append(True)
            attempts.append(False)  # chat fallback always available
            # de-dupe while preserving order
            seen = set()
            ordered = []
            for flag in attempts:
                if flag not in seen:
                    seen.add(flag)
                    ordered.append(flag)

            last_raw = ""
            last_resp = None
            for use_code in ordered:
                resp = code_model.generate(
                    system_prompt + "\n\n" + user_prompt,
                    use_code_model=use_code,
                )
                last_resp = resp
                raw = (resp.text or "").strip()
                tag = "code_model" if use_code else "chat_model"
                if not raw:
                    last_raw = f"ERROR: empty LLM reply ({tag} returned blank)"
                    continue
                if raw.startswith("ERROR:"):
                    last_raw = raw
                    continue
                extracted = extract_python_code(raw)
                if not extracted:
                    last_raw = raw
                    continue
                return extracted, raw, resp
            return None, last_raw or "ERROR: empty LLM reply", last_resp

        def _deterministic_fallback_code() -> str:
            """Last resort when every LLM path blanks — never leave Linus (or peers) empty.

            Short numpy experiment that always compiles and writes results.json.
            """
            claim = (hyp_for_code or problem_for_code or "smoke")[:180].replace("\\", "\\\\").replace("'", "\\'")
            return f'''import json, sys
import numpy as np
import pandas as pd

def main():
    rng = np.random.default_rng(42)
    x = rng.normal(size=(200, 4))
    y = (x[:, 0] + 0.3 * rng.normal(size=200) > 0).astype(int)
    # trivial linear probe
    w = np.linalg.lstsq(x, y.astype(float), rcond=None)[0]
    pred = (x @ w > 0.5).astype(int)
    acc = float((pred == y).mean())
    out = {{
        "experiment": "deterministic_fallback_{agent_name}",
        "agent": "{agent_name}",
        "claim": "{claim}",
        "accuracy": acc,
        "fallback": True,
    }}
    with open("results.json", "w") as f:
        json.dump(out, f, indent=2)
    pd.DataFrame([out]).to_csv("results.csv", index=False)
    print(json.dumps(out))
    if acc >= 0.5:
        print("RESULT PASS")
        sys.exit(0)
    print("RESULT FAIL")
    sys.exit(1)

if __name__ == "__main__":
    main()
'''

        code, raw_text, _ = _gen_code(prompt, prefer_code_model=True)
        # do not hard-fail yet — retries + deterministic fallback below

        syntax_err = None
        if code:
            try:
                compile(code, f"exp_{agent_name}.py", "exec")
            except SyntaxError as exc:
                syntax_err = exc
        else:
            syntax_err = None

        if syntax_err:
            retry_prompt = (
                prompt
                + f"\n\nRETRY — previous code failed at line {syntax_err.lineno}: {syntax_err.msg}. "
                "Return ONE shorter, complete script (~50 lines max). "
                "Only the EXPERIMENT_NAME line and a single ```python block. No markdown prose. "
                "On failure print RESULT FAIL then sys.exit(1); on success RESULT PASS then sys.exit(0)."
            )
            code2, raw2, _ = _gen_code(retry_prompt, prefer_code_model=True)
            if code2:
                code, raw_text = code2, raw2
                try:
                    compile(code, f"exp_{agent_name}.py", "exec")
                    syntax_err = None
                except SyntaxError as exc2:
                    syntax_err = exc2

        # Final rescue: minimal prompt, no book noise (Linus long hyps often die here)
        if syntax_err or not code:
            mini = (
                "Write ONE short complete Python experiment (~40 lines).\n"
                f"Claim to test: {hyp_for_code[:500]}\n"
                "Use numpy/scipy/pandas; matplotlib.use('Agg'); relative paths only. "
                "No tensorflow/jax. No directory trees or bash.\n"
                "RESULT / EXIT: print exactly RESULT PASS or RESULT FAIL. "
                "On failure: print RESULT FAIL then sys.exit(1). "
                "On success: print RESULT PASS then optionally sys.exit(0). "
                "NEVER exit 0 after RESULT FAIL. Save results.json.\n"
                "Return ONLY:\nEXPERIMENT_NAME: rescue_smoke\n"
                f"{backticks}python\n# code\n{backticks}\n"
            )
            code3, raw3, _ = _gen_code(mini, prefer_code_model=True)
            if code3:
                try:
                    compile(code3, f"exp_{agent_name}.py", "exec")
                    code, raw_text, syntax_err = code3, raw3, None
                except SyntaxError as exc3:
                    syntax_err = exc3
                    if code3:
                        code, raw_text = code3, raw3
            elif not code:
                # rescue extract also failed — keep latest raw for preview
                if raw3:
                    raw_text = raw3

        # Hard last resort: deterministic template so implement never 503s empty
        used_fallback = False
        if not code or syntax_err:
            fb = _deterministic_fallback_code()
            try:
                compile(fb, f"exp_{agent_name}.py", "exec")
                code = fb
                syntax_err = None
                used_fallback = True
                raw_text = (
                    (raw_text or "")
                    + "\n[DETERMINISTIC_FALLBACK] code model blank/broken; "
                    "using local numpy smoke template so loop can continue."
                )
            except SyntaxError:
                pass

        if not code:
            return _empty_extract_response(
                (raw_text or "ERROR: empty code after retries"),
                raw_text,
            )

        if syntax_err:
            # Still broken — surface as error so run_lab doesn't pretend success
            return jsonify({
                'agent': agent_name,
                'error': (
                    f"ERROR: syntax after retries line {syntax_err.lineno}: {syntax_err.msg}"
                ),
                'code': code,
                'experiment_name': 'syntax_fail',
                'raw_preview': (raw_text or "")[:2000],
                'extract_failed': False,
            }), 200  # run_lab checks error field

        name_match = re.search(r'EXPERIMENT_NAME:\s*(\S+)', raw_text or "")
        if used_fallback:
            experiment_name = f"deterministic_fallback_{agent_name}"
        else:
            experiment_name = name_match.group(1) if name_match else 'unnamed_experiment'

        return jsonify({
            'agent': agent_name,
            'code': code,
            'experiment_name': experiment_name,
            'book_context_used': bool(book_ctx),
            'book_sources': book_sources,
            'skills_context_used': bool(skills_ctx),
            'skill_sources': skill_sources,
            'used_deterministic_fallback': used_fallback,
            'timestamp': datetime.utcnow().isoformat()
        }), 200

    app.agent_name = agent_name
    app.agent_port = agent_port
    return app

def run_agent(app: Flask, config: dict):
    print("Starting " + app.agent_name + " on port " + str(app.agent_port))
    print("Lab Capabilities: Sauron Vision & Artifact Vault Enabled")
    app.run(host='0.0.0.0', port=app.agent_port, debug=False)