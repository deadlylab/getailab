#!/usr/bin/env python3
"""
GetAiLab Persona Builder — friendly scientist setup with online research.

Researches historical figures (Wikipedia → optional Playwright/Sauron), synthesizes
rich squad YAML fields + system prompts via the configured LLM, then forges the lab.

Usage:
    python3 scripts/persona_builder.py
    python3 scripts/persona_builder.py --scientist "Edmond Halley" --role meteorologist \\
        --agenda "Atmospheric circulation and forecasting" --preview-only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LLM_TIMEOUT = int(os.getenv("PERSONA_BUILDER_LLM_TIMEOUT", "120"))

try:
    import requests
    import yaml
except ImportError as exc:
    print(f"Missing dependency: {exc}. Run: pip install requests PyYAML")
    sys.exit(1)

USER_AGENT = "GetAiLab-PersonaBuilder/1.0 (research; mailto:research@getailab.dev)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
MAX_CONTEXT_CHARS = 14_000


# ── slug helpers ─────────────────────────────────────────────────────────────

def slugify(name: str) -> str:
    s = re.sub(r"[^a-z0-9_]+", "_", (name or "").lower().strip())
    s = re.sub(r"_+", "_", s).strip("_")
    return s[:40] or "scientist"


def is_sane_slug(slug: str) -> bool:
    if not slug or len(slug) > 40:
        return False
    if slug.count("_") > 4:
        return False
    return bool(re.match(r"^[a-z][a-z0-9_]*$", slug))


def suggest_slug(display_name: str) -> str:
    parts = re.sub(r"[^a-zA-Z\s]", " ", display_name).split()
    if not parts:
        return "scientist"
    if len(parts) == 1:
        return slugify(parts[0])
    return slugify(parts[-1])


# ── web research ─────────────────────────────────────────────────────────────

@dataclass
class ResearchBundle:
    query: str
    sources: List[Dict[str, str]] = field(default_factory=list)
    text: str = ""
    sauron_json: Optional[dict] = None

    def add(self, label: str, url: str, body: str) -> None:
        body = (body or "").strip()
        if not body:
            return
        self.sources.append({"label": label, "url": url})
        block = f"\n\n## {label}\nSource: {url}\n\n{body[:MAX_CONTEXT_CHARS]}"
        if len(self.text) + len(block) > MAX_CONTEXT_CHARS * 2:
            return
        self.text += block


def _wiki_get(params: dict) -> dict:
    resp = requests.get(
        WIKI_API,
        params={**params, "format": "json"},
        headers={"User-Agent": USER_AGENT},
        timeout=25,
    )
    resp.raise_for_status()
    return resp.json()


def search_wikipedia(name: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (page_title, plain-text extract) for best Wikipedia match."""
    data = _wiki_get({
        "action": "query",
        "list": "search",
        "srsearch": name,
        "srlimit": 5,
    })
    hits = data.get("query", {}).get("search", [])
    if not hits:
        return None, None

    title = hits[0]["title"]
    extract_data = _wiki_get({
        "action": "query",
        "prop": "extracts",
        "explaintext": True,
        "titles": title,
        "exchars": 12000,
    })
    pages = extract_data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()), {})
    extract = (page.get("extract") or "").strip()
    return title, extract or None


def fetch_url_text(url: str, max_chars: int = 8000) -> str:
    try:
        from getailab.library.ingest.reference_ingester import fetch_url_as_text
        return fetch_url_as_text(url, max_chars=max_chars)
    except Exception:
        resp = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=30)
        resp.raise_for_status()
        return resp.text[:max_chars]


async def playwright_capture(url: str) -> Tuple[Optional[str], Optional[bytes]]:
    try:
        from sauron_vision import CaptureEngine
        _, markdown, screenshot = await CaptureEngine().capture_url(url)
        return markdown, screenshot
    except Exception as exc:
        print(f"  ⚠ Playwright capture failed: {exc}")
        return None, None


def sauron_extract(query: str, text: str, image_bytes: Optional[bytes] = None) -> Optional[dict]:
    try:
        from llm.adapter import create_default_adapter
        from llm.sauron_core import extract_with_adapter
        adapter = create_default_adapter()
        return extract_with_adapter(
            adapter,
            query,
            image_bytes=image_bytes,
            text_context=text[:12000] if text else None,
        )
    except Exception as exc:
        print(f"  ⚠ Sauron extraction failed: {exc}")
        return None


def literature_snippets(name: str, role: str, agenda: str) -> str:
    try:
        from getailab.literature_search import search_literature, format_literature_block
        q = f"{name} {role} {agenda}"
        results = search_literature(q, max_per_source=2)
        return format_literature_block(results) if results else ""
    except Exception:
        return ""


def gather_research(
    scientist_name: str,
    role: str,
    agenda: str,
    *,
    use_playwright: bool = False,
    use_sauron: bool = False,
    use_literature: bool = False,
) -> ResearchBundle:
    bundle = ResearchBundle(query=scientist_name)
    print(f"  🔍 Researching: {scientist_name}")

    title, wiki_text = search_wikipedia(scientist_name)
    if wiki_text:
        url = f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
        bundle.add("Wikipedia", url, wiki_text)
        print(f"     ✓ Wikipedia — {title} ({len(wiki_text):,} chars)")
    else:
        print("     · Wikipedia — no match")

    if use_literature:
        lit = literature_snippets(scientist_name, role, agenda)
        if lit:
            bundle.add("Literature search", "getailab/literature_search", lit)
            print("     ✓ Literature — PubMed/arXiv/Semantic Scholar snippets")

    wiki_url = bundle.sources[0]["url"] if bundle.sources else None
    markdown = None
    screenshot = None
    if use_playwright and wiki_url:
        print("     … Playwright deep capture")
        markdown, screenshot = asyncio.run(playwright_capture(wiki_url))
        if markdown:
            bundle.add("Playwright page capture", wiki_url, markdown)
            print(f"     ✓ Playwright — {len(markdown):,} chars")

    if use_sauron and bundle.text:
        print("     … Sauron structured extraction")
        query = (
            f"Extract biographical and scientific credentials for {scientist_name} "
            f"as a {role} working on: {agenda}. Focus on testable methods, data sources, "
            f"key publications, and domain innovations."
        )
        bundle.sauron_json = sauron_extract(query, bundle.text, screenshot)
        if bundle.sauron_json:
            summary = bundle.sauron_json.get("summary", "")
            if summary:
                bundle.add("Sauron extraction", wiki_url or "sauron", summary)
            print(f"     ✓ Sauron — {bundle.sauron_json.get('topic', 'extracted')}")

    return bundle


# ── LLM persona synthesis ────────────────────────────────────────────────────

PERSONA_JSON_SCHEMA = """
Return ONLY valid JSON (no markdown fences):
{
  "slug": "short_snake_case_id e.g. halley",
  "full_name": "Display name with dates if historical",
  "display_role": "Role — specialty tagline for the lab UI",
  "role": "short_role_slug",
  "expertise": ["3-8 bullet strings"],
  "implement_focus": "one line: what Python artifacts they produce",
  "persona_summary": "2-4 sentences for DOMAIN FOCUS",
  "system_prompt": "Full multi-paragraph system prompt (see rules below)"
}
"""


def _parse_llm_json(text: str) -> Optional[dict]:
    if not text:
        return None
    raw = text.strip()
    raw = re.sub(r"^```(?:json)?\s*", "", raw)
    raw = re.sub(r"\s*```$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def _persona_synthesis_prompt(
    scientist_name: str,
    role: str,
    agenda: str,
    research: ResearchBundle,
    profile: str,
    lab_display_name: str,
) -> str:
    sauron_block = ""
    if research.sauron_json:
        sauron_block = f"\nSAURON STRUCTURED DATA:\n{json.dumps(research.sauron_json, indent=2)[:4000]}\n"

    debate_heat = "moderate dialectic" if profile == "research" else "concise collaboration"
    return f"""You are the GetAiLab Persona Architect. Build a production scientist persona for a multi-agent research lab.

LAB: {lab_display_name}
RESEARCH AGENDA: {agenda}
SCIENTIST: {scientist_name}
ROLE IN THIS LAB: {role}
BUILD PROFILE: {profile} ({debate_heat})

RESEARCH CONTEXT (ground truth — do not invent facts not supported here):
{research.text[:MAX_CONTEXT_CHARS] or "(No web research — use general knowledge cautiously and mark uncertainty.)"}
{sauron_block}

RULES FOR system_prompt:
1. Open with "You are <Name> — <Role>." using their historical or custom identity.
2. Include LAB RESEARCH AGENDA and DOMAIN FOCUS sections (agenda + persona_summary content).
3. Describe voice, temperament, and how they argue in council (name colleagues, demand artifacts).
4. Include **How you operate in GetAiLab loops** with Phase 1 (hypothesis) and Phase 2 (Python → .csv/.json/.png).
5. Include 3-4 **Example interactions** in their voice.
6. Close with standard GetAiLab lines: dialectic lab, prior research book may be injected.
7. Slug must be SHORT (e.g. halley, fitzroy, tesla) — NEVER a full sentence.
8. expertise must be a list of distinct skill strings, not one giant paragraph.
9. implement_focus: concrete Python deliverables for this lab agenda.
10. Target 400-900 words for system_prompt. No YAML fences inside JSON strings — use \\n for newlines.

{PERSONA_JSON_SCHEMA}"""


def synthesize_persona(
    scientist_name: str,
    role: str,
    agenda: str,
    research: ResearchBundle,
    *,
    profile: str = "research",
    lab_display_name: str = "Research Lab",
    custom_notes: str = "",
) -> dict:
    try:
        from llm.adapter import create_default_adapter
        adapter = create_default_adapter()
        info = adapter.get_info()
        print(f"  🧠 Synthesizing persona via {info.get('configured_provider', 'LLM')}...")
        prompt = _persona_synthesis_prompt(
            scientist_name, role, agenda, research, profile, lab_display_name
        )
        if custom_notes:
            prompt += f"\nUSER NOTES:\n{custom_notes}\n"
        response = adapter.generate(prompt, timeout=LLM_TIMEOUT)
        data = _parse_llm_json(response)
        if data:
            return _normalize_persona(data, scientist_name, role, agenda, profile)
    except Exception as exc:
        print(f"  ⚠ LLM synthesis failed: {exc}")

    print("  ↩ Using template fallback (no LLM or parse error)")
    return _template_persona(scientist_name, role, agenda, research, profile)


def _normalize_persona(
    data: dict,
    scientist_name: str,
    role: str,
    agenda: str,
    profile: str,
) -> dict:
    slug = slugify(data.get("slug") or suggest_slug(scientist_name))
    if not is_sane_slug(slug):
        slug = suggest_slug(scientist_name)

    expertise = data.get("expertise") or []
    if isinstance(expertise, str):
        expertise = [e.strip() for e in re.split(r"[;\n]+", expertise) if e.strip()]

    persona_summary = (data.get("persona_summary") or "").strip()
    system_prompt = (data.get("system_prompt") or "").strip()
    if not system_prompt:
        system_prompt = _template_system_prompt(
            data.get("full_name") or scientist_name,
            data.get("display_role") or role,
            agenda,
            persona_summary or role,
            profile,
        )

    implement_focus = (data.get("implement_focus") or persona_summary or role)[:200]

    return {
        "slug": slug,
        "full_name": data.get("full_name") or scientist_name,
        "display_role": data.get("display_role") or role,
        "role": slugify(data.get("role") or role)[:40] or "researcher",
        "expertise": expertise[:8] or [persona_summary[:120] or role],
        "implement_focus": implement_focus,
        "persona": persona_summary or implement_focus,
        "system_prompt": system_prompt,
    }


def _template_system_prompt(name: str, display_role: str, agenda: str, focus: str, profile: str) -> str:
    return (
        f"You are {name} — {display_role}.\n\n"
        f"LAB RESEARCH AGENDA:\n{agenda}\n\n"
        f"DOMAIN FOCUS:\n{focus}\n\n"
        "You are part of a multi-agent dialectic research lab (GetAiLab).\n"
        "Phase 1: Formulate a high-rigor, testable hypothesis for the problem.\n"
        "Phase 2: Write executable Python that produces auditable artifacts on disk "
        "(.csv, .json, .png).\n"
        "Call out weak reasoning. Prefer simulations, data analysis, and measurable outputs.\n"
        "Address colleagues by name. Demand provenance for data and reproducible charts.\n"
        "Your prior research book may be injected — build on it, do not blindly repeat."
    )


def _template_persona(
    scientist_name: str,
    role: str,
    agenda: str,
    research: ResearchBundle,
    profile: str,
) -> dict:
    slug = suggest_slug(scientist_name)
    wiki_body = ""
    for src in research.sources:
        if src.get("label") == "Wikipedia":
            wiki_body = research.text.split("## Wikipedia", 1)[-1][:2500]
            break
    summary = ""
    if wiki_body:
        lines = [ln.strip() for ln in wiki_body.splitlines() if ln.strip() and not ln.startswith("Source:")]
        summary = " ".join(lines[:6])[:500]
    elif research.text:
        summary = research.text.split("\n\n")[0][:400]
    if not summary:
        summary = f"{scientist_name} — specialist in {role} for this lab's agenda."

    expertise: List[str] = []
    if wiki_body:
        for sentence in re.split(r"(?<=[.!?])\s+", summary):
            s = sentence.strip()
            if len(s) > 30 and len(expertise) < 6:
                expertise.append(s[:160])
    if not expertise:
        expertise = [summary[:200]]

    display_role = f"{role} — {scientist_name}"
    return {
        "slug": slug,
        "full_name": scientist_name,
        "display_role": display_role,
        "role": slugify(role)[:40] or "researcher",
        "expertise": expertise,
        "implement_focus": f"{role}: simulations, synoptic charts, and auditable data artifacts",
        "persona": summary,
        "system_prompt": _template_system_prompt(scientist_name, display_role, agenda, summary, profile),
    }


# ── interactive UX ───────────────────────────────────────────────────────────

def _prompt(msg: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"{msg}{suffix}: ").strip()
    return val or default


def _yes_no(msg: str, default_yes: bool = True) -> bool:
    default = "Y" if default_yes else "n"
    val = input(f"{msg} [{default}/{'n' if default_yes else 'Y'}]: ").strip().lower()
    if not val:
        return default_yes
    return val in ("y", "yes", "1", "true")


def _preview_persona(p: dict) -> None:
    print("\n  ┌─ Persona preview ─────────────────────────────────────")
    print(f"  │ slug:          {p['slug']}")
    print(f"  │ full_name:     {p.get('full_name', '')}")
    print(f"  │ display_role:  {p.get('display_role', '')}")
    print(f"  │ expertise:     {len(p.get('expertise') or [])} items")
    print(f"  │ implement:     {(p.get('implement_focus') or '')[:70]}")
    sp = p.get("system_prompt") or ""
    words = len(sp.split())
    print(f"  │ system_prompt: {words} words")
    print("  └────────────────────────────────────────────────────────")
    if _yes_no("  Show full system prompt?", default_yes=False):
        print("─" * 60)
        print(sp)
        print("─" * 60)


def build_one_scientist(
    index: int,
    total: int,
    agenda: str,
    profile: str,
    lab_display_name: str,
) -> Tuple[str, dict]:
    print(f"\n{'═' * 60}")
    print(f"  SCIENTIST {index + 1} of {total}")
    print(f"{'═' * 60}")

    mode = _prompt("  Mode: [1] Historical (auto-research)  [2] Custom agent", "1")
    historical = mode != "2"

    if historical:
        scientist_name = _prompt("  Historical figure name", "Edmond Halley")
    else:
        scientist_name = _prompt("  Agent display name", f"Scientist {index + 1}")

    role = _prompt("  Role in this lab", "Research Scientist")
    custom_notes = _prompt("  Extra notes (optional)", "")

    use_research = _yes_no("  Research online (Wikipedia)?", default_yes=historical)
    use_playwright = False
    use_sauron = False
    use_literature = False
    if use_research and _yes_no("  Add literature search (PubMed/arXiv — slower)?", default_yes=False):
        use_literature = True
    if use_research and _yes_no("  Deep scrape with Playwright (needs chromium)?", default_yes=False):
        use_playwright = True
    if use_research and _yes_no("  Run Sauron structured extraction (extra LLM pass)?", default_yes=False):
        use_sauron = True

    research = ResearchBundle(query=scientist_name)
    if use_research:
        research = gather_research(
            scientist_name,
            role,
            agenda,
            use_playwright=use_playwright,
            use_sauron=use_sauron,
            use_literature=use_literature,
        )
    elif custom_notes:
        research.add("User notes", "local", custom_notes)

    persona = synthesize_persona(
        scientist_name,
        role,
        agenda,
        research,
        profile=profile,
        lab_display_name=lab_display_name,
        custom_notes=custom_notes,
    )

    while True:
        _preview_persona(persona)
        action = _prompt("  [A]ccept  [E]dit  [R]egenerate  [N]ame/slug only", "A").lower()
        if action in ("a", "accept", ""):
            break
        if action in ("r", "regenerate"):
            persona = synthesize_persona(
                scientist_name, role, agenda, research,
                profile=profile, lab_display_name=lab_display_name, custom_notes=custom_notes,
            )
            continue
        if action in ("n", "name"):
            persona["slug"] = slugify(_prompt("  slug (short id)", persona["slug"]))
            persona["full_name"] = _prompt("  full_name", persona.get("full_name", scientist_name))
            continue
        if action in ("e", "edit"):
            persona["display_role"] = _prompt("  display_role", persona.get("display_role", role))
            persona["persona"] = _prompt("  persona summary", persona.get("persona", ""))
            persona["implement_focus"] = _prompt("  implement_focus", persona.get("implement_focus", ""))
            if _yes_no("  Replace system_prompt manually?", default_yes=False):
                print("  Paste system prompt; end with a lone line: END")
                lines = []
                while True:
                    line = input()
                    if line.strip() == "END":
                        break
                    lines.append(line)
                persona["system_prompt"] = "\n".join(lines)
            continue

    squad_entry = {
        "role": persona["display_role"],
        "persona": persona["persona"],
        "full_name": persona.get("full_name"),
        "display_role": persona.get("display_role"),
        "expertise": persona.get("expertise"),
        "implement_focus": persona.get("implement_focus"),
        "system_prompt": persona.get("system_prompt"),
        "_role_slug": persona.get("role"),
    }
    return persona["slug"], squad_entry


def interactive_forge_wizard() -> None:
    scripts_dir = Path(__file__).resolve().parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    from create_lab import _slug, forge_lab

    print()
    print("  ╔══════════════════════════════════════════════════════════════════╗")
    print("  ║   GetAiLab · Persona Builder                                     ║")
    print("  ║   Research · synthesize · forge complete labs                    ║")
    print("  ╚══════════════════════════════════════════════════════════════════╝")
    print()

    raw_id = _prompt("Lab ID (e.g. weather_lab, environmental)", "weather_lab")
    lab_id = _slug(raw_id)
    if lab_id == "chimera":
        print("  ⚠ 'chimera' is reserved — using custom_lab")
        lab_id = "custom_lab"

    display_name = _prompt("Display name", lab_id.replace("_", " ").title())
    agenda = _prompt(
        "Core research agenda",
        "Atmospheric and environmental data analysis with testable forecasting",
    )

    print("\n  Build profile:")
    print("    1. research  — full vault, books, rich prompts")
    print("    2. canvas    — thin personas, fast setup")
    prof = _prompt("Profile [1/2]", "1")
    profile = "canvas" if prof in ("2", "canvas") else "research"

    while True:
        try:
            num = int(_prompt("How many scientists", "3"))
            if 1 <= num <= 10:
                break
            print("  Enter 1–10.")
        except ValueError:
            print("  Invalid number.")

    squad: Dict[str, Dict[str, Any]] = {}
    for i in range(num):
        slug, entry = build_one_scientist(i, num, agenda, profile, display_name)
        if slug in squad:
            slug = f"{slug}_{i + 1}"
        squad[slug] = entry

    print("\n" + "═" * 60)
    print(f"  Lab:     {lab_id}")
    print(f"  Name:    {display_name}")
    print(f"  Agenda:  {agenda}")
    print(f"  Squad:   {', '.join(squad)}")
    print("═" * 60)

    if not _yes_no("Forge this lab now?", default_yes=True):
        out = ROOT / "data" / "persona_drafts" / f"{lab_id}_squad_preview.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps({"lab_id": lab_id, "display_name": display_name, "agenda": agenda, "squad": squad}, indent=2))
        print(f"  Draft saved: {out}")
        return

    input("\nPress ENTER to forge...")
    forge_lab(lab_id, display_name, agenda, squad, profile)


def build_scientist_cli(
    scientist_name: str,
    role: str,
    agenda: str,
    *,
    profile: str = "research",
    lab_display_name: str = "Research Lab",
    use_playwright: bool = False,
    use_sauron: bool = False,
    use_literature: bool = False,
    preview_only: bool = False,
) -> dict:
    research = gather_research(
        scientist_name, role, agenda,
        use_playwright=use_playwright,
        use_sauron=use_sauron,
        use_literature=use_literature,
    )
    persona = synthesize_persona(
        scientist_name, role, agenda, research,
        profile=profile, lab_display_name=lab_display_name,
    )
    if preview_only:
        print(json.dumps(persona, indent=2))
    return persona


def main() -> None:
    parser = argparse.ArgumentParser(description="GetAiLab Persona Builder")
    parser.add_argument("--scientist", help="Build a single scientist (non-interactive)")
    parser.add_argument("--role", default="Research Scientist")
    parser.add_argument("--agenda", default="General systems research")
    parser.add_argument("--profile", choices=("research", "canvas"), default="research")
    parser.add_argument("--playwright", action="store_true", help="Use Playwright deep capture")
    parser.add_argument("--sauron", action="store_true", help="Run Sauron extraction (extra LLM pass)")
    parser.add_argument("--literature", action="store_true", help="Search PubMed/arXiv/Semantic Scholar")
    parser.add_argument("--fast", action="store_true", help="Wikipedia only; skip optional slow steps")
    parser.add_argument("--preview-only", action="store_true")
    args = parser.parse_args()

    if args.scientist:
        fast = args.fast or not (args.playwright or args.sauron or args.literature)
        build_scientist_cli(
            args.scientist,
            args.role,
            args.agenda,
            profile=args.profile,
            use_playwright=args.playwright and not fast,
            use_sauron=args.sauron and not fast,
            use_literature=args.literature and not fast,
            preview_only=True,
        )
        return

    interactive_forge_wizard()


if __name__ == "__main__":
    main()