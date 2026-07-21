#!/usr/bin/env python3
"""
GET AI LAB - Commander Console & CLI
Cross-platform: Windows, macOS, Linux. Web dashboard via lab service.
Entry point for chat, status, web launch, research loops, and beef-up reference ingestion.

Beef up example:
  python3 run_lab.py --beef-up albert --file paper.md --title "Background Reading"
"""
import requests
import json
import time
import re
import sys
import os
import platform
import webbrowser
import argparse
import random
from argparse import Namespace
from datetime import datetime

# Line editing (backspace, arrows, history) on Unix/macOS/Docker TTY
try:
    import readline  # noqa: F401
except ImportError:
    pass

# Cross-platform color support (ANSI everywhere, graceful on Windows cmd/PowerShell)
def _supports_color():
    plat = platform.system().lower()
    if plat == 'windows':
        # Enable ANSI on modern Win10+ via env or assume; no colorama dep to keep pure
        # Best on Windows Terminal, PowerShell 7+, or VSCode. CMD may be limited - graceful fallback.
        return bool(os.environ.get('TERM') or 'ANSICON' in os.environ or 'WT_SESSION' in os.environ or os.environ.get('PROMPT'))
    return True

USE_COLOR = _supports_color()

def c(text, color=""):
    if not USE_COLOR or not color:
        return text
    codes = {"r": "\033[91m", "g": "\033[92m", "y": "\033[93m", "b": "\033[94m", "m": "\033[95m", "c": "\033[96m", "w": "\033[97m", "reset": "\033[0m"}
    return codes.get(color, "") + text + codes["reset"]


def _is_llm_error(text: str) -> bool:
    if not text:
        return True
    t = str(text).strip()
    if t.startswith("ERROR:") or "HTTPConnectionPool" in t or "Connection refused" in t:
        return True
    try:
        from llm.sanitize import has_tool_artifacts
        if has_tool_artifacts(t):
            return True
    except Exception:
        pass
    return False


def _is_ollama_timeout(err: str) -> bool:
    e = str(err).lower()
    return "timed out" in e or "timeout" in e


def _is_systemic_llm_failure(err: str) -> bool:
    """True when every scientist will fail the same way (e.g. Ollama down in Docker)."""
    if _is_ollama_timeout(err):
        return False
    e = str(err).lower()
    return any(
        token in e
        for token in (
            "host.docker.internal",
            "connection refused",
            "max retries exceeded",
            "failed to establish",
            "name or service not known",
            "connection error",
        )
    )


def _llm_fix_suggestions(sample_error: str = "") -> list:
    fixes = []
    err = str(sample_error).lower()
    in_docker = SCIENTIST_HOST_MODE == "docker" or "docker.internal" in err
    if in_docker:
        fixes.append("./scripts/ollama_for_docker.sh   — expose Ollama to containers")
        fixes.append("./boot_example.sh   — native boot (localhost Ollama, no Docker hop)")
    else:
        fixes.append("ollama serve   — start local Ollama")
        fixes.append("curl -s http://localhost:11434/api/tags   — should return model JSON")
    fixes.append("Set cloud LLM in .env: LLM_PROVIDER=openai + OPENAI_API_KEY")
    fixes.append("docker compose status   or   python3 run_lab.py --status")
    return fixes


def _service_fix_suggestions() -> list:
    return [
        "./boot_example.sh   — start native squad",
        "docker compose up -d   — start example lab in Docker",
        "python3 run_lab.py --status   — see what is offline",
        "tail -f logs/app_oracle.log   — oracle errors",
    ]


def _timeout_fix_suggestions() -> list:
    ollama_t = os.getenv("OLLAMA_TIMEOUT", "600")
    return [
        f"OLLAMA_TIMEOUT={ollama_t} in .env — Ollama generate wait (restart squad after change)",
        f"SCIENTIST_HTTP_TIMEOUT={SCIENTIST_HTTP_TIMEOUT} — HTTP limit from run_lab.py to each scientist",
        "Use a faster model in .env if replies are very slow (smaller quant / fewer parameters)",
        "curl -s http://localhost:11434/api/ps   — check if Ollama is stuck on another job",
        "tail -f logs/app_albert.log   — watch one scientist while testing",
        "Smoke test: curl -m 600 -X POST localhost:5025/hypothesis -H 'Content-Type: application/json' -d '{\"problem_statement\":\"test\"}'",
    ]


def _print_oops(
    title: str,
    what_happened: str,
    fixes: list,
    *,
    loop_id=None,
    report_path=None,
    markdown_log: str = "",
):
    """Friendly failure panel — explains what broke and how to fix it."""
    print(c("\n  ╭──────────────────────────────────────────────────────────────╮", "r"))
    print(c("  │  😅  OOPS — loop paused (nothing else will run usefully)      │", "r"))
    print(c("  ╰──────────────────────────────────────────────────────────────╯", "r"))
    print(c(f"\n  {title}", "y"))
    print(c(f"\n  What happened:\n  {what_happened}", "w"))
    print(c("\n  Try this:", "g"))
    for i, fix in enumerate(fixes, 1):
        print(c(f"    {i}. {fix}", "c"))
    if loop_id is not None:
        print(c(f"\n  Partial state saved: loop_{loop_id}_report.md", "m"))
        if report_path and markdown_log:
            note = (
                f"\n## ⚠️ Loop Aborted\n{title}\n\n{what_happened}\n\n"
                + "**Suggested fixes:**\n"
                + "\n".join(f"- {f}" for f in fixes)
                + "\n"
            )
            _append_live_report(report_path, note)
    print(c("\n  Fix the issue above, then start a fresh loop.\n", "w"))
    sys.stdout.flush()


def _abort_loop(
    *,
    title: str,
    what_happened: str,
    fixes: list,
    loop_id=None,
    report_path=None,
    markdown_log: str = "",
    tracker=None,
    reason: str = "aborted",
):
    _print_oops(title, what_happened, fixes, loop_id=loop_id, report_path=report_path, markdown_log=markdown_log)
    if tracker and loop_id is not None:
        try:
            tracker.close_loop(loop_id, reason[:500])
        except Exception:
            pass
    return False


def _probe_ollama_endpoint(endpoint: str) -> tuple:
    """Return (ok, detail_line) for a quick Ollama /api/tags probe."""
    url = f"{endpoint.rstrip('/')}/api/tags"
    try:
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            return True, f"GET {url} → 200 OK"
        return False, f"GET {url} → HTTP {resp.status_code}"
    except requests.exceptions.ConnectionError:
        return False, f"GET {url} → connection refused (is ollama serve running?)"
    except requests.exceptions.Timeout:
        return False, f"GET {url} → timed out (Ollama busy or hung — try: pkill ollama; ollama serve)"
    except Exception as exc:
        return False, f"GET {url} → {exc}"


def _ensure_llm_ready() -> bool:
    """Abort loops early if the configured LLM backend is down."""
    try:
        from llm.adapter import create_default_adapter, get_env_provider_config
        cfg = get_env_provider_config()
        provider = cfg.get("provider", "ollama")
        endpoint = cfg.get("endpoint") or ""
        if provider == "ollama" and not endpoint:
            endpoint = "http://localhost:11434"

        # Retry — Ollama can be slow to answer while loading a model
        adapter = create_default_adapter()
        for attempt in range(1, 4):
            if adapter.is_ready():
                info = adapter.get_info()
                _emit(
                    f"🧠 LLM ready: {info.get('provider', '?')} @ {info.get('endpoint', '?')}",
                    "g",
                )
                return True
            if attempt < 3:
                _emit(f"   LLM probe {attempt}/3 failed — retrying in 3s …", "y")
                time.sleep(3)

        probe_ok, probe_detail = (
            _probe_ollama_endpoint(endpoint) if provider == "ollama" else (False, "")
        )
        sample = f"{provider} @ {endpoint or '(default)'}"
        if provider == "ollama" and "docker.internal" in str(endpoint):
            detail = (
                "Ollama is not reachable from this Docker runtime.\n"
                f"  Probe: {probe_detail}\n"
                "  Containers use host.docker.internal — Ollama must listen on 0.0.0.0."
            )
        elif provider == "ollama":
            detail = (
                "Ollama did not respond to health checks.\n"
                f"  Probe: {probe_detail}\n"
                "  If you just started the squad, wait a few seconds and retry."
            )
        else:
            detail = f"Cloud provider '{provider}' is not ready — check API key and .env."
        _print_oops(
            "LLM backend offline — loop would fail on every scientist.",
            detail,
            _llm_fix_suggestions(sample),
        )
        return False
    except Exception as exc:
        _print_oops(
            "Could not verify LLM backend.",
            str(exc),
            _llm_fix_suggestions(),
        )
        return False


def prompt_line(message: str = "", *, color: str = "w", prompt: str = "> ") -> str:
    """Editable prompt — message is printed separately; input uses a plain prompt string.

    Prefers stdin when it is a TTY; otherwise tries /dev/tty so Commander can still
    answer the Phase-4 menu when stdout is piped/logged but a real terminal exists.
    """
    if message:
        print(c(message, color), flush=True)
    sys.stdout.flush()
    sys.stderr.flush()

    def _readline_from(fh) -> str:
        # Write prompt to stderr so it shows even if stdout is captured
        try:
            fh_out = sys.stderr if not sys.stdout.isatty() else sys.stdout
            fh_out.write(prompt)
            fh_out.flush()
        except Exception:
            print(prompt, end="", flush=True)
        line = fh.readline()
        if line == "":
            raise EOFError("EOF")
        return line.rstrip("\r\n").strip()

    # 1) Normal interactive stdin
    if sys.stdin.isatty():
        try:
            return input(prompt).strip()
        except EOFError:
            print(c("\n  ⚠️  EOF on stdin — no interactive input available.", "y"), flush=True)
            return ""

    # 2) Fallback: controlling terminal (common when run under wrappers/logs)
    try:
        with open("/dev/tty", "r") as tty_in:
            print(
                c("  (stdin is not a TTY — reading choice from /dev/tty)", "y"),
                flush=True,
            )
            return _readline_from(tty_in)
    except Exception as e:
        print(
            c(
                f"  ⚠️  No interactive input (stdin not a TTY, /dev/tty failed: {e}). "
                "Run in a real terminal: zsh /home/deadly/ai_dev/run_ai_dev.sh",
                "y",
            ),
            flush=True,
        )
        return ""

# Lab env bootstrap: base .env for secrets, then .env.<LAB_ID> so product labs
# are not silently stolen by LAB_ID=chimera in the root .env.
def _bootstrap_lab_env() -> None:
    try:
        from pathlib import Path
        from dotenv import load_dotenv
    except ImportError:
        return
    root = Path(__file__).resolve().parent
    # Do not override an already-exported LAB_ID from the shell / run_*.sh wrapper
    load_dotenv(root / ".env", override=False)
    lid = (os.getenv("LAB_ID") or "").strip()
    if lid:
        lab_env = root / f".env.{lid}"
        if lab_env.is_file():
            load_dotenv(lab_env, override=True)


_bootstrap_lab_env()

# Squad + service URLs — from data/labs/<LAB_ID>/config/lab.yaml (example lab default)
try:
    from getailab.lab_config import get_lab_id, get_scientists_dict, get_service_urls, load_lab_config
    ACTIVE_LAB_ID = get_lab_id()
    LAB_CONFIG = load_lab_config(ACTIVE_LAB_ID)
    SCIENTISTS = get_scientists_dict(ACTIVE_LAB_ID)
    _oracle_default, _lab_default = get_service_urls(ACTIVE_LAB_ID)
except Exception:
    ACTIVE_LAB_ID = os.getenv("LAB_ID", "example")
    LAB_CONFIG = {}
    SCIENTISTS = {
        'researcher': 5125,
        'critic': 5126,
    }
    _oracle_default, _lab_default = "http://localhost:5124", "http://localhost:5135"

def _loop_report_path(loop_id: int) -> str:
    """Per-lab loop report — always data/labs/<id>/reports/ (private vault via symlink)."""
    try:
        from getailab.lab_config import lab_reports_dir
        reports = lab_reports_dir(ACTIVE_LAB_ID)
        reports.mkdir(parents=True, exist_ok=True)
        return str(reports / f"loop_{loop_id}_report.md")
    except Exception:
        # last resort: still prefer vault-style path under cwd
        fallback = Path("data") / "labs" / str(ACTIVE_LAB_ID) / "reports"
        fallback.mkdir(parents=True, exist_ok=True)
        return str(fallback / f"loop_{loop_id}_report.md")


ORACLE_URL = os.getenv("ORACLE_URL", _oracle_default).rstrip("/")
LAB_URL = os.getenv("LAB_URL", _lab_default).rstrip("/")
DASHBOARD_URL = os.getenv("DASHBOARD_URL", f"{LAB_URL}/")
SCIENTIST_HOST_MODE = os.getenv("SCIENTIST_HOST_MODE", "localhost").strip().lower()
SCIENTIST_HTTP_TIMEOUT = int(os.getenv("SCIENTIST_HTTP_TIMEOUT", "600"))
ORACLE_SYNTH_TIMEOUT = int(os.getenv("ORACLE_SYNTH_TIMEOUT", "300"))


def scientist_url(name: str, port: int) -> str:
    """Resolve a scientist agent URL. Set SCIENTIST_HOST_MODE=docker in compose."""
    override = os.getenv(f"SCIENTIST_{name.upper()}_URL", "").strip()
    if override:
        return override.rstrip("/")
    if SCIENTIST_HOST_MODE == "docker":
        return f"http://{name}:{port}"
    host = os.getenv("SCIENTIST_HOST", "localhost").strip() or "localhost"
    return f"http://{host}:{port}"

def get_platform_info():
    return {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "node": platform.node()
    }

def print_platform_support_matrix():
    """Report full cross-platform status for GetAiLab / the example lab. Used by --support / --platforms."""
    plat = get_platform_info()
    print(c("\n" + "="*80, "c"))
    print(c("GETAILAB / GET AI LAB — PLATFORM SUPPORT", "g"))
    print(c(f"Current Host: {plat['system']} {plat['release']} ({plat['machine']}) | Python {plat['python']}", "w"))
    print(c("="*80, "c"))
    matrix = [
        ("Web / PWA Dashboard + Chat", "✅ Full (any browser + install to home)"),
        ("Windows (10/11)", "✅ Full CLI + services (python run_lab.py). Desktop launcher. Docker Desktop."),
        ("macOS (Intel + Apple Silicon)", "✅ Full CLI + zsh/bash. desktop_launcher. Docker Desktop."),
        ("Linux (all distros)", "✅ Full native bash + systemd. CLI + launcher + Docker."),
        ("Android (Chrome + WebView)", "✅ PWA (add to home) + mobile_chat_stub.html + /api/mobile/* . Native WebView bridge ready."),
        ("iOS (Safari + WKWebView)", "✅ PWA + stub + WKWebView JS bridge. Same APIs as desktop/CLI."),
    ]
    for name, status in matrix:
        print(c(f"  • {name}: {status}", "reset"))
    lab_port = LAB_URL.rsplit(":", 1)[-1].rstrip("/")
    ora_port = ORACLE_URL.rsplit(":", 1)[-1].rstrip("/")
    sci_ports = ", ".join(f"{n}:{p}" for n, p in sorted(SCIENTISTS.items())) or "(none)"
    print(c(f"\nBackend (LAB_ID={ACTIVE_LAB_ID}): lab :{lab_port}, oracle :{ora_port}, scientists: {sci_ports}.", "m"))
    print(c("Docker: Universal portable backend on any host with Docker (Linux native, Win/Mac via Docker Desktop).", "b"))
    print(c("CLI Chat: run_lab.py --chat works identically, tags source/platform for server.", "y"))
    print(c("="*80 + "\n", "c"))

def print_header(title):
    plat = get_platform_info()
    header = f"\n{'='*80}\n🚀 {title.upper()}\nPlatform: {plat['system']} {plat['release']} | Python {plat['python']}\n{'='*80}"
    print(c(header, "c"))
    sys.stdout.flush()


def print_welcome_splash():
    """Commander Console intro — shown once at interactive startup."""
    plat = get_platform_info()
    print(c("", "reset"))
    print(c("  ╔══════════════════════════════════════════════════════════════════════╗", "c"))
    print(c("  ║                                                                      ║", "c"))
    print(c("  ║   ⚗️   GET AI LAB  ·  GET AI LAB  ·  COMMANDER CONSOLE          ║", "c"))
    print(c("  ║                                                                      ║", "c"))
    lab_label = LAB_CONFIG.get("display_name") or ACTIVE_LAB_ID
    print(c(f"  ║   Lab: {lab_label[:58]:<58}  ║", "c"))
    print(c("  ║   Loop: Hypothesis → Implement → Execute → Synthesize → Direction    ║", "c"))
    print(c("  ║                                                                      ║", "c"))
    print(c("  ╚══════════════════════════════════════════════════════════════════════╝", "c"))
    print(c(f"  {plat['system']} {plat['release']} · {plat['machine']} · Python {plat['python']}", "w"))
    print(c(f"  Vault: data/labs/{ACTIVE_LAB_ID}/  ·  Dashboard: {LAB_URL}", "m"))
    print()


def _service_pulse_line() -> str:
    """One-line backend health for the welcome screen."""
    parts = []
    try:
        lab = requests.get(LAB_URL + "/health", timeout=2).json()
        parts.append(c("Lab ●", "g") if lab.get("status") else c("Lab ○", "r"))
    except Exception:
        parts.append(c("Lab ○ offline", "r"))
    try:
        oracle = requests.get(ORACLE_URL + "/health", timeout=2).json()
        parts.append(c("Oracle ●", "g") if oracle.get("status") == "healthy" else c("Oracle ○", "y"))
    except Exception:
        parts.append(c("Oracle ○ offline", "r"))
    online = sum(1 for name, port in SCIENTISTS.items()
                 if _probe_url(scientist_url(name, port) + "/health"))
    parts.append(c(f"Squad {online}/{len(SCIENTISTS)}", "g" if online == len(SCIENTISTS) else "y"))
    return "  " + "  ·  ".join(parts)


def _probe_url(url: str) -> bool:
    try:
        requests.get(url, timeout=1.5).raise_for_status()
        return True
    except Exception:
        return False


def _scientist_book_pages(name: str) -> int:
    try:
        from getailab.library import get_scientist_book
        book = get_scientist_book(name.lower())
        return book.page_count() if book else 0
    except Exception:
        return 0


def _print_squad_books():
    """Show each scientist's research book size."""
    from personas.loader import get_persona, get_squad_names

    print(c("\n  📚 Scientist research books (knowledge grows each loop + your references):", "m"))
    for name in get_squad_names():
        if name == "oracle":
            continue
        try:
            persona = get_persona(name)
            role = (persona.get("display_role") or persona.get("role", ""))[:44]
        except Exception:
            role = ""
        pages = _scientist_book_pages(name)
        bar = "█" * min(pages // 5, 12) if pages else "·"
        print(c(f"     {name.title():12} {pages:4} pg  {bar:<12}  {role}", "w"))
    print()


def _pick_scientist(*, allow_cancel: bool = True) -> str | None:
    """Numbered picker — returns lowercase scientist name or None."""
    from personas.loader import get_persona, get_squad_names

    names = [n for n in get_squad_names() if n != "oracle"]
    print(c("\n  Select a scientist:", "b"))
    for i, name in enumerate(names, 1):
        try:
            persona = get_persona(name)
            role = (persona.get("display_role") or "")[:40]
        except Exception:
            role = ""
        pages = _scientist_book_pages(name)
        print(c(f"    {i:2}. {name.title():12}  ({pages} pages)  {role}", "w"))
    if allow_cancel:
        print(c("     0. Cancel", "y"))
    raw = prompt_line(prompt="  Enter number: ")
    if allow_cancel and raw in ("0", "q", "quit", "cancel", ""):
        return None
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(names):
            return names[idx]
    except ValueError:
        match = raw.lower().strip()
        if match in names:
            return match
    print(c("  ⚠️  Invalid selection.", "y"))
    return None


def _print_main_menu():
    print(c("  ──────────────────────────────────────────────────────────────────────", "c"))
    print(c("  WHAT WOULD YOU LIKE TO DO?", "g"))
    print(c("  ──────────────────────────────────────────────────────────────────────", "c"))
    options = [
        ("1", "🔬", "Run a research loop", "I have a problem statement"),
        ("2", "✨", "Curiosity Portal", "No idea yet — let the Oracle muse for you"),
        ("3", "📚", "Beef up a scientist", "Add papers, notes, or URLs to their book"),
        ("4", "📖", "Browse references", "See what's already in a scientist's book"),
        ("5", "💬", "Council chat", "Talk to the live field + Oracle"),
        ("6", "🌐", "Open dashboard", f"Web UI at {LAB_URL}"),
        ("7", "📡", "System status", "Health check all services"),
        ("8", "🚪", "Exit", "Leave the Commander Console"),
        ("9", "🔥", "Forge new lab", "Wizard — custom squad + vault (uni_lab merge)"),
        ("10", "📋", "Collaborative review", "Squad reviews your docs → Oracle research paths"),
        ("11", "🏭", "Test & review product", "Oracle QA on Engineering product SoR"),
        ("12", "📦", "Run Engineering", "Engineering build from latest handoff"),
    ]
    for num, icon, label, hint in options:
        print(c(f"    {num}. {icon}  {label:<22}  {hint}", "w"))
    print(c("  ──────────────────────────────────────────────────────────────────────", "c"))
    print()


def interactive_product_review():
    """Oracle / commander: test & review packages under product SoR (Engineering)."""
    print_header("Engineering — Test & Review Product")
    try:
        from getailab.develop.product_line import (
            list_product_packages,
            production_line_banner,
            review_all_products,
            review_product_package,
        )
    except Exception as e:
        print(c(f"  ❌ product_line unavailable: {e}", "r"))
        return

    print(c(f"  {production_line_banner()}", "m"))
    listing = list_product_packages()
    pkgs = listing.get("packages") or []
    if not pkgs:
        print(c(f"  No packages under {listing.get('product_root')}", "y"))
        print(c("  Land something via handoff → Engineering, or write under product/.", "w"))
        return

    print(c("\n  Packages:", "b"))
    for i, p in enumerate(pkgs, 1):
        flags = []
        if p.get("has_smoke"):
            flags.append("smoke")
        if p.get("has_tests"):
            flags.append("tests")
        print(c(f"    {i:2}. {p['name']:<24} py={p.get('py_files', 0)}  {','.join(flags) or '—'}", "w"))
    print(c("     a. Review ALL packages (smoke + unittest)", "g"))
    print(c("     0. Cancel", "y"))

    raw = prompt_line(prompt="  Package number / name / a: ").strip().lower()
    if raw in ("0", "q", "quit", "cancel", ""):
        return

    run_smoke = prompt_line("  Run smoke? [Y/n]: ", prompt="").strip().lower() not in ("n", "no")
    run_tests = prompt_line("  Run unittest? [Y/n]: ", prompt="").strip().lower() not in ("n", "no")

    print(c("\n  → Running Engineering QA …", "y"))
    if raw in ("a", "all", "*"):
        out = review_all_products(run_smoke=run_smoke, run_tests=run_tests)
        print(c(f"\n  {out.get('oracle_summary')}", "g" if out.get("no_ship_count") == 0 else "y"))
        for r in out.get("results") or []:
            v = r.get("verdict", "?")
            col = "g" if v == "SHIP" else "r"
            print(c(f"    [{v}] {r.get('package')} — {r.get('oracle_summary', '')}", col))
        return

    # single package
    name = raw
    try:
        idx = int(raw) - 1
        if 0 <= idx < len(pkgs):
            name = pkgs[idx]["name"]
    except ValueError:
        pass

    out = review_product_package(name, run_smoke=run_smoke, run_tests=run_tests)
    v = out.get("verdict", "NO-SHIP")
    print(c(f"\n  Verdict: {v}", "g" if v == "SHIP" else "r"))
    print(c(f"  {out.get('oracle_summary')}", "m"))
    if out.get("smoke"):
        tail = (out["smoke"].get("stdout") or "")[-500:]
        if tail.strip():
            print(c("  --- smoke stdout (tail) ---", "c"))
            print(tail)
    if out.get("tests") and not out["tests"].get("success"):
        err = (out["tests"].get("stderr") or out["tests"].get("stdout") or "")[-500:]
        if err.strip():
            print(c("  --- test output (tail) ---", "y"))
            print(err)


def interactive_run_engineering():
    """Run Engineering on latest Oracle handoff."""
    print_header("Engineering — Run on Handoff")
    try:
        from getailab.handoff import (
            handoff_queue_dir,
            list_pending,
            list_handoffs,
            load_handoff,
            refresh_latest_pointer,
            resolve_handoff_path,
        )
    except Exception as e:
        print(c(f"  ❌ handoff unavailable: {e}", "r"))
        return

    # Lab isolation — never surface chimera / foreign pending packs
    try:
        from getailab.handoff import current_source_lab

        active = current_source_lab() or os.getenv("LAB_ID") or "ai_dev"
    except Exception:
        active = os.getenv("LAB_ID") or "ai_dev"
    print(c(f"  Handoff filter: source_lab={active}  (foreign labs excluded)", "m"))

    # Heal stale LATEST.<lab>.txt (common: pack moved to done/, pointer still under pending/)
    try:
        healed = refresh_latest_pointer()
        if healed:
            print(c(f"  Queue pointer → {healed}", "c"))
    except Exception:
        pass

    pending = list_pending()
    print(c(f"  Queue: {handoff_queue_dir() / 'pending'}  ({len(pending)} for {active})", "m"))
    if pending:
        for p in pending[:5]:
            print(c(f"    · {p.name}", "w"))
    else:
        print(c("  No pending packs for this lab. Create with Phase 4 → d", "y"))

    try:
        path = resolve_handoff_path()
        doc = load_handoff(path)
        src = str(doc.get("source_lab") or "")
        if src and src != active and active not in ("dev_shed", "engineering"):
            print(c(f"  ❌ Refuse foreign handoff source_lab={src!r} (active={active})", "r"))
            return
        print(c(f"  Handoff: {doc.get('handoff_id')} — {doc.get('title')}", "g"))
        print(c(f"  source_lab={src or '?'}  ·  {path.parent.name}/{path.name}", "c"))
        print(c(f"  Product: {doc.get('product_root') or os.getenv('GETAILAB_PRODUCT_ROOT', '/home/deadly/ai_dev/product')}", "w"))
        preview = (doc.get("dev_shed_problem") or "")[:400]
        if preview:
            print(c(f"  SoW preview:\n{preview}…\n", "w"))
        if path.parent.name != "pending":
            print(c(f"  ⚠️  This pack is already '{path.parent.name}' — re-running Engineering on it.", "y"))
    except Exception as e:
        print(c(f"  ⚠️  Could not load handoff: {e}", "y"))
        print(c("  Fix: Phase 4 → type exactly  d  (create pack from this loop), then  p", "g"))
        print(c("  Or:  python3 scripts/handoff_cli.py create --lab ai_dev --loop N --synthesis-file …", "w"))
        print(c("  Quarantine foreign: python3 scripts/handoff_cli.py quarantine --keep-lab ai_dev", "w"))
        return

    go = prompt_line("  Boot Engineering + one build loop now? [Y/n]: ", prompt="").strip().lower()
    if go in ("n", "no"):
        print(c("  Skipped. Manual: python3 scripts/handoff_cli.py run-engineering", "w"))
        return

    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "handoff_cli.py")
    try:
        import subprocess

        # Prefer resolved json path so CLI doesn't re-hit a dead LATEST
        jp = (doc.get("_paths") or {}).get("json") or str(path)
        subprocess.run(
            [sys.executable, script, "run-engineering", jp],
            cwd=os.path.dirname(os.path.abspath(__file__)),
        )
    except KeyboardInterrupt:
        print(c("\n  Engineering run cancelled.", "y"))
        return

    rev = prompt_line("  Run product test & review now? [Y/n]: ", prompt="").strip().lower()
    if rev not in ("n", "no"):
        interactive_product_review()


def interactive_beef_up_wizard():
    """Walk the user through adding knowledge to a scientist's book."""
    print_header("Beef Up — Feed the Scientists")
    print(c("  Add reference material before a loop — it surfaces in hypothesis & implement.", "m"))
    print(c("  Scientists remember patterns from their book, not your private user data.\n", "w"))

    scientist = _pick_scientist()
    if not scientist:
        return

    print(c("\n  How do you want to add knowledge?", "b"))
    print(c("    1. Paste text / notes", "w"))
    print(c("    2. Load from a file (.md, .txt, .pdf text, etc.)", "w"))
    print(c("    3. Fetch from a URL (web reader)", "w"))
    mode = prompt_line(prompt="  Choose [1/2/3]: ")

    title = ""
    content = ""
    url = ""
    file_path = ""

    if mode in ("2", "file", "f"):
        file_path = prompt_line("  File path: ")
        if not file_path or not os.path.isfile(file_path):
            print(c(f"  ❌ File not found: {file_path}", "r"))
            return
        title = prompt_line("  Title (Enter = filename): ", prompt="")
        if not title:
            title = os.path.basename(file_path)
    elif mode in ("3", "url", "u"):
        url = prompt_line("  URL: ")
        if not url:
            print(c("  ❌ URL required.", "r"))
            return
        title = prompt_line("  Title (Enter = auto): ", prompt="")
    else:
        print(c("  Enter your notes (single line OK; for long text use option 2 — file):", "y"))
        content = prompt_line("  Your notes: ")
        if not content:
            print(c("  ❌ No content provided.", "r"))
            return
        title = prompt_line("  Title for this reference: ")

    tags_raw = prompt_line("  Tags (comma-separated, optional): ", prompt="")
    tags = [t.strip() for t in tags_raw.split(",") if t.strip()] or None

    print(c(f"\n  → Archiving to {scientist.title()}'s book …", "y"))
    args = Namespace(
        beef_up=scientist,
        file=file_path or None,
        url=url or None,
        text=content or None,
        title=title,
        tags=",".join(tags) if tags else None,
        list_refs=False,
        beef_query="",
    )
    try:
        run_beef_up(args)
    except SystemExit:
        return
    print(c("\n  ✅ Knowledge ingested. It will appear in their next loop phases.", "g"))


def interactive_browse_refs():
    """Browse references in a scientist's book."""
    print_header("Scientist Reference Library")
    scientist = _pick_scientist()
    if not scientist:
        return
    query = prompt_line("  Search filter (Enter = show all): ", prompt="")
    args = Namespace(
        beef_up=scientist,
        list_refs=True,
        beef_query=query,
        file=None, url=None, text=None, title=None, tags=None,
    )
    run_beef_up(args)


def interactive_collaborative_review():
    """Walk the user through uploading material for squad review."""
    print_header("Collaborative Review — Squad Document Analysis")
    print(c("  Scientists review your material independently; Oracle synthesizes research paths.", "m"))
    print(c("  Great before a loop — or to stress-test a working question.\n", "w"))

    print(c("  How are you supplying material?", "b"))
    print(c("    1. File(s) on disk", "w"))
    print(c("    2. Paste inline notes", "w"))
    print(c("    3. URL (web reader)", "w"))
    print(c("    4. File(s) + working question (recommended)", "w"))
    mode = prompt_line(prompt="  Choose [1/2/3/4]: ")

    files: list = []
    text = ""
    urls: list = []
    question = ""

    if mode in ("4", "file+q", "fq"):
        raw_paths = prompt_line("  File path(s), comma-separated: ")
        files = [p.strip() for p in raw_paths.split(",") if p.strip()]
        question = prompt_line("  Working question (what should the squad assess?): ")
    elif mode in ("1", "file", "f"):
        raw_paths = prompt_line("  File path(s), comma-separated: ")
        files = [p.strip() for p in raw_paths.split(",") if p.strip()]
    elif mode in ("3", "url", "u"):
        url = prompt_line("  URL: ")
        if url:
            urls = [url]
    else:
        print(c("  Enter your notes (for long docs use option 1 — file):", "y"))
        text = prompt_line("  Your notes: ")

    if not question:
        question = prompt_line("  Working question (Enter to skip): ", prompt="")

    title = prompt_line("  Session title (Enter = auto from filename): ", prompt="")
    ingest_ans = prompt_line("  Ingest into scientist books? [Y/n]: ", prompt="").lower()
    ingest = ingest_ans not in ("n", "no")

    from scripts.collaborative_review import run_collaborative_review

    try:
        if not _ensure_llm_ready():
            return
        run_collaborative_review(
            files=files or None,
            text=text,
            urls=urls or None,
            question=question,
            title=title,
            ingest=ingest,
        )
    except Exception as e:
        print(c(f"  ❌ Review failed: {e}", "r"))
        print(c("  Ensure squad is up: ./boot_example.sh or python3 run_lab.py --status", "y"))


def _print_forged_labs_summary():
    """Show forged labs registered in data/labs/."""
    try:
        from getailab.lab_config import list_forged_labs
        labs = [c for c in list_forged_labs() if c.get("lab_id") != "example"]
        if not labs:
            return
        print(c("\n  🔥 Forged labs (switch with LAB_ID + .env.<id>):", "y"))
        for cfg in labs:
            lid = cfg.get("lab_id", "?")
            print(c(
                f"     {lid:16} Oracle :{cfg.get('oracle_port','?')}  "
                f"Lab :{cfg.get('lab_port','?')}  ·  ./boot_{lid}.sh",
                "w",
            ))
        print()
    except Exception:
        pass


def interactive_forge_lab():
    """Launch the Lab Forge wizard (scripts/create_lab.py)."""
    print_header("Lab Forge — Build Your Research Division")
    print(c("  Scaffolds personas, vault, scientist apps, and boot script.", "m"))
    print(c("  Ports auto-allocated — won't clash with the example lab.", "w"))
    print(c("  List labs: python3 scripts/create_lab.py --list-labs\n", "m"))
    script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "create_lab.py")
    try:
        import subprocess
        subprocess.run([sys.executable, script], cwd=os.path.dirname(os.path.abspath(__file__)))
    except KeyboardInterrupt:
        print(c("\n  Forge cancelled.", "y"))


def run_commander_console():
    """Interactive Commander Console — welcome, menu, and action routing."""
    print_welcome_splash()
    print(_service_pulse_line())
    if ACTIVE_LAB_ID != "example":
        print(c(f"  Active lab: {ACTIVE_LAB_ID} (not the shipped example lab — ensure ./boot_{ACTIVE_LAB_ID}.sh ran)", "y"))
    _print_forged_labs_summary()
    _print_squad_books()
    _print_main_menu()

    while True:
        choice = prompt_line("  Your choice [1-12]: ", prompt="").strip().lower()

        if choice in ("8", "exit", "quit", "q"):
            print(c("\n  👋 Field persists. See you in the lab.\n", "g"))
            break
        if choice in ("1", "loop", "research", "full"):
            run_full_loop()
        elif choice in ("2", "explore", "no idea", "no-idea", "muse", "surprise", "portal"):
            problem = explore_flow() or no_idea_flow()
            if problem:
                run_full_loop(problem)
        elif choice in ("3", "beef", "beef-up", "beef up", "knowledge", "reference"):
            interactive_beef_up_wizard()
        elif choice in ("4", "browse", "refs", "references", "library"):
            interactive_browse_refs()
        elif choice in ("5", "chat"):
            run_chat_mode()
        elif choice in ("6", "web", "dashboard"):
            open_dashboard()
        elif choice in ("7", "status"):
            print_header("System Status")
            print(json.dumps(check_services(), indent=2))
            print(_service_pulse_line())
        elif choice in ("9", "forge", "create", "create-lab", "new lab"):
            interactive_forge_lab()
        elif choice in ("10", "review", "collab", "collab-review", "collaborative"):
            interactive_collaborative_review()
        elif choice in ("11", "product", "test-product", "review-product", "qa", "production-qa"):
            interactive_product_review()
        elif choice in ("12", "production", "prod", "engineering", "eng", "devshed", "dev-shed", "handoff-run", "factory"):
            interactive_run_engineering()
        else:
            print(c("  ⚠️  Pick 1–12, or keyword (loop, product, engineering, production, explore, beef, review, forge, chat, status, exit).", "y"))
            continue

        print()
        _print_main_menu()


def _emit(text="", color=""):
    """Print and flush immediately so the user sees scientist output as it arrives."""
    print(c(text, color) if color else text)
    sys.stdout.flush()


def _append_live_report(report_path, text):
    try:
        with open(report_path, "a", encoding="utf-8") as fh:
            fh.write(text)
    except Exception as e:
        _emit(f"⚠️  Could not update live report ({e})", "y")


def _print_book_sources(name, sources):
    if not sources:
        return
    _emit(f"📚 [{name.upper()}] Research book sources ({len(sources)}):", "m")
    for src in sources:
        loop_part = f" loop {src['loop_id']}" if src.get("loop_id") else ""
        _emit(f"    ↳ [{src.get('page_type', '?')}{loop_part}] {src.get('title', src.get('page_id', ''))}", "reset")


def _get_ticket_tracker():
    try:
        from getailab.tickets import get_loop_ticket_tracker
        return get_loop_ticket_tracker()
    except Exception as exc:
        _emit(f"[Tickets] Tracking unavailable: {exc}", "y")
        return None

def extract_url(text):
    match = re.search(r'(https?://[^\s]+)', text)
    return match.group(0) if match else None

def call_sauron(url, query: str = ""):
    """
    Sauron Vision — structured extract via lab /vision/extract, with /web/read fallback.
    Wired into intake when the problem contains a URL (or --sauron-url).
    """
    q = (query or "Extract key technical claims, methods, figures, numbers, and citations.").strip()
    print(c("\n👁️  SAURON VISION ACTIVATED — " + url + "...", "y"))
    timeout = int(os.getenv("SAURON_HTTP_TIMEOUT", "45"))
    chunks = []

    # Primary: vision/extract (Sauron stack — HTTP+LLM, optional browser/vision via env)
    try:
        res = requests.post(
            LAB_URL + "/vision/extract",
            json={"url": url, "query": q},
            timeout=timeout,
        ).json()
        if res.get("success"):
            print(c("✅ Sauron /vision/extract OK.", "g"))
            text = res.get("text") or ""
            if not text and res.get("data") is not None:
                text = json.dumps(res.get("data"), indent=2, ensure_ascii=False)
            if text:
                chunks.append("### Sauron Vision extract\n" + str(text)[:12000])
        else:
            err = res.get("error") or (res.get("data") or {}).get("error") or "unknown"
            print(c(f"⚠️  Sauron vision soft-fail: {err}", "y"))
    except Exception as e:
        print(c(f"⚠️  Sauron vision endpoint error: {e}", "y"))

    # Fallback / complement: raw web markdown
    try:
        res = requests.post(
            LAB_URL + "/web/read",
            json={"url": url},
            timeout=timeout,
        ).json()
        if res.get("success") and res.get("text"):
            print(c("✅ Sauron /web/read OK.", "g"))
            chunks.append("### Page text (web/read)\n" + str(res.get("text"))[:8000])
        elif not chunks:
            print(c("❌ Sauron failed to extract the page.", "r"))
    except Exception as e:
        if not chunks:
            print(c("❌ Lab connection error: " + str(e), "r"))
            return ""

    if not chunks:
        return ""
    header = (
        f"SAURON VISION CONTEXT (source: {url})\n"
        "Use this grounded material in hypotheses. Cite concrete claims; do not invent URLs.\n\n"
    )
    return header + "\n\n".join(chunks)


def _literature_via_module(query: str, max_per: int) -> dict:
    """In-process literature search — no lab HTTP hop (survives gate/offline sandbox)."""
    from getailab.literature_search import search_literature
    return search_literature(query, max_per_source=max_per)


def build_classroom_context(
    class_id: str = "",
    scope: str = "full",
    mark_job: str = "",
    mark_submission: str = "",
) -> str:
    """
    University classroom modules: curriculum pack + optional marking assist.
    Injected into every scientist as loop context (with literature/Sauron).
    """
    if not class_id and not mark_job:
        return ""
    chunks = []
    try:
        if class_id:
            from getailab.classroom import format_curriculum_context

            print(c(f"\n🎓 CLASSROOM — loading curriculum class={class_id} scope={scope}", "y"))
            cur = format_curriculum_context(class_id, scope=scope or "full")
            if cur.strip():
                chunks.append(cur)
                print(c(f"✅ Curriculum context ready ({len(cur)} chars).", "g"))
            else:
                print(c("⚠️  Curriculum empty — load files via university_classroom.py", "y"))
        if class_id and mark_job:
            from getailab.classroom import format_marking_context

            print(c(f"📝 MARKING ASSIST — job={mark_job}", "y"))
            mk = format_marking_context(
                class_id,
                mark_job,
                submission=mark_submission or None,
            )
            if mk.strip():
                chunks.append(mk)
                print(c(f"✅ Marking context ready ({len(mk)} chars).", "g"))
    except Exception as exc:
        print(c(f"⚠️  Classroom context failed: {exc}", "y"))
        return ""
    return "\n\n".join(chunks).strip()


def call_literature(query: str) -> str:
    """
    Loop grounding — **lab library + diary first** (default).
    External PubMed/arXiv only if LITERATURE_ALLOW_EXTERNAL=1.
    Prefer lab /literature/search; fall back to in-process module if lab 401/down.
    """
    if os.getenv("LITERATURE_SEARCH_ENABLED", "true").lower() in ("0", "false", "no", "off"):
        return ""
    prefer_lib = os.getenv("LITERATURE_PREFER_LIBRARY", "true").lower() not in (
        "0", "false", "no", "off",
    )
    allow_ext = os.getenv("LITERATURE_ALLOW_EXTERNAL", "false").lower() in (
        "1", "true", "yes", "on",
    )
    if prefer_lib and not allow_ext:
        print(c("\n📚 LAB GROUNDING — library shelf + diary (external APIs off)...", "y"))
    elif prefer_lib:
        print(c("\n📚 LAB GROUNDING — library first, external APIs allowed as fallback...", "y"))
    else:
        print(c("\n📚 LITERATURE SEARCH — live PubMed / arXiv (+ optional Semantic Scholar)...", "y"))
    # Client wait must exceed server-side parallel source timeouts (~40s)
    client_timeout = int(os.getenv("LITERATURE_CLIENT_TIMEOUT", "90"))
    max_per = int(os.getenv("LITERATURE_MAX_PER_SOURCE", "5"))
    prefer_direct = os.getenv("LITERATURE_DIRECT", "").lower() in ("1", "true", "yes", "on")
    # Library-only is local/fast — prefer direct module so we don't depend on lab process reload
    if prefer_lib and not allow_ext:
        prefer_direct = True
    res: dict = {}
    via = "lab"

    def _handle(res: dict, via: str) -> str:
        total = int(res.get("total") or 0)
        errs = res.get("errors") or []
        soft = res.get("soft_warnings") or []
        ok_sources = res.get("sources_ok") or []
        formatted = res.get("formatted") or ""
        q_used = (res.get("query") or "")[:120]
        mode = res.get("mode") or ""
        if formatted and total > 0:
            label = "hits" if "lab" in (mode or "") or "lab_local" in (ok_sources or []) else "papers"
            print(c(f"✅ Found {total} {label} via {ok_sources or 'local'} ({via}).", "g"))
            if q_used:
                print(c(f"   query: {q_used}", "c"))
            if mode:
                print(c(f"   mode:  {mode}", "m"))
            # show top titles so commander sees relevance
            papers = res.get("papers") or []
            for p in papers[:5]:
                title = (p.get("title") or "?")[:90]
                src = p.get("source") or "?"
                print(c(f"   · [{src}] {title}", "w"))
            if errs:
                print(c(f"   hard fail (ignored if others OK): {errs[0][:120]}", "y"))
            if soft:
                print(c(f"   soft: {soft[0][:120]}", "w"))
            return formatted[:15000]
        print(c("⚠️  Grounding empty — squad will rely on persona books + prior loops.", "y"))
        if q_used:
            print(c(f"   query was: {q_used}", "c"))
        if errs:
            print(c(f"   ({errs[0][:160]})", "y"))
        elif soft:
            print(c(f"   ({soft[0][:160]})", "y"))
        return formatted[:15000]

    if prefer_direct:
        try:
            return _handle(_literature_via_module(query, max_per), "direct module")
        except Exception as e:
            print(c("⚠️  Direct literature failed: " + str(e), "y"))
            return ""

    try:
        r = requests.post(
            LAB_URL + "/literature/search",
            json={"query": query, "max_per_source": max_per},
            timeout=client_timeout,
        )
        # Gate / HTML login page / non-JSON → fall through to in-process
        if r.status_code == 401 or "dashboard_gate" in (r.text or "")[:200]:
            raise RuntimeError(f"lab literature HTTP {r.status_code} (dashboard gate)")
        try:
            res = r.json()
        except Exception:
            raise RuntimeError(f"lab literature non-JSON HTTP {r.status_code}")
        if r.status_code >= 400 and not res.get("total"):
            raise RuntimeError(res.get("error") or f"lab literature HTTP {r.status_code}")
        return _handle(res, "lab HTTP")
    except Exception as e:
        print(c(f"⚠️  Lab literature path failed ({e}) — trying direct module…", "y"))
        try:
            return _handle(_literature_via_module(query, max_per), "direct module")
        except Exception as e2:
            print(c("⚠️  Literature search skipped: " + str(e2), "y"))
            return ""


# ============================================================
# NO-IDEA / ONBOARDING FLOW
# For users without a ready research question.
# Categories align with scientists/app_oracle.py generate_problem.
# ============================================================

CLI_NO_IDEA_CURATED = {
    "surprise": [
        "What open question would benefit most from multiple specialist perspectives and sandbox experiments?",
        "How can structured disagreement between researchers produce better hypotheses than consensus-seeking dialogue?",
    ],
    "foundations": [
        "What core assumption in a familiar domain should be tested before building further theory on top of it?",
        "Which definitions in a contested field are imprecise enough to block rigorous experimentation?",
    ],
    "frontiers": [
        "Where do current methods break down on problems that are high-stakes, novel, or poorly specified?",
        "What edge case would reveal whether a popular approach is robust or merely convenient?",
    ],
    "interdisciplinary": [
        "What connection between two fields is discussed informally but has never been modeled and tested?",
        "How would a tool from one discipline change conclusions in another if applied rigorously?",
    ],
    "applied": [
        "What practical system could be improved by a small, well-designed experiment rather than more opinion?",
        "Which real-world failure mode deserves a reproducible analysis before anyone proposes a fix?",
    ],
    "theoretical": [
        "What abstract question rewards clear formalization even if immediate data is limited?",
        "How can a thought experiment be turned into code that produces inspectable artifacts?",
    ],
    "historical": [
        "What past research program succeeded or failed for reasons we still misunderstand?",
        "Which old debate would change if revisited with modern tools and a multi-agent review loop?",
    ],
    "everyday": [
        "What seemingly simple phenomenon becomes interesting when you demand measurement and a testable model?",
        "Which everyday observation has a mechanism that specialists explain differently?",
    ],
    "personal": [
        "What question from lived experience could be reframed as a rigorous, testable research problem?",
        "How might family history or local context suggest a problem the squad can attack without losing rigor?",
    ],
    "library_fork": [
        "Building on a prior loop in this lab, what follow-up experiment would stress-test the last synthesis?",
        "Which conclusion from past artifacts should be revisited because new methods or data are available?",
    ],
}

CATEGORY_LABELS = {
    "surprise": "Surprise Me",
    "foundations": "Foundations & First Principles",
    "frontiers": "Frontiers & Open Problems",
    "interdisciplinary": "Interdisciplinary Connections",
    "applied": "Applied & Practical",
    "theoretical": "Theoretical & Formal",
    "historical": "Historical & Retrospective",
    "everyday": "Everyday Phenomena",
    "personal": "Personal Context",
    "library_fork": "Build on Past Loops",
}

def no_idea_flow():
    """The heart of the onboarding / no-idea experience.
    Presents inviting menu. Supports family note for personal resonance.
    Auto-generates (prefers live Oracle Muse + Library + personas; graceful fallback).
    Returns a fully-formed problem statement ready to kick off the loop.
    """
    print_header("NO RESEARCH IDEA? START HERE")
    print(c("You don't need a polished question — pick a category and the Muse will draft a problem statement.", "c"))
    print(c("The squad will then hypothesise, implement experiments, and synthesise results.", "m"))
    print()

    # Optional family / personal resonance (beautifully optional, never required)
    family_note = ""
    print(c("Optional personal thread (family history, ancestral mystery, lived experience, or a general curiosity):", "w"))
    print(c("(leave blank for pure universal resonance — or type a short note like 'grandfather was a watchmaker' or 'family stories of intuition')", "reset"))
    try:
        family_note = prompt_line(prompt="> ")
    except:
        pass
    if family_note:
        print(c(f"  ✓ Personal resonance noted. The Muse will weave it lightly.\n", "g"))

    # Category menu
    print(c("Choose a resonance chamber (or 0 for surprise):", "w"))
    cats = list(CATEGORY_LABELS.keys())
    for i, cat in enumerate(cats, 1):
        print(c(f"  [{i}] {CATEGORY_LABELS[cat]}", "reset"))
    print(c("  [0] Surprise me / any chamber", "y"))

    choice = "0"
    try:
        choice = prompt_line("\nYour choice (number): ", prompt="")
    except KeyboardInterrupt:
        print("\nPortal closed. The field remains open.")
        return None

    if choice == "0" or not choice.isdigit():
        category = "surprise"
    else:
        idx = int(choice) - 1
        category = cats[idx] if 0 <= idx < len(cats) else "surprise"

    label = CATEGORY_LABELS.get(category, "Surprise")
    print(c(f"\n✨ Entering {label} ...", "c"))

    # Try live Oracle Muse first (deep integration with personas + real Library DB)
    generated = None
    try:
        payload = {"category": category}
        if family_note:
            payload["family_note"] = family_note
        res = requests.post(f"{ORACLE_URL}/generate_problem", json=payload, timeout=35).json()
        if res.get("problem_statement"):
            generated = res
            print(c("  🧠 Oracle Muse responded (full Library + persona lens engaged).", "g"))
    except Exception as e:
        print(c(f"  (Oracle Muse offline or slow — using local curated resonance. {str(e)[:60]})", "y"))

    if not generated:
        # Pure local vision-grade curated (still excellent, integrates the same themes)
        bases = CLI_NO_IDEA_CURATED.get(category, CLI_NO_IDEA_CURATED["surprise"])
        base_ps = random.choice(bases)
        if family_note and category in ("personal", "everyday", "surprise") and len(family_note) > 4:
            base_ps = base_ps.rstrip(".") + f" — a thread lightly resonant with {family_note[:90]}."
        persona = random.choice(list(SCIENTISTS.keys()))
        generated = {
            "problem_statement": base_ps,
            "category": category,
            "persona_hint": persona,
            "muse_note": f"Local curated starter • {label} • Voiced near {persona}'s lens. (Full Muse available when Oracle is live.)",
            "source": "cli_local_curated",
            "family_infused": bool(family_note)
        }

    problem = generated["problem_statement"]
    print("\n" + "="*70)
    print(c("🦅 THE MUSE DELIVERS A PROBLEM STATEMENT", "g"))
    print("="*70)
    print(c(problem, "w"))
    print()
    print(c(f"Category: {generated.get('category')}", "reset"))
    print(c(f"Lens hint: {generated.get('persona_hint', 'council')}", "reset"))
    print(c(f"Note: {generated.get('muse_note', '')}", "m"))
    if generated.get("family_infused"):
        print(c("Personal resonance: woven in.", "c"))
    print("="*70 + "\n")

    # User approval / edit / regenerate
    while True:
        action = prompt_line(
            "Ignite this problem in the full dialectic loop? [Y]es / [E]dit / [N]ew resonance / [Q]uit portal: ",
            prompt="",
        ).lower()
        if action in ['y', 'yes', '']:
            print(c("🚀 Problem accepted. Launching the squad...", "g"))
            return problem
        elif action in ['e', 'edit']:
            try:
                edited = prompt_line("Edit the problem statement:")
                if edited:
                    problem = edited
                    print(c("Problem updated.", "g"))
                    # continue to confirm
            except:
                pass
        elif action in ['n', 'new', 'r', 'regenerate']:
            print(c("Drawing a fresh resonance from the same chamber...", "y"))
            # recurse lightly or pick new base
            if not generated.get("source", "").startswith("cli"):
                # try oracle again or local
                try:
                    res2 = requests.post(f"{ORACLE_URL}/generate_problem", json={"category": category, "family_note": family_note}, timeout=30).json()
                    problem = res2.get("problem_statement", problem)
                except:
                    problem = random.choice(CLI_NO_IDEA_CURATED.get(category, CLI_NO_IDEA_CURATED["surprise"]))
            else:
                problem = random.choice(CLI_NO_IDEA_CURATED.get(category, CLI_NO_IDEA_CURATED["surprise"]))
            print(c(f"\nNew statement:\n{problem}\n", "w"))
            # loop back for decision
        elif action in ['q', 'quit', 'exit']:
            print(c("Portal closed gracefully. You can always return with --no-idea or 'explore'.", "m"))
            return None
        else:
            print(c("Y to ignite, E to edit, N for new, Q to quit.", "y"))


# Convenience alias for --explore etc.
def explore_flow():
    return no_idea_flow()

def sanitize_problem_statement(problem: str) -> tuple:
    """Strip banner pollution and refuse empty/garbage charters.

    Returns (cleaned_problem, warnings_list). Raises ValueError if unusable.
    """
    warnings = []
    text = (problem or "").strip()
    if not text:
        raise ValueError("empty problem statement")

    # Strip decorative banner lines (====, ----, **** walls)
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        stripped = line.strip()
        if re.fullmatch(r"[=\-_*#~]{8,}", stripped):
            warnings.append("stripped banner line")
            continue
        cleaned_lines.append(line)
    text = "\n".join(cleaned_lines).strip()
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Collapse recycled report dumps: if mostly boilerplate after a short stem
    if len(text) > 4000:
        warnings.append(f"truncated problem from {len(text)} to 4000 chars")
        text = text[:4000].rstrip() + "\n…[truncated — paste a crisp charter, not a full report]"

    # Refuse bare stubs
    low = text.lower().strip()
    stub_patterns = (
        r"^goal\s*:\s*$",
        r"^goal\s*$",
        r"^todo\s*$",
        r"^tbd\s*$",
        r"^test\s*$",
        r"^n/?a\s*$",
    )
    for pat in stub_patterns:
        if re.fullmatch(pat, low):
            raise ValueError(
                f"problem statement is a stub ({text!r}). "
                "Provide a real project charter with acceptance criteria."
            )

    if len(text) < 12:
        raise ValueError(
            f"problem statement too short ({len(text)} chars). "
            "Need a real charter, not a one-word goal."
        )

    return text, warnings


def _implement_fail_notes(err: str, imp_res: dict = None) -> str:
    """Build ticket notes with raw LLM preview when code extract fails."""
    parts = [str(err or "implement failed")[:800]]
    raw = ""
    if isinstance(imp_res, dict):
        raw = (
            imp_res.get("raw_preview")
            or imp_res.get("raw_text")
            or ""
        )
        if imp_res.get("extract_failed"):
            parts.append("extract_failed=true")
    if raw:
        parts.append("--- raw_preview ---")
        parts.append(str(raw)[:2800])
    return "\n".join(parts)[:4000]


def _append_cli_lab_ops(event: dict) -> None:
    """Mirror implement/execute ops into vault logs/lab_ops.jsonl from CLI side."""
    try:
        vault = (os.getenv("GETAILAB_LAB_ROOT") or "").strip()
        if not vault:
            return
        log_dir = os.path.join(vault, "logs")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, "lab_ops.jsonl")
        payload = dict(event or {})
        payload.setdefault("ts", datetime.utcnow().isoformat() + "Z")
        payload.setdefault("lab_id", os.getenv("LAB_ID", ""))
        payload.setdefault("source", "run_lab")
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(payload, default=str) + "\n")
    except Exception:
        pass


def check_services():
    """Multi-platform health check for all components + lab ticket ledger."""
    status = {}
    try:
        lab = requests.get(LAB_URL + "/health", timeout=3).json()
        status['lab'] = lab
    except Exception:
        status['lab'] = {'status': 'offline'}
    try:
        oracle = requests.get(ORACLE_URL + "/health", timeout=3).json()
        status['oracle'] = oracle
    except Exception:
        status['oracle'] = {'status': 'offline'}
    for name, port in SCIENTISTS.items():
        try:
            h = requests.get(scientist_url(name, port) + "/health", timeout=2).json()
            status[name] = h
        except Exception:
            status[name] = {'status': 'offline'}

    # Extra commander detail: blocked implements + recent fails (ai_dev vault)
    ledger = _status_ticket_ledger()
    if ledger:
        status["ticket_ledger"] = ledger
    return status


def _status_ticket_ledger() -> dict:
    """Summarize blocked tickets / recent experiment fails for --status."""
    out = {}
    try:
        import sqlite3
        vault = (os.getenv("GETAILAB_LAB_ROOT") or "").strip()
        tickets_db = os.getenv("JOB_TICKETS_DB") or (
            os.path.join(vault, "job_tickets.db") if vault else ""
        )
        results_db = os.path.join(vault, "lab_results.db") if vault else ""

        if tickets_db and os.path.isfile(tickets_db):
            conn = sqlite3.connect(tickets_db)
            conn.row_factory = sqlite3.Row
            blocked = conn.execute(
                "SELECT COUNT(*) AS n FROM tickets WHERE status='blocked'"
            ).fetchone()["n"]
            by_agent = [
                dict(r)
                for r in conn.execute(
                    "SELECT assignee, COUNT(*) AS n FROM tickets "
                    "WHERE status='blocked' GROUP BY assignee ORDER BY n DESC"
                ).fetchall()
            ]
            recent = [
                {
                    "ticket_id": r["ticket_id"],
                    "title": r["title"],
                    "assignee": r["assignee"],
                    "notes": (r["notes"] or "")[:160],
                    "updated_at": r["updated_at"],
                }
                for r in conn.execute(
                    "SELECT ticket_id, title, assignee, notes, updated_at FROM tickets "
                    "WHERE status='blocked' ORDER BY updated_at DESC LIMIT 8"
                ).fetchall()
            ]
            linus_impl = [
                dict(r)
                for r in conn.execute(
                    "SELECT ticket_id, title, status, substr(notes,1,120) AS notes "
                    "FROM tickets WHERE assignee='linus' AND title LIKE '%implement%' "
                    "AND status='blocked' ORDER BY ticket_id DESC LIMIT 5"
                ).fetchall()
            ]
            conn.close()
            out["blocked_total"] = blocked
            out["blocked_by_assignee"] = by_agent
            out["blocked_recent"] = recent
            out["linus_blocked_implements"] = linus_impl

        if results_db and os.path.isfile(results_db):
            conn = sqlite3.connect(results_db)
            conn.row_factory = sqlite3.Row
            fails = [
                {
                    "loop_id": r["loop_id"],
                    "agent": r["agent_name"],
                    "stderr": (r["stderr"] or "")[:120],
                    "created_at": r["created_at"],
                }
                for r in conn.execute(
                    "SELECT loop_id, agent_name, stderr, created_at FROM lab_experiments "
                    "WHERE success=0 ORDER BY id DESC LIMIT 5"
                ).fetchall()
            ]
            conn.close()
            out["recent_experiment_fails"] = fails
    except Exception as exc:
        out["ledger_error"] = str(exc)[:200]
    return out

def run_chat_mode():
    """Enhanced interactive chat interface with the Council. Works in CLI on any platform. Mobile users use web companion."""
    print_header("GetAiLab Council Chat (Cross-Platform Live Mode)")
    plat = platform.system()
    print(c(f"Host platform: {plat} | Source tagged for server. Unified with web + /api/mobile/chat (Android/iOS).", "c"))
    print(c("Type your message to the Council. 'exit' to quit. 'pulse' to broadcast. 'status' for health.", "b"))
    print(c("This CLI chat uses the live field + Oracle. For full mobile/Android/iOS: open the PWA dashboard chat or load mobile_chat_stub.html.", "m"))
    history = []
    while True:
        try:
            msg = prompt_line(prompt="\n> YOU: ")
            if not msg: continue
            if msg.lower() in ['exit', 'quit', 'q']:
                print(c("Chat ended.", "g"))
                break
            if msg.lower() == 'status':
                print(json.dumps(check_services(), indent=2))
                continue
            if msg.lower() == 'pulse':
                try:
                    r = requests.post(LAB_URL + "/api/pulse", json={"message": "CLI pulse from " + platform.system()}).json()
                    print(c("FIELD PULSE: " + r.get('pulse', {}).get('message', 'Resonance sent.'), "y"))
                except Exception as e: print(c("Pulse error: " + str(e), "r"))
                continue
            
            # Real chat: call enhanced lab chat API (mobile + CLI unified)
            try:
                chat_res = requests.post(LAB_URL + "/api/chat", json={
                    "message": msg,
                    "source": "cli",
                    "platform": platform.system(),
                    "history": history[-4:]
                }, timeout=45).json()
                reply = chat_res.get('reply', 'The field is considering...')
                agent = chat_res.get('agent', 'ORACLE')
                print(c(f"\n🧠 [{agent}] : {reply}", "c"))
                history.append({"user": msg, "agent": agent, "reply": reply})
            except Exception as e:
                print(c(f"⚠️ Council temporarily unreachable ({e}). Using local resonance.", "y"))
                print(c("Services may be offline. Start the lab with boot_example.sh or docker compose up.", "m"))
        except KeyboardInterrupt:
            print(c("\nChat closed. Field persists.", "g"))
            break


def _coerce_dir_id(raw) -> int:
    """Direction ids must be int for ★ matching (model often returns string '1')."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _clean_next_problem(text: str) -> str:
    """Strip report/menu markdown so the next loop problem is plain prose."""
    s = (text or "").strip()
    s = re.sub(r"^#{1,6}\s*", "", s)
    s = re.sub(r"^\d+[\.)]\s*", "", s)
    s = re.sub(r"[★☆✦]\s*", "", s)
    s = s.replace("**", "").strip()
    # if someone pasted "### 1. Title ★\nbody", keep body when present
    lines = [ln.strip() for ln in s.splitlines() if ln.strip()]
    if len(lines) >= 2 and (len(lines[0]) < 100):
        # first line looks like a title — prefer rest as problem if longer
        rest = " ".join(lines[1:]).strip()
        if len(rest) > len(lines[0]):
            s = rest
    return s.strip()


def _print_research_directions(directions: list, oracle_pick: int, oracle_rationale: str):
    """Show Oracle's three suggested next-loop directions."""
    print(c("\n  🔮 Oracle — three possible next directions:\n", "m"))
    try:
        pick = int(oracle_pick)
    except (TypeError, ValueError):
        pick = 1
    for d in directions:
        idx = _coerce_dir_id(d.get("id", 0))
        title = d.get("title", f"Direction {idx}")
        stmt = d.get("problem_statement", "")
        rationale = d.get("rationale", "")
        leads = d.get("lead_scientists") or []
        marker = " ★" if idx == pick else ""
        print(c(f"  {idx}. {title}{marker}", "g" if idx == pick else "w"))
        if stmt:
            preview = stmt if len(stmt) <= 200 else stmt[:197] + "…"
            print(c(f"     → {preview}", "c"))
        if rationale:
            print(c(f"     {rationale}", "reset"))
        if leads:
            print(c(f"     Lead: {', '.join(str(x) for x in leads)}", "y"))
        else:
            print(c("     Lead: (unassigned)", "y"))
        print()
    if oracle_rationale:
        print(c(f"  Oracle's note: {oracle_rationale}", "m"))


def _normalize_phase4_choice(raw: str) -> str:
    """
    Map Phase-4 input to a menu key.

    Clipboard paste often glues text onto the key, e.g.
      '*Build directly on what the squad already agreed.*d'
    → treat trailing menu letter as the choice.
    """
    s = (raw or "").strip()
    if not s:
        return ""
    low = s.lower()
    keys = {
        "1", "2", "3", "o", "oracle", "d", "dev", "devshed", "handoff", "build",
        "p", "prod", "production", "factory", "run-dev-shed", "engineering", "eng",
        "t", "test", "qa", "review-product", "product-qa",
        "c", "custom", "own", "input",
        "q", "quit", "exit", "stop", "done", "n", "no",
    }
    if low in keys:
        return low

    # Pure trailing single key after junk / paste
    m = re.search(r"(?:^|[\s\*.,;:!?)\]\"'`]+)([123dptocq])\s*$", low)
    if m and len(s) > 1:
        key = m.group(1)
        print(c(f"  (paste+key detected — using menu key {key!r}, ignoring leading text)", "m"))
        return key

    # Long paste ending with a bare letter
    if len(low) > 8 and low[-1] in "123dptocq" and not low[-2].isalnum():
        key = low[-1]
        print(c(f"  (trailing menu key {key!r} after paste — using that)", "m"))
        return key

    return low


def _phase4_researcher_input(
    *,
    synthesis: str,
    original_problem: str,
    report_path: str,
    loop_id: str | int | None = None,
) -> tuple:
    """
    Direction picker — fifth work stage; CLI labels it Phase 4 (after hypothesis,
    experiment audit, synthesis). Researcher chooses next loop or quits.
    Returns (next_problem, markdown_note) or (None, '') to end the chain.
    """
    print_header("Phase 4: Researcher Input — What's Next?")
    print(c("  The loop is complete. Pick a direction for another loop, or stop here.\n", "w"))
    # Make pause state obvious to Commander
    once_env = os.getenv("GETAILAB_LOOP_ONCE", "")
    print(c(f"  GETAILAB_LOOP_ONCE={once_env!r}  stdin_tty={sys.stdin.isatty()}", "m"))
    if loop_id is not None:
        print(c(f"  loop_id={loop_id}", "m"))
    # Do NOT bail just because stdin is not a TTY — prompt_line falls back to /dev/tty.
    # Only hard-block when LOOP_ONCE is set (handled by caller before menu).

    directions = []
    oracle_pick = 1
    oracle_rationale = ""
    try:
        rec_payload = {
            "synthesis": synthesis,
            "problem_statement": original_problem,
            "user_comment": "",
        }
        if loop_id is not None:
            rec_payload["loop_id"] = loop_id
        rec_res = requests.post(
            ORACLE_URL + "/recommend_next",
            json=rec_payload,
            timeout=ORACLE_SYNTH_TIMEOUT,
        )
        rec_res.raise_for_status()
        data = rec_res.json()
        directions = data.get("directions") or []
        # Normalize ids to int so ★ and menu picks stay consistent
        for d in directions:
            d["id"] = _coerce_dir_id(d.get("id"))
            if d.get("problem_statement"):
                d["problem_statement"] = _clean_next_problem(d["problem_statement"])
            if d.get("title"):
                d["title"] = _clean_next_problem(d["title"]).split("\n")[0][:80]
        try:
            oracle_pick = int(data.get("oracle_pick") or 1)
        except (TypeError, ValueError):
            oracle_pick = 1
        if oracle_pick not in (1, 2, 3):
            oracle_pick = 1
        oracle_rationale = data.get("oracle_rationale", "")
    except Exception as e:
        print(c(f"  ⚠️  Could not fetch directions from Oracle: {e}", "y"))
        print(c("  You can still enter your own problem or quit.", "w"))

    if directions:
        _print_research_directions(directions, oracle_pick, oracle_rationale)
        dir_log = "\n## Oracle — Suggested Next Directions\n"
        for d in directions:
            idx = _coerce_dir_id(d.get("id", "?"))
            star = " ★" if idx == oracle_pick else ""
            dir_log += f"\n### {idx}. {d.get('title', 'Direction')}{star}\n"
            dir_log += d.get("problem_statement", "") + "\n"
            if d.get("rationale"):
                dir_log += f"\n*{d['rationale']}*\n"
            leads = d.get("lead_scientists") or []
            if leads:
                dir_log += f"\n**Lead:** {', '.join(str(x) for x in leads)}\n"
        if oracle_rationale:
            dir_log += f"\n**Oracle's pick ({oracle_pick}):** {oracle_rationale}\n"
        _append_live_report(report_path, dir_log + "\n")

    print(c("  ─────────────────────────────────────────────────────────────", "c"))
    print(c("  What would you like to do?", "b"))
    print(c("    1 / 2 / 3     Start next loop with that direction", "w"))
    print(c("    o             Let the Oracle decide (type o — Enter alone re-prompts)", "g"))
    print(c("    d             Handoff build requirements → Engineering", "g"))
    print(c("    p             Run Engineering now (latest handoff)", "g"))
    print(c("    t             Test & review product SoR (Engineering QA)", "g"))
    print(c("    c             Enter your own problem statement or URL", "w"))
    print(c("    q             Quit — finish here (report stays saved)", "w"))
    print(c("  ─────────────────────────────────────────────────────────────", "c"))
    print(c("  Waiting for your key… (1 / 2 / 3 / o / d / p / t / c / q then Enter)", "g"), flush=True)

    # Re-prompt until explicit key. Bare Enter used to mean "oracle auto" and
    # felt like the menu would not let the commander choose.
    choice = ""
    choice_raw = ""
    for _attempt in range(12):
        choice_raw = prompt_line(prompt="\n  Your choice [1/2/3/o/d/p/t/c/q]: ")
        choice = _normalize_phase4_choice(choice_raw)
        if choice == "":
            print(c("  (empty — type a key: 1 / 2 / 3 / o / d / p / t / c / q)", "y"), flush=True)
            continue
        break
    else:
        print(c("\n  👋 No choice after several prompts — stopping. Report saved.", "g"))
        return None, "\n## Researcher Input — Next Loop\n**Choice:** abandoned (no input)\n\n"

    if choice in ("q", "quit", "exit", "stop", "done", "n", "no"):
        print(c("\n  👋 Stopping here — report saved. No next loop.", "g"))
        return None, ""

    if choice in ("t", "test", "review-product", "qa", "product-qa"):
        print(c("\n  🏭 Engineering product QA…", "m"))
        try:
            interactive_product_review()
            note = "\n## Oracle — Engineering Product Review\nCommander ran Engineering QA from Phase 4 menu.\n\n"
            _append_live_report(report_path, note)
        except Exception as e:
            note = f"\n## Oracle — Engineering Product Review\n**FAILED:** {e}\n\n"
            print(c(f"  ⚠️  Review failed: {e}", "y"))
        more = prompt_line(prompt="  Continue research menu? [o/1/2/3/d/p/c/q]: ").strip().lower()
        if more in ("q", "quit", "", "n", "no"):
            return None, note
        choice = more if more != "o" else "o"

    if choice in ("p", "prod", "production", "factory", "run-dev-shed"):
        print(c("\n  📦 Engineering line…", "m"))
        note = ""
        try:
            interactive_run_engineering()
            note = "\n## Oracle — Engineering Run\nCommander launched Engineering on handoff from Phase 4.\n\n"
            _append_live_report(report_path, note)
        except Exception as e:
            note = f"\n## Oracle — Engineering Run\n**FAILED:** {e}\n\n"
            print(c(f"  ⚠️  Engineering run failed: {e}", "y"))
        more = prompt_line(prompt="  Continue research menu? [o/1/2/3/d/t/c/q]: ").strip().lower()
        if more in ("q", "quit", "", "n", "no"):
            return None, note
        choice = more if more != "o" else "o"

    if choice in ("d", "dev", "devshed", "handoff", "build"):
        note = _oracle_dev_shed_handoff(
            synthesis=synthesis,
            original_problem=original_problem,
            report_path=report_path,
            directions=directions,
            oracle_pick=oracle_pick,
            loop_id_hint=str(loop_id or ""),
        )
        # Stay in menu after handoff — offer production run immediately
        print(c("  Handoff written. Engineering options:", "m"))
        print(c("    p  Run Engineering now", "g"))
        print(c("    t  Test & review product SoR", "g"))
        print(c("    o/1/2/3/c  More research  ·  q  stop", "w"))
        more = prompt_line(prompt="  Continue? [p/t/o/1/2/3/c/q]: ").strip().lower()
        if more in ("q", "quit", "", "n", "no"):
            return None, note
        if more in ("p", "prod", "production"):
            try:
                interactive_run_engineering()
                note += "\n## Engineering\nRan Engineering after handoff.\n\n"
            except Exception as e:
                note += f"\n## Engineering\n**FAILED:** {e}\n\n"
            more2 = prompt_line(prompt="  Next? [t/o/1/2/3/c/q]: ").strip().lower()
            if more2 in ("t", "test", "qa"):
                try:
                    interactive_product_review()
                except Exception:
                    pass
                return None, note
            if more2 in ("q", "quit", "", "n", "no"):
                return None, note
            choice = more2 if more2 != "o" else "o"
        elif more in ("t", "test", "qa"):
            try:
                interactive_product_review()
            except Exception:
                pass
            return None, note
        elif more in ("o", "oracle", "1", "2", "3", "c"):
            choice = more if more != "o" else "o"
        else:
            return None, note

    # Explicit o only — empty Enter no longer auto-chains (was stealing the menu)
    if choice in ("o", "oracle", "decide", "auto"):
        if directions and 1 <= oracle_pick <= len(directions):
            picked = directions[oracle_pick - 1]
            problem = _clean_next_problem(picked.get("problem_statement", "") or picked.get("title", ""))
            title = _clean_next_problem(picked.get("title", f"Direction {oracle_pick}")).split("\n")[0][:80]
            print(c(f"\n  ✨ Oracle chose direction {oracle_pick}: {title}", "g"))
            if oracle_rationale:
                print(c(f"     {oracle_rationale}", "m"))
            leads = picked.get("lead_scientists") or []
            lead_line = f"**Lead:** {', '.join(str(x) for x in leads)}\n" if leads else ""
            note = (
                f"\n## Researcher Input — Next Loop\n"
                f"**Choice:** Oracle decided (direction {oracle_pick})\n"
                f"**Title:** {title}\n"
                f"**Problem:** {problem}\n"
                f"{lead_line}\n"
            )
            return problem, note
        fallback = "Continue rigorous analysis of the prior synthesis."
        print(c(f"\n  ✨ Oracle fallback: {fallback}", "g"))
        return fallback, f"\n## Researcher Input — Next Loop\n**Choice:** Oracle fallback\n**Problem:** {fallback}\n\n"

    if choice in ("1", "2", "3"):
        idx = int(choice)
        if directions and idx <= len(directions):
            picked = directions[idx - 1]
            problem = _clean_next_problem(picked.get("problem_statement", "") or picked.get("title", ""))
            title = _clean_next_problem(picked.get("title", f"Direction {idx}")).split("\n")[0][:80]
            print(c(f"\n  ▶ Starting next loop with direction {idx}: {title}", "g"))
            leads = picked.get("lead_scientists") or []
            lead_line = f"**Lead:** {', '.join(str(x) for x in leads)}\n" if leads else ""
            note = (
                f"\n## Researcher Input — Next Loop\n"
                f"**Choice:** Direction {idx}\n"
                f"**Title:** {title}\n"
                f"**Problem:** {problem}\n"
                f"{lead_line}\n"
            )
            return problem, note
        print(c("  ⚠️  That direction isn't available — enter your own instead.", "y"))
        choice = "c"

    if choice in ("c", "custom", "own", "input"):
        custom = prompt_line(
            "  Your problem statement or URL (Enter = cancel back to menu): ",
            prompt="  problem> ",
        )
        if not custom:
            return _phase4_researcher_input(
                synthesis=synthesis,
                original_problem=original_problem,
                report_path=report_path,
                loop_id=loop_id,
            )
        if custom.lower() in ("q", "quit", "exit"):
            return None, ""
        confirm = prompt_line(
            f"  Start next loop with that problem? [y/N]: ",
            prompt="  confirm> ",
        ).strip().lower()
        if confirm not in ("y", "yes"):
            print(c("  Cancelled — back to menu.", "y"))
            return _phase4_researcher_input(
                synthesis=synthesis,
                original_problem=original_problem,
                report_path=report_path,
                loop_id=loop_id,
            )
        print(c(f"\n  ▶ Starting next loop with your problem.", "g"))
        note = f"\n## Researcher Input — Next Loop\n**Choice:** Custom input\n**Problem:** {custom}\n\n"
        return custom, note

    # Long paste at the choice prompt used to auto-chain a loop (felt like "no menu").
    # Only accept free-text after explicit confirmation; short junk re-prompts.
    if choice_raw and choice not in (
        "1", "2", "3", "o", "oracle", "c", "q", "d", "p", "t",
        "quit", "exit", "stop", "done", "dev", "devshed", "handoff", "build",
        "prod", "production", "factory", "test", "qa", "review-product",
    ):
        if len(choice_raw) > 40 or " " in choice_raw.strip():
            print(c("  ⚠️  That looks like a full problem statement, not a menu key.", "y"))
            print(c(f"     preview: {choice_raw[:120]}…", "w") if len(choice_raw) > 120 else c(f"     text: {choice_raw}", "w"))
            confirm = prompt_line(
                "  Use this as the NEXT loop problem? [y/N]  (N = return to menu): ",
                prompt="",
            ).strip().lower()
            if confirm in ("y", "yes"):
                print(c(f"\n  ▶ Starting next loop with your free-text problem.", "g"))
                note = (
                    f"\n## Researcher Input — Next Loop\n"
                    f"**Choice:** Free text (confirmed)\n"
                    f"**Problem:** {choice_raw}\n\n"
                )
                return choice_raw, note
            print(c("  Returning to menu — pick 1/2/3/o/d/p/t/c/q.", "m"))
            return _phase4_researcher_input(
                synthesis=synthesis,
                original_problem=original_problem,
                report_path=report_path,
                loop_id=loop_id,
            )
        print(c(f"  ⚠️  Unknown choice {choice_raw!r} — try 1, 2, 3, o, d, p, t, c, or q.", "y"))
        return _phase4_researcher_input(
            synthesis=synthesis,
            original_problem=original_problem,
            report_path=report_path,
            loop_id=loop_id,
        )

    print(c("  ⚠️  Didn't recognise that — try 1, 2, 3, o, d, p, t, c, or q.", "y"))
    return _phase4_researcher_input(
        synthesis=synthesis,
        original_problem=original_problem,
        report_path=report_path,
        loop_id=loop_id,
    )


def _oracle_dev_shed_handoff(
    *,
    synthesis: str,
    original_problem: str,
    report_path: str,
    directions: list | None = None,
    oracle_pick: int = 1,
    loop_id_hint: str = "",
) -> str:
    """Oracle emits build requirements pack for Engineering; returns markdown note for report."""
    try:
        from getailab.handoff import create_handoff_from_loop
        from getailab.lab_config import get_lab_id

        lab_id = get_lab_id()
        # loop id from report path if present
        loop_id = loop_id_hint or "?"
        try:
            import re as _re

            m = _re.search(r"loop_(\d+)", str(report_path))
            if m:
                loop_id = m.group(1)
        except Exception:
            pass

        print(c("\n  📦 Oracle → Engineering handoff (build requirements)…", "m"))
        doc = create_handoff_from_loop(
            source_lab=lab_id,
            loop_id=str(loop_id),
            problem=original_problem,
            synthesis=synthesis,
            directions=directions or [],
            oracle_pick=oracle_pick,
            use_llm=True,
            report_path=str(report_path),
        )
        paths = doc.get("_paths") or {}
        print(c(f"  ✅ Handoff {doc.get('handoff_id')}: {doc.get('title')}", "g"))
        print(c(f"     JSON: {paths.get('json')}", "c"))
        print(c(f"     MD:   {paths.get('md')}", "c"))
        print(c("     Run:  python3 scripts/handoff_cli.py run-engineering", "y"))
        note = (
            f"\n## Oracle → Engineering Handoff\n"
            f"**handoff_id:** `{doc.get('handoff_id')}`\n"
            f"**title:** {doc.get('title')}\n"
            f"**priority:** {doc.get('priority')}\n"
            f"**json:** `{paths.get('json')}`\n"
            f"**md:** `{paths.get('md')}`\n\n"
            f"### Engineering problem\n\n"
            f"```\n{doc.get('dev_shed_problem', '')}\n```\n\n"
        )
        _append_live_report(report_path, note)
        return note
    except Exception as e:
        print(c(f"  ⚠️  Handoff failed: {e}", "y"))
        return f"\n## Oracle → Engineering Handoff\n**FAILED:** {e}\n\n"


def run_full_loop(
    problem=None,
    *,
    class_id: str = "",
    scope: str = "full",
    mark_job: str = "",
    mark_submission: str = "",
):
    """Original powerful dialectic loop, now platform-aware and resilient."""
    class_id = (class_id or os.getenv("UNIVERSITY_CLASS_ID") or "").strip()
    scope = (scope or os.getenv("UNIVERSITY_CLASS_SCOPE") or "full").strip()
    mark_job = (mark_job or os.getenv("UNIVERSITY_MARK_JOB") or "").strip()
    mark_submission = (mark_submission or os.getenv("UNIVERSITY_MARK_SUBMISSION") or "").strip()

    if mark_job and class_id and (not problem or str(problem).strip() in ("", "(auto)", "auto")):
        try:
            from getailab.classroom import build_marking_problem

            problem = build_marking_problem(
                class_id, mark_job, submission=mark_submission or None
            )
            print(c("📝 Auto problem from marking job:", "m"))
            print(c(problem[:500] + ("…" if len(problem) > 500 else ""), "w"))
        except Exception as exc:
            _print_oops("Could not build marking problem from job.", str(exc), [])
            return

    if not problem:
        raw = prompt_line(
            "Enter Initial Problem Statement (or paste a URL), or type 'explore'/'no idea'/'muse'/'surprise' for the Curiosity Portal:",
        )
        if raw.lower() in ['explore', 'no idea', 'muse', 'surprise', 'no-idea', 'portal']:
            problem = explore_flow() or no_idea_flow()
            if not problem:
                print(c("No problem from portal. Using a default resonance instead.", "y"))
                problem = random.choice(CLI_NO_IDEA_CURATED["surprise"])
        else:
            problem = raw
    if not _ensure_llm_ready():
        return

    loop_count = 1

    while True:
        print_header("Dialectic Loop #" + str(loop_count) + " Initiated")
        
        context_data = ""
        classroom_ctx = build_classroom_context(
            class_id=class_id,
            scope=scope,
            mark_job=mark_job,
            mark_submission=mark_submission,
        )
        if classroom_ctx:
            context_data = classroom_ctx
        url = extract_url(problem)
        # Explicit SAURON_URL env wins; else URL embedded in the problem statement
        sauron_url = (os.getenv("SAURON_URL") or "").strip() or url
        if sauron_url:
            sauron_ctx = call_sauron(sauron_url, query=problem[:500])
            context_data = (context_data + "\n\n" + sauron_ctx).strip() if context_data else sauron_ctx
        # Marking jobs default to skip literature noise (override with MARKING_LITERATURE=1)
        skip_lit = bool(mark_job) and os.getenv("MARKING_LITERATURE", "").lower() not in (
            "1",
            "true",
            "yes",
            "on",
        )
        if not skip_lit:
            lit_ctx = call_literature(problem)
            if lit_ctx:
                lit_block = "LITERATURE SEARCH CONTEXT\n" + lit_ctx
                context_data = (context_data + "\n\n" + lit_block).strip() if context_data else lit_block
        else:
            print(c("📚 Literature skipped for marking job (set MARKING_LITERATURE=1 to enable).", "m"))

        try:
            problem, _ps_warnings = sanitize_problem_statement(problem)
            for w in _ps_warnings:
                print(c(f"  ⚠️  problem sanitize: {w}", "y"))
        except ValueError as exc:
            _print_oops(
                "Problem statement rejected — fix the charter before looping.",
                str(exc),
                [
                    "Use a real PROJECT: … with acceptance criteria and product paths.",
                    "Do not paste full prior reports or banner walls of ====",
                    "Avoid stubs like 'goal:' alone.",
                ],
            )
            return

        try:
            res = requests.post(ORACLE_URL + "/initiate_loop", json={'problem_statement': problem}).json()
            loop_id = res['loop_id']
            print(c("\n[ORACLE] Loop " + str(loop_id) + " Registered in Agora DB.", "g"))
        except Exception as exc:
            _print_oops(
                "Oracle is offline — cannot register a loop.",
                str(exc),
                _service_status_suggestions(),
            )
            return

        report_path = _loop_report_path(loop_id)
        markdown_log = "# GetAiLab Loop " + str(loop_id) + "\n"
        markdown_log += "**Date:** " + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "\n"
        markdown_log += "**Problem:** " + problem + "\n"
        if class_id:
            markdown_log += f"**Class:** {class_id} · scope={scope or 'full'}\n"
        if mark_job:
            markdown_log += f"**Marking job:** {mark_job}\n"
            markdown_log += "**Mode:** marking_assist (lecturer is examiner of record)\n"
        markdown_log += "\n"
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(markdown_log)
        _emit(f"📝 Live report writing to {report_path} (updates after each scientist)", "m")

        raw_data_for_oracle = "PROBLEM: " + problem + "\n\n"

        tracker = _get_ticket_tracker()
        if tracker:
            parent_tid = tracker.open_loop(loop_id, problem)
            _emit(f"🎫 Loop ticket #{parent_tid} opened (phase tracking active)", "m")
        
        # --- Phase 1: Hypotheses ---
        print_header("Phase 1: Hypothesis Generation")
        _emit(
            f"ℹ️  Local Ollama: up to {SCIENTIST_HTTP_TIMEOUT}s per scientist "
            f"(large prompts + book context — grab a coffee for all 10).",
            "m",
        )
        hypotheses = {}
        failed_hypothesis = set()
        hyp_ok = 0
        hyp_llm_fail = 0
        hyp_timeout_fail = 0
        sample_llm_error = ""

        for name, port in SCIENTISTS.items():
            _emit(f"\n⏳ Waiting on {name.capitalize()}...", "y")
            hyp_tid = None
            if tracker:
                hyp_tid = tracker.start_phase(loop_id, name, "hypothesis", problem[:800])
            try:
                hyp_resp = requests.post(scientist_url(name, port) + "/hypothesis", json={
                    'problem_statement': problem,
                    'context': context_data,
                    'loop_id': loop_id,
                }, timeout=SCIENTIST_HTTP_TIMEOUT)
                if hyp_resp.status_code == 503:
                    res = hyp_resp.json()
                    hyp = res.get('error', 'LLM unavailable')
                    failed_hypothesis.add(name)
                    if _is_ollama_timeout(hyp):
                        hyp_timeout_fail += 1
                        _emit(
                            f"❌ {name.capitalize()} — Ollama reply timed out "
                            f"(local LLM slow on large prompts — not unreachable).",
                            "r",
                        )
                    else:
                        hyp_llm_fail += 1
                        _emit(f"❌ {name.capitalize()} — LLM unavailable.", "r")
                    if not sample_llm_error:
                        sample_llm_error = hyp
                    if tracker and hyp_tid:
                        tracker.fail(hyp_tid, name, hyp[:500])
                    if _is_ollama_timeout(hyp) and hyp_timeout_fail >= 2:
                        _abort_loop(
                            title="Ollama keeps timing out — needs more seconds per reply.",
                            what_happened=(
                                f"{hyp_timeout_fail} scientists hit the Ollama generate limit. "
                                "Each hypothesis sends persona + book context — several minutes "
                                "per scientist on local hardware is normal."
                            ),
                            fixes=_timeout_fix_suggestions(),
                            loop_id=loop_id,
                            report_path=report_path,
                            markdown_log=markdown_log,
                            tracker=tracker,
                            reason="Ollama timeouts",
                        )
                        return
                    if _is_systemic_llm_failure(hyp):
                        _emit("   ↳ Same issue will hit every scientist — stopping early.", "y")
                        _abort_loop(
                            title="LLM unreachable — all scientists would fail the same way.",
                            what_happened=hyp[:400],
                            fixes=_llm_fix_suggestions(hyp),
                            loop_id=loop_id,
                            report_path=report_path,
                            markdown_log=markdown_log,
                            tracker=tracker,
                            reason="LLM systemic failure",
                        )
                        return
                    continue
                res = hyp_resp.json()
                if res.get('error') or _is_llm_error(res.get('hypothesis', '')):
                    hyp = res.get('error') or res.get('hypothesis', 'LLM error')
                    failed_hypothesis.add(name)
                    hyp_llm_fail += 1
                    if not sample_llm_error:
                        sample_llm_error = hyp
                    _emit(f"❌ {name.capitalize()} — LLM error.", "r")
                    if tracker and hyp_tid:
                        tracker.fail(hyp_tid, name, hyp[:500])
                    if _is_systemic_llm_failure(hyp):
                        _emit("   ↳ Systemic LLM failure — stopping early.", "y")
                        _abort_loop(
                            title="LLM unreachable — all scientists would fail the same way.",
                            what_happened=hyp[:400],
                            fixes=_llm_fix_suggestions(hyp),
                            loop_id=loop_id,
                            report_path=report_path,
                            markdown_log=markdown_log,
                            tracker=tracker,
                            reason="LLM systemic failure",
                        )
                        return
                    continue

                hyp = res.get('hypothesis', 'ERROR')
                hypotheses[name] = hyp
                hyp_ok += 1

                if res.get('book_context_used'):
                    _print_book_sources(name, res.get('book_sources', []))
                
                _emit(f"\n🧠 [{name.upper()}] HYPOTHESIS:\n{hyp}\n{'-'*40}", "b")
                
                section = "## " + name.capitalize() + "'s Hypothesis\n" + hyp + "\n\n"
                markdown_log += section
                _append_live_report(report_path, section)
                raw_data_for_oracle += "[" + name.upper() + " HYPOTHESIS]: " + hyp + "\n"
                if tracker and hyp_tid:
                    tracker.complete(hyp_tid, name, f"Hypothesis: {len(hyp)} chars")
            except requests.exceptions.Timeout:
                failed_hypothesis.add(name)
                hyp_timeout_fail += 1
                _emit(
                    f"❌ {name.capitalize()} timed out after {SCIENTIST_HTTP_TIMEOUT}s "
                    f"(Ollama still generating — local LLM is slow, not dead).",
                    "r",
                )
                if tracker and hyp_tid:
                    tracker.fail(hyp_tid, name, f"timeout {SCIENTIST_HTTP_TIMEOUT}s")
                if hyp_timeout_fail >= 2:
                    _abort_loop(
                        title="Scientists keep timing out — Ollama needs more time per reply.",
                        what_happened=(
                            f"{hyp_timeout_fail} scientists hit the {SCIENTIST_HTTP_TIMEOUT}s HTTP limit. "
                            "Each hypothesis sends a large persona prompt plus book context to Ollama. "
                            "On local hardware this often takes several minutes per scientist."
                        ),
                        fixes=_timeout_fix_suggestions(),
                        loop_id=loop_id,
                        report_path=report_path,
                        markdown_log=markdown_log,
                        tracker=tracker,
                        reason="Scientist timeouts",
                    )
                    return
            except requests.exceptions.RequestException as e:
                failed_hypothesis.add(name)
                _emit(f"❌ {name.capitalize()} unreachable: {e}", "r")
                if tracker and hyp_tid:
                    tracker.fail(hyp_tid, name, str(e))
            except Exception as e:
                failed_hypothesis.add(name)
                _emit(f"❌ {name.capitalize()} hypothesis failed: {e}", "r")
                if tracker and hyp_tid:
                    tracker.fail(hyp_tid, name, str(e))

        if hyp_ok == 0:
            detail = (
                f"No scientist produced a hypothesis ({hyp_llm_fail} LLM errors, "
                f"{hyp_timeout_fail} timeouts, {len(failed_hypothesis)} total failures)."
            )
            if hyp_timeout_fail:
                fixes = _timeout_fix_suggestions()
            elif hyp_llm_fail:
                fixes = _llm_fix_suggestions(sample_llm_error)
            else:
                fixes = _service_fix_suggestions()
            _abort_loop(
                title="Phase 1 produced nothing usable — skipping experiments and synthesis.",
                what_happened=detail,
                fixes=fixes,
                loop_id=loop_id,
                report_path=report_path,
                markdown_log=markdown_log,
                tracker=tracker,
                reason="No hypotheses",
            )
            return

        if hyp_llm_fail:
            _emit(
                f"\n  ⚠️  {hyp_llm_fail} scientist(s) skipped (LLM/offline). "
                f"Continuing with {hyp_ok} who responded.",
                "y",
            )

        # --- Phase 2: Execution & Artifacts ---
        print_header("Phase 2: Experiment & Artifact Audit")
        code_ok = 0
        exec_ok = 0
        exec_fail = 0
        syntax_fail = 0
        for name, port in SCIENTISTS.items():
            if name in failed_hypothesis or name not in hypotheses:
                _emit(f"\n⏭️  Skipping {name.capitalize()} — no valid hypothesis.", "y")
                continue
            _emit(f"\n⏳ {name.capitalize()} is writing experiment...", "y")
            imp_tid = None
            exec_tid = None
            try:
                if tracker:
                    imp_tid = tracker.start_phase(
                        loop_id, name, "implement",
                        hypotheses.get(name, problem)[:800],
                    )
                imp_http = requests.post(scientist_url(name, port) + "/implement", json={
                    'hypothesis': hypotheses.get(name, problem),
                    'problem_statement': problem,
                    'loop_id': loop_id,
                }, timeout=None)
                if imp_http.status_code == 503:
                    try:
                        body = imp_http.json()
                        err = body.get('error', 'LLM unavailable')
                    except Exception:
                        body = {}
                        err = imp_http.text[:300] or 'LLM unavailable'
                    notes = _implement_fail_notes(err, body if isinstance(body, dict) else None)
                    _emit(f"❌ {name.capitalize()} — code generation failed (LLM).", "r")
                    _emit(f"   ↳ {str(err)[:240]}", "y")
                    if tracker and imp_tid:
                        tracker.fail(imp_tid, name, notes)
                    _append_cli_lab_ops({
                        "event": "implement", "loop_id": loop_id, "agent": name,
                        "success": False, "error": str(err)[:400],
                        "extract_failed": bool(isinstance(body, dict) and body.get("extract_failed")),
                    })
                    continue
                try:
                    imp_res = imp_http.json()
                except Exception:
                    _emit(f"❌ {name.capitalize()} — code generation failed (non-JSON response).", "r")
                    if tracker and imp_tid:
                        tracker.fail(imp_tid, name, "non-JSON implement response")
                    _append_cli_lab_ops({
                        "event": "implement", "loop_id": loop_id, "agent": name,
                        "success": False, "error": "non-JSON implement response",
                    })
                    continue
                if imp_res.get('error') or _is_llm_error(imp_res.get('code', '')):
                    err = imp_res.get('error') or imp_res.get('code', 'LLM error')
                    notes = _implement_fail_notes(err, imp_res)
                    _emit(f"❌ {name.capitalize()} — code generation failed.", "r")
                    _emit(f"   ↳ {str(err)[:240]}", "y")
                    if tracker and imp_tid:
                        tracker.fail(imp_tid, name, notes)
                    _append_cli_lab_ops({
                        "event": "implement", "loop_id": loop_id, "agent": name,
                        "success": False, "error": str(err)[:400],
                        "extract_failed": bool(imp_res.get("extract_failed")),
                    })
                    continue

                experiment_name = imp_res.get('experiment_name', 'unnamed_experiment')
                code = (imp_res.get('code') or '').strip()
                if not code:
                    notes = _implement_fail_notes(
                        "empty code",
                        {**imp_res, "extract_failed": True},
                    )
                    _emit(f"⚠️  {name.capitalize()} returned no code — skipping lab execute.", "y")
                    if tracker and imp_tid:
                        tracker.fail(imp_tid, name, notes)
                    _append_cli_lab_ops({
                        "event": "implement", "loop_id": loop_id, "agent": name,
                        "success": False, "error": "empty code", "extract_failed": True,
                    })
                    continue
                try:
                    compile(code, f"exp_{name}.py", "exec")
                except SyntaxError as syn:
                    syntax_fail += 1
                    notes = _implement_fail_notes(
                        f"syntax error line {syn.lineno}: {syn.msg}",
                        imp_res,
                    )
                    _emit(
                        f"❌ {name.capitalize()} — code still broken after retry "
                        f"(line {syn.lineno}: {syn.msg}). Skipping execute.",
                        "r",
                    )
                    if tracker and imp_tid:
                        tracker.fail(imp_tid, name, notes)
                    _append_cli_lab_ops({
                        "event": "implement", "loop_id": loop_id, "agent": name,
                        "success": False, "error": f"syntax line {syn.lineno}: {syn.msg}",
                    })
                    continue

                code_ok += 1
                if imp_res.get('book_context_used'):
                    _print_book_sources(name, imp_res.get('book_sources', []))
                
                _emit(f"🧪 [{name.upper()}] Experiment: {experiment_name}", "c")
                _emit("--- GENERATED CODE ---\n" + code + "\n--------------")
                
                if tracker and imp_tid:
                    tracker.complete(imp_tid, name, f"Experiment: {experiment_name}")

                _emit("⚙️  Executing code in Lab V2...")
                if tracker:
                    exec_tid = tracker.start_phase(loop_id, name, "execute", experiment_name)
                lab_res = requests.post(LAB_URL + "/execute", json={
                    'code': code, 'agent_name': name, 'loop_id': loop_id
                }, timeout=None).json()
                
                def _clean_report_text(t, limit=60_000):
                    if t is None:
                        return ""
                    if isinstance(t, bytes):
                        t = t.decode("utf-8", errors="replace")
                    t = str(t).replace("\x00", "")
                    if len(t) > limit:
                        t = t[:limit] + "\n...[truncated]...\n"
                    return t

                stdout = _clean_report_text(lab_res.get('stdout', ''))
                stderr = _clean_report_text(lab_res.get('stderr', ''))
                artifacts = lab_res.get('artifacts', [])
                run_success = lab_res.get('success', False)

                if not run_success:
                    exec_fail += 1
                    _emit(
                        f"❌ [{name.upper()}] LAB EXECUTION FAILED "
                        f"({len(artifacts)} artifacts, stderr below).",
                        "r",
                    )
                else:
                    exec_ok += 1
                    _emit(
                        f"✅ [{name.upper()}] LAB OK — {len(artifacts)} artifact(s).",
                        "g",
                    )
                
                if artifacts:
                    _emit("--- ARTIFACTS ---\n" + "\n".join(artifacts) + "\n--------------")
                else:
                    _emit("--- ARTIFACTS ---\nNone generated.\n--------------", "y")
                if stdout.strip():
                    _emit("--- STDOUT ---\n" + stdout + "\n--------------")
                if stderr.strip():
                    _emit("--- STDERR ---\n" + stderr + "\n--------------")
                
                bt = "```"
                exp_section = (
                    "## " + name.capitalize() + "'s Experiment\n"
                    + f"**Experiment:** {experiment_name}\n\n"
                    + bt + "python\n" + code + "\n" + bt + "\n"
                    + "### Lab Results\n**Artifacts:** " + (", ".join(artifacts) if artifacts else "None") + "\n"
                    + "**STDOUT:**\n" + bt + "text\n" + stdout + "\n" + bt + "\n"
                )
                if stderr:
                    exp_section += "**STDERR:**\n" + bt + "text\n" + stderr + "\n" + bt + "\n"
                exp_section += "\n"
                markdown_log += exp_section
                _append_live_report(report_path, exp_section)
                
                raw_data_for_oracle += "[" + name.upper() + " LAB RESULTS]:\nSTDOUT: " + stdout + "\nFILES: " + str(artifacts) + "\n"
                if tracker and exec_tid:
                    if run_success:
                        tracker.complete(
                            exec_tid, name,
                            f"{len(artifacts)} artifacts; stdout {len(stdout)} chars",
                        )
                    else:
                        tracker.fail(exec_tid, name, (stderr or "execution failed")[:500])
            except requests.exceptions.RequestException as e:
                _emit(f"❌ {name.capitalize()} experiment failed (network): {e}", "r")
                if tracker:
                    if imp_tid:
                        tracker.fail(imp_tid, name, str(e))
                    if exec_tid:
                        tracker.fail(exec_tid, name, str(e))
            except Exception as e:
                _emit(f"❌ {name.capitalize()} experiment failed: {e}", "r")
                if tracker:
                    if imp_tid:
                        tracker.fail(imp_tid, name, str(e))
                    if exec_tid:
                        tracker.fail(exec_tid, name, str(e))

        _emit(
            f"\n📊 Phase 2 audit: {code_ok} compiled OK · {exec_ok} executed OK · "
            f"{exec_fail} runtime failures · {syntax_fail} syntax failures",
            "c" if exec_ok else "y",
        )
        if exec_fail or syntax_fail:
            _emit(
                "   ↳ Check STDERR in the report. Cloud models may truncate long scripts — "
                "shorter experiments work better.",
                "y",
            )

        if code_ok == 0:
            _abort_loop(
                title="No runnable experiment code — synthesis would lack lab evidence.",
                what_happened=(
                    f"{hyp_ok} hypotheses OK, but 0 scripts passed syntax check. "
                    f"Syntax failures: {syntax_fail}. "
                    "Try OLLAMA_NUM_PREDICT_CODE=8192 in .env and restart the squad."
                ),
                fixes=_llm_fix_suggestions(sample_llm_error) if hyp_llm_fail else _timeout_fix_suggestions(),
                loop_id=loop_id,
                report_path=report_path,
                markdown_log=markdown_log,
                tracker=tracker,
                reason="No runnable code",
            )
            return

        if exec_ok == 0:
            _emit(
                f"\n⚠️  All {code_ok} script(s) compiled but none executed cleanly — "
                "Oracle will synthesize from hypotheses + stderr only.",
                "y",
            )

        # --- Phase 3: Synthesis ---
        print_header("Phase 3: Oracle Synthesis")
        print(c("⏳ Synthesizing Consensus Artefact for the squad...", "y"))
        syn_tid = tracker.start_phase(loop_id, "oracle", "synthesize", "Consensus artefact") if tracker else None
        archive_tid = None
        
        with open("oracle_last_payload.json", "w") as f:
            json.dump({'loop_id': loop_id, 'raw_data': raw_data_for_oracle}, f)

        oracle_response = None
        oracle_response = requests.post(
            ORACLE_URL + "/synthesize",
            json={
                'loop_id': loop_id,
                'raw_data': raw_data_for_oracle,
                'problem_statement': problem,  # belt-and-suspenders for correct loop framing
            },
            timeout=ORACLE_SYNTH_TIMEOUT
        )
        
        try:
            oracle_response.raise_for_status() 
            synth_res = oracle_response.json()
        except requests.exceptions.JSONDecodeError:
            _abort_loop(
                title="Oracle returned garbled data.",
                what_happened="Synthesis response was not valid JSON. Payload saved to oracle_last_payload.json.",
                fixes=_service_fix_suggestions() + ["tail -f logs/app_oracle.log"],
                loop_id=loop_id,
                report_path=report_path,
                markdown_log=markdown_log,
                tracker=tracker,
                reason="Oracle JSON error",
            )
            return
        except requests.exceptions.RequestException as e:
            detail = str(e)
            if oracle_response is not None and getattr(oracle_response, "status_code", 0) == 500:
                detail += (
                    "\n  Oracle likely hit the same LLM issue as the scientists. "
                    "Check logs/app_oracle.log."
                )
            _abort_loop(
                title="Oracle synthesis failed.",
                what_happened=detail,
                fixes=_llm_fix_suggestions(sample_llm_error) + ["tail -f logs/app_oracle.log"],
                loop_id=loop_id,
                report_path=report_path,
                markdown_log=markdown_log,
                tracker=tracker,
                reason="Synthesis failed",
            )
            if tracker and syn_tid:
                tracker.fail(syn_tid, "oracle", detail[:500])
            return

        synthesis = synth_res.get('synthesis', '')
        
        _emit(f"\n🔮 [ORACLE] CONSENSUS ARTEFACT:\n{synthesis}", "m")
        synth_section = "## Oracle's Consensus Artefact\n" + synthesis + "\n\n"
        markdown_log += synth_section
        _append_live_report(report_path, synth_section)

        if tracker:
            if syn_tid:
                tracker.complete(syn_tid, "oracle", f"Synthesis: {len(synthesis)} chars")
            if synth_res.get("library_archived"):
                archive_tid = tracker.start_phase(loop_id, "oracle", "archive", "Library vault ingest")
                summary = synth_res.get("library_summary") or {}
                archive_msg = f"{summary.get('pages_written', 0)} pages archived"
                attestation = summary.get("attestation") or {}
                sig = attestation.get("signature") or {}
                if sig.get("root_hash"):
                    archive_msg += f"; vault signed {sig['root_hash'][:16]}..."
                elif attestation.get("signed") is False:
                    archive_msg += "; vault sign skipped"
                tracker.complete(archive_tid, "oracle", archive_msg)
            summary = tracker.get_loop_summary(loop_id)
            completed = summary["by_status"].get("completed", 0)
            _emit(
                f"🎫 Loop {loop_id} tickets: {summary['ticket_count']} total, {completed} completed",
                "m",
            )
            tracker.close_loop(loop_id, f"Loop {loop_id} dialectic complete")

        try:
            from getailab.gabby.gabby import Gabby
            from pathlib import Path
            # User engagement profile only — NEVER writes scientist books / lab vault.
            # Keep under engine data/users (not mixed into /home/deadly/ai_dev knowledge).
            data_root = Path(__file__).resolve().parent / "data"
            gabby = Gabby("default", data_root)
            topic = problem[:200] if problem else ""
            adaptive = gabby.on_loop_completed(loop_id, topic=topic)
            _emit(
                f"📚 Adaptive learner (user profile only, not lab KB): "
                f"{adaptive.get('engagement_level')} "
                f"(AQF ~{adaptive.get('estimated_aqf_level')})",
                "m",
            )
        except Exception:
            pass
        
        # Web / automation: one loop then exit (no interactive Phase 4)
        once = os.getenv("GETAILAB_LOOP_ONCE", "").lower() in ("1", "true", "yes", "on")
        auto_ho = os.getenv("GETAILAB_HANDOFF_AUTO", "").lower() in ("1", "true", "yes", "on")
        _emit(
            f"  ⏸  post-synthesis: LOOP_ONCE={once} HANDOFF_AUTO={auto_ho} "
            f"stdin_tty={sys.stdin.isatty()}",
            "m",
        )
        # Auto handoff: only when explicitly requested — never surprise-skip the menu
        if auto_ho or (once and os.getenv("GETAILAB_HANDOFF_ON_ONCE", "0").lower() in (
            "1",
            "true",
            "yes",
            "on",
        )):
            # Skip auto-handoff when the loop *is* Engineering (dev_shed) (already building)
            try:
                from getailab.lab_config import get_lab_id as _glid

                _lid = _glid()
            except Exception:
                _lid = os.getenv("LAB_ID", "")
            if _lid not in ("dev_shed",) and synthesis:
                _oracle_dev_shed_handoff(
                    synthesis=synthesis,
                    original_problem=problem,
                    report_path=report_path,
                    directions=[],
                    oracle_pick=1,
                    loop_id_hint=str(loop_id),
                )
        if once:
            print(c("\n  👋 Single-loop mode (GETAILAB_LOOP_ONCE) — report saved. No menu.", "g"))
            print(c("     Unset GETAILAB_LOOP_ONCE to pause for 1/2/3/o/d/p/t/c/q.", "y"))
            break

        print(c("\n  ══════════════════════════════════════════════════════════", "c"))
        print(c("  COMMANDER: pick next action (menu will wait for your key)", "g"))
        print(c("  ══════════════════════════════════════════════════════════", "c"))
        next_problem, next_note = _phase4_researcher_input(
            synthesis=synthesis,
            original_problem=problem,
            report_path=report_path,
            loop_id=loop_id,
        )
        if next_problem is None:
            print(c("\n  👋 Loop chain ended. Report saved.", "g"))
            break
        problem = next_problem
        if next_note:
            _append_live_report(report_path, next_note)
        loop_count += 1

def open_dashboard():
    print(c(f"🌐 Opening GetAiLab Dashboard (Web + Mobile PWA ready): {DASHBOARD_URL}", "c"))
    try:
        webbrowser.open(DASHBOARD_URL)
    except Exception:
        print("Open manually in your browser.")


def run_beef_up(args):
    """Add user reference material to a scientist's research book (beef up brains)."""
    _root = os.path.dirname(os.path.abspath(__file__))
    if _root not in sys.path:
        sys.path.insert(0, _root)

    from getailab.library import add_scientist_reference, get_scientist_references
    from personas.loader import get_squad_names

    scientist = (args.beef_up or "").lower().strip()
    valid = [n for n in get_squad_names() if n != "oracle"]

    if scientist not in valid:
        print(c(f"❌ Unknown scientist '{scientist}'. Choose one of: {', '.join(valid)}", "r"))
        raise SystemExit(1)

    print_header(f"Beef Up — {scientist.title()}'s Research Book")

    if args.list_refs:
        result = get_scientist_references(scientist, query=args.beef_query or "")
        refs = result.get("references", [])
        print(c(f"📚 {len(refs)} reference page(s) in {scientist}'s book", "g"))
        for ref in refs:
            loop_part = f" | loop {ref['loop_id']}" if ref.get("loop_id") else ""
            print(c(f"  • [{ref['page_type']}{loop_part}] {ref['title']}", "w"))
            print(c(f"    {ref['snippet'][:160]}...", "reset"))
        return

    content = (args.text or "").strip()
    file_path = (args.file or "").strip()
    url = (args.url or "").strip()
    title = (args.title or "").strip()
    tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()] or None

    if file_path:
        if not os.path.isfile(file_path):
            print(c(f"❌ File not found: {file_path}", "r"))
            raise SystemExit(1)
        with open(file_path, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
        if not title:
            title = os.path.basename(file_path)
        source_label = "file"
    elif url:
        source_label = "url"
    else:
        source_label = "user"

    if not content and not url:
        print(c("❌ Provide reference material via --file, --url, or --text.", "r"))
        print(c("Examples:", "y"))
        print(c("  python3 run_lab.py --beef-up albert --file paper.md --title 'Background'", "reset"))
        print(c("  python3 run_lab.py --beef-up albert --url https://example.com/article", "reset"))
        print(c("  python3 run_lab.py --beef-up albert --text 'Key insight about geodesics on manifolds.'", "reset"))
        print(c("  python3 run_lab.py --beef-up albert --list-refs", "reset"))
        raise SystemExit(1)

    try:
        result = add_scientist_reference(
            scientist,
            title=title,
            content=content,
            url=url,
            tags=tags,
            source_label=source_label,
        )
    except Exception as e:
        print(c(f"❌ Beef-up failed: {e}", "r"))
        raise SystemExit(1)

    print(c(f"✅ Reference archived to {scientist}'s book", "g"))
    print(c(f"   Page: {result['page_id']}", "w"))
    print(c(f"   Title: {result['title']}", "w"))
    print(c(f"   Size: {result['content_length']} chars | source: {result['source']}", "w"))
    if result.get("url"):
        print(c(f"   URL: {result['url']}", "w"))
    print(c(f"\n📖 This material will surface in {scientist.title()}'s next hypothesis/implement phases.", "m"))


def main():
    parser = argparse.ArgumentParser(description="GetAiLab CLI — research loops, chat, dashboard.")
    parser.add_argument("--chat", action="store_true", help="Interactive council chat")
    parser.add_argument("--web", "--dashboard", action="store_true", help="Open the web dashboard")
    parser.add_argument("--status", action="store_true", help="Check service health")
    parser.add_argument("--support", "--platforms", "--matrix", dest="support", action="store_true", help="Print platform support and run commands")
    parser.add_argument("--problem", type=str, help="Problem statement to start a research loop")
    parser.add_argument(
        "--class",
        dest="class_id",
        type=str,
        default="",
        help="University classroom: class_id for curriculum context (e.g. COMP2001)",
    )
    parser.add_argument(
        "--scope",
        type=str,
        default="full",
        help="Curriculum scope: full | week:N | assessment:name | outcomes",
    )
    parser.add_argument(
        "--mark-job",
        dest="mark_job",
        type=str,
        default="",
        help="University marking assist job id (with --class)",
    )
    parser.add_argument(
        "--mark-submission",
        dest="mark_submission",
        type=str,
        default="",
        help="Optional submission filename filter for marking job",
    )
    parser.add_argument("--loop", action="store_true", help="Run full research loop (default behavior)")
    parser.add_argument("--no-idea", "--explore", "--surprise", dest="no_idea", action="store_true", help="No-idea onboarding: auto-generate a problem statement")
    parser.add_argument("--category", type=str, help="Category for --no-idea (e.g. applied, library_fork, personal)")
    parser.add_argument("--beef-up", metavar="SCIENTIST", help="Beef up a scientist's brain: add reference material to their book")
    parser.add_argument("--file", type=str, help="Reference file path (with --beef-up)")
    parser.add_argument("--url", type=str, help="URL to fetch as reference (with --beef-up)")
    parser.add_argument("--text", type=str, help="Inline reference note (with --beef-up)")
    parser.add_argument("--title", type=str, help="Reference title (with --beef-up)")
    parser.add_argument("--tags", type=str, help="Comma-separated tags (with --beef-up)")
    parser.add_argument("--list-refs", action="store_true", help="List references for --beef-up scientist")
    parser.add_argument("--beef-query", type=str, default="", help="Search filter when using --list-refs")
    parser.add_argument("--forge-lab", action="store_true", help="Launch Lab Forge wizard (custom research division)")
    parser.add_argument("--list-labs", action="store_true", help="List registered + forged research labs")
    parser.add_argument("--collab-review", action="store_true", help="Run collaborative document review (squad + Oracle synthesis)")
    parser.add_argument("--question", "-q", type=str, default="", help="Working question (with --collab-review)")
    parser.add_argument("--no-ingest", action="store_true", help="Skip scientist book ingest (with --collab-review)")
    parser.add_argument("--dry-run", action="store_true", help="Load review material only; no API calls")
    args = parser.parse_args()

    if args.support:
        print_platform_support_matrix()
        _lab_port = LAB_URL.rsplit(":", 1)[-1].rstrip("/")
        print(c("HOW TO RUN — EXACT COMMANDS PER PLATFORM (no compromises):", "c"))
        print(c(f"  Web (any): python run_lab.py --web   OR open {LAB_URL} after lab boot", "reset"))
        print(c("  Windows:   python run_lab.py   |   python run_lab.py --chat   |   python desktop_launcher.py", "reset"))
        print(c("  macOS:     python3 run_lab.py  |   ./boot_example.sh (or python3)   |   python3 desktop_launcher.py", "reset"))
        print(c("  Linux:     python3 run_lab.py  |   ./boot_example.sh   |   python3 desktop_launcher.py", "reset"))
        print(c(f"  Android/iOS: Browser to {LAB_URL} -> Add to Home (PWA)   OR load dashboard/frontend/mobile_chat_stub.html in WebView.", "reset"))
        print(c(f"  Docker (all hosts): docker compose up -d   ;   docker compose run --rm cli   ; web at :{_lab_port}", "reset"))
        print(c("  Full status: python run_lab.py --status ; services health + unified chat.", "m"))
        print(c("  Beef up brains: python3 run_lab.py --beef-up albert --file paper.md --title 'Background'", "m"))
        return
    if args.list_labs:
        script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "scripts", "create_lab.py")
        import subprocess
        subprocess.run([sys.executable, script, "--list-labs"], check=False)
        return
    if args.forge_lab:
        interactive_forge_lab()
        return
    if args.collab_review:
        from scripts.collaborative_review import run_collaborative_review
        if not _ensure_llm_ready():
            return
        files = []
        if args.file:
            files.append(args.file)
        try:
            run_collaborative_review(
                files=files or None,
                text=args.text or "",
                urls=[args.url] if args.url else None,
                question=args.question or "",
                title=args.title or "",
                ingest=not args.no_ingest,
                dry_run=args.dry_run,
            )
        except Exception as e:
            print(c(f"❌ Collaborative review failed: {e}", "r"))
            raise SystemExit(1) from e
        return
    if args.beef_up:
        run_beef_up(args)
        return
    if args.status:
        status = check_services()
        print(json.dumps(status, indent=2))
        # Human-readable ledger for Commander (ticket_ledger also in JSON)
        ledger = status.get("ticket_ledger") or {}
        if ledger.get("blocked_total") is not None:
            print(c(f"\n🎫 Blocked tickets: {ledger.get('blocked_total')}", "y"))
            for row in ledger.get("blocked_by_assignee") or []:
                print(c(f"   · {row.get('assignee')}: {row.get('n')}", "y"))
            linus_b = ledger.get("linus_blocked_implements") or []
            if linus_b:
                print(c(f"\n🔧 Linus blocked implements: {len(linus_b)}", "r"))
                for row in linus_b[:3]:
                    print(c(f"   · #{row.get('ticket_id')} {row.get('title')}: {(row.get('notes') or '')[:80]}", "r"))
            fails = ledger.get("recent_experiment_fails") or []
            if fails:
                print(c("\n💥 Recent experiment fails:", "r"))
                for f in fails[:3]:
                    print(c(
                        f"   · loop {f.get('loop_id')} {f.get('agent')}: {(f.get('stderr') or '')[:80]}",
                        "r",
                    ))
        return
    if args.web:
        open_dashboard()
        return
    if args.chat:
        run_chat_mode()
        return
    class_id = getattr(args, "class_id", "") or ""
    scope = getattr(args, "scope", "full") or "full"
    mark_job = getattr(args, "mark_job", "") or ""
    mark_submission = getattr(args, "mark_submission", "") or ""
    loop_kwargs = dict(
        class_id=class_id,
        scope=scope,
        mark_job=mark_job,
        mark_submission=mark_submission,
    )

    if mark_job and class_id and not args.problem:
        # Lecturer convenience: marking job alone starts the assist loop
        run_full_loop(None, **loop_kwargs)
        return
    if args.problem:
        run_full_loop(args.problem, **loop_kwargs)
        return
    if args.no_idea:
        problem = explore_flow() or no_idea_flow()
        if problem:
            run_full_loop(problem, **loop_kwargs)
        else:
            print(c("No problem selected.", "m"))
        return
    if args.category:
        # Quick direct category without full menu (great for scripts or repeat visitors)
        print(c(f"Quick Muse entry for category: {args.category}", "y"))
        try:
            res = requests.post(f"{ORACLE_URL}/generate_problem", json={"category": args.category}, timeout=30).json()
            p = res.get("problem_statement") or random.choice(CLI_NO_IDEA_CURATED.get(args.category, CLI_NO_IDEA_CURATED["surprise"]))
            run_full_loop(p, **loop_kwargs)
            return
        except Exception:
            p = random.choice(CLI_NO_IDEA_CURATED.get(args.category, CLI_NO_IDEA_CURATED["surprise"]))
            run_full_loop(p, **loop_kwargs)
            return
    # class-only: still enter console, but env is set for subsequent loops
    if class_id:
        os.environ["UNIVERSITY_CLASS_ID"] = class_id
        os.environ["UNIVERSITY_CLASS_SCOPE"] = scope
        if mark_job:
            os.environ["UNIVERSITY_MARK_JOB"] = mark_job
    run_commander_console()

if __name__ == "__main__":
    main()