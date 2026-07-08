#!/usr/bin/env python3
"""
Regenerate loop report markdown from SQLite + lab artifacts, then rebuild loops.tar.gz.

Reconstructs missing reports (13, 14, 16) from:
  - chimera_lab.db (agora_loops: problem, date, synthesis)
  - lab/lab_results.db (lab_experiments: code, stdout, stderr, artifacts)
  - Existing reports / codex synthesis pages / sibling loop hypotheses

Usage:
    python3 scripts/regenerate_loop_reports.py
    python3 scripts/regenerate_loop_reports.py --loops 13 14 16
    python3 scripts/regenerate_loop_reports.py --no-tar
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import tarfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = ROOT / "docs" / "loops"
_ACTIVE_LAB = "example"


def _lab_paths(lab_id: str):
    import sys
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from getailab.lab_config import agora_db_path, lab_artifacts_dir, lab_results_db_path

    lid = lab_id or "example"
    return (
        agora_db_path(lid),
        lab_results_db_path(lid),
        lab_artifacts_dir(lid),
        ROOT / "data" / "labs" / lid / "codex" / "book" / "pages",
    )

SCIENTIST_ORDER = [
    "albert", "bohr", "heisenberg", "alan", "brian", "carl", "neil", "roger", "emmy", "andrew",
]


def _connect_chimera():
    agora_db, _, _, _ = _lab_paths(_ACTIVE_LAB)
    return sqlite3.connect(agora_db)


def _connect_lab():
    _, lab_db, _, _ = _lab_paths(_ACTIVE_LAB)
    return sqlite3.connect(lab_db)


def _loop_meta(loop_id: int) -> Tuple[str, str, str]:
    conn = _connect_chimera()
    row = conn.execute(
        "SELECT problem_statement, start_time, consensus_artefact FROM agora_loops WHERE loop_id = ?",
        (loop_id,),
    ).fetchone()
    conn.close()
    if not row:
        return "", "", ""
    problem, start_time, synthesis = row
    return (problem or "").strip(), (start_time or "").strip(), (synthesis or "").strip()


def _codex_synthesis(loop_id: int) -> str:
    _, _, _, codex_pages = _lab_paths(_ACTIVE_LAB)
    path = codex_pages / f"synthesis-{loop_id}.json"
    if not path.is_file():
        return ""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return (data.get("content") or "").strip()
    except Exception:
        return ""


def _experiments(loop_id: int) -> Dict[str, dict]:
    conn = _connect_lab()
    rows = conn.execute(
        """
        SELECT agent_name, experiment_name, code, stdout, stderr, success, artifacts_json
        FROM lab_experiments WHERE loop_id = ? ORDER BY id ASC
        """,
        (str(loop_id),),
    ).fetchall()
    conn.close()
    out: Dict[str, dict] = {}
    for agent, exp_name, code, stdout, stderr, success, artifacts_json in rows:
        agent = (agent or "").lower()
        artifacts: List[str] = []
        try:
            artifacts = json.loads(artifacts_json or "[]") or []
        except Exception:
            pass
        out[agent] = {
            "experiment_name": exp_name or "",
            "code": code or "",
            "stdout": stdout or "",
            "stderr": stderr or "",
            "success": bool(success),
            "artifacts": artifacts,
        }
    return out


def _parse_report_sections(report_md: str) -> Dict[str, Dict[str, str]]:
    sections: Dict[str, Dict[str, str]] = {}
    if not report_md:
        return sections
    for match in re.finditer(r"^##\s+(.+?)\s*$", report_md, re.M):
        heading = match.group(1).strip()
        start = match.end()
        nxt = re.search(r"^##\s+", report_md[start:], re.M)
        body = (report_md[start: start + nxt.start()] if nxt else report_md[start:]).strip()
        if "'s Hypothesis" in heading:
            name = heading.split("'s")[0].strip().lower()
            sections.setdefault(name, {})["hypothesis"] = body
        elif heading == "Oracle's Consensus Artefact":
            sections["_oracle"] = {"synthesis": body}
    return sections


def _load_existing_report(loop_id: int) -> str:
    for path in (ROOT / f"loop_{loop_id}_report.md", REPORTS_DIR / f"loop_{loop_id}_report.md"):
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace")
    return ""


def _hypothesis_from_book(loop_id: int, scientist: str) -> str:
    path = ROOT / "data" / "labs" / "example" / "scientists" / scientist / "book" / "pages" / f"hypothesis-{loop_id}-{scientist}.json"
    if not path.is_file():
        return ""
    try:
        return (json.loads(path.read_text(encoding="utf-8")).get("content") or "").strip()
    except Exception:
        return ""


def _hypothesis_from_sibling(loop_id: int, scientist: str) -> str:
    """Loop 14 shares problem statement with loop 15 — borrow hypotheses from 15's report."""
    if loop_id != 14:
        return ""
    report = _load_existing_report(15)
    return _parse_report_sections(report).get(scientist, {}).get("hypothesis", "")


def _hypothesis_from_code(code: str) -> str:
    if not code or code.startswith("ERROR:") or len(code) < 80:
        return ""
    lines = code.splitlines()
    i = 0
    # Optional module docstring at file top
    if i < len(lines) and lines[i].strip().startswith('"""'):
        buf = []
        for line in lines:
            buf.append(line)
            if line.strip().endswith('"""') and len(buf) > 1:
                break
        doc = "\n".join(buf).strip().strip('"""').strip()
        if len(doc) > 120:
            return doc
    # Collect # commentary lines until first def/class (skip imports)
    comment_lines: List[str] = []
    for line in lines:
        s = line.strip()
        if s.startswith(("import ", "from ")):
            continue
        if s.startswith(("def ", "class ")):
            break
        if s.startswith("#"):
            text = s.lstrip("#").strip()
            if text and not text.startswith("---") and "Copyright" not in text:
                comment_lines.append(text)
    body = "\n".join(comment_lines).strip()
    return body if len(body) > 80 else ""


def _resolve_hypothesis(
    loop_id: int,
    scientist: str,
    experiments: Dict[str, dict],
    *,
    allow_existing_report: bool = True,
) -> str:
    if allow_existing_report:
        existing = _parse_report_sections(_load_existing_report(loop_id))
        if existing.get(scientist, {}).get("hypothesis"):
            hyp = existing[scientist]["hypothesis"]
            if not hyp.startswith("*Hypothesis text was not archived"):
                return hyp
    book = _hypothesis_from_book(loop_id, scientist)
    if book:
        return book
    sibling = _hypothesis_from_sibling(loop_id, scientist)
    if sibling:
        return sibling
    exp = experiments.get(scientist, {})
    from_code = _hypothesis_from_code(exp.get("code", ""))
    if from_code:
        return from_code
    return (
        f"*Hypothesis text was not archived for Loop {loop_id}. "
        f"Experiment code and lab results below are reconstructed from `lab_results.db` and `lab/artifacts/{loop_id}/`.*"
    )


def _format_experiment(scientist: str, exp: dict) -> str:
    name = scientist.capitalize()
    code = exp.get("code", "").strip()
    stdout = exp.get("stdout", "").strip()
    stderr = exp.get("stderr", "").strip()
    artifacts = exp.get("artifacts") or []
    exp_name = exp.get("experiment_name") or "unnamed_experiment"
    status = "✅ success" if exp.get("success") else "❌ failed"

    parts = [f"## {name}'s Experiment", f"**Experiment:** {exp_name}", f"**Status:** {status}", ""]
    if code:
        parts.append("```python")
        parts.append(code)
        parts.append("```")
    parts.append("### Lab Results")
    parts.append(f"**Artifacts:** {', '.join(artifacts) if artifacts else 'None'}")
    if stdout:
        parts.append("**STDOUT:**")
        parts.append("```text")
        parts.append(stdout)
        parts.append("```")
    if stderr:
        parts.append("**STDERR:**")
        parts.append("```text")
        parts.append(stderr)
        parts.append("```")
    parts.append("")
    return "\n".join(parts)


def build_report(loop_id: int, *, reconstructed: bool = False) -> str:
    problem, start_time, db_synthesis = _loop_meta(loop_id)
    synthesis = db_synthesis or _codex_synthesis(loop_id)
    experiments = _experiments(loop_id)

    if not problem and not experiments:
        raise ValueError(f"No data for loop {loop_id}")

    date_str = start_time.replace("T", " ")[:19] if start_time else "unknown"
    lines = [f"# GetAiLab Loop {loop_id}"]
    if reconstructed:
        lines.append(f"**Reconstructed:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} (from DB + artifacts)")
    lines.append(f"**Date:** {date_str}")
    lines.append(f"**Problem:** {problem or '(see codex problem page)'}")
    lines.append("")

    for scientist in SCIENTIST_ORDER:
        hyp = _resolve_hypothesis(
            loop_id, scientist, experiments, allow_existing_report=not reconstructed
        )
        lines.append(f"## {scientist.capitalize()}'s Hypothesis")
        lines.append(hyp)
        lines.append("")

    for scientist in SCIENTIST_ORDER:
        if scientist in experiments:
            lines.append(_format_experiment(scientist, experiments[scientist]))

    lines.append("## Oracle's Consensus Artefact")
    if synthesis:
        lines.append(synthesis)
    else:
        lines.append(
            f"*No Oracle synthesis was stored for Loop {loop_id} in `agora_loops` or codex. "
            "See prior loop syntheses (e.g. Loop 12) for the research arc that led to this problem.*"
        )
    lines.append("")
    lines.append("---")
    lines.append("*Copyright (c) 2026 CryptO'Brien Pty Ltd. All Rights Reserved.*")
    if reconstructed:
        lines.append(f"*Report regenerated by scripts/regenerate_loop_reports.py*")
    lines.append("")
    return "\n".join(lines)


def write_report(loop_id: int, content: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORTS_DIR / f"loop_{loop_id}_report.md"
    path.write_text(content, encoding="utf-8")
    root_copy = ROOT / f"loop_{loop_id}_report.md"
    if root_copy.exists() or loop_id >= 17:
        root_copy.write_text(content, encoding="utf-8")
    return path


def rebuild_tar(loop_ids: List[int], tar_path: Path) -> int:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    added = 0
    with tarfile.open(tar_path, "w:gz") as tar:
        for loop_id in sorted(loop_ids):
            report = REPORTS_DIR / f"loop_{loop_id}_report.md"
            if not report.is_file():
                continue
            arcname = f"loops/loop_{loop_id}_report.md"
            tar.add(report, arcname=arcname)
            added += 1
    return added


def main():
    parser = argparse.ArgumentParser(description="Regenerate the example lab loop reports and loops.tar.gz")
    parser.add_argument("--lab-id", default="example", help="Lab ID (default: example)")
    parser.add_argument("--loops", type=int, nargs="*", help="Only regenerate these loop IDs")
    parser.add_argument("--no-tar", action="store_true", help="Skip rebuilding loops.tar.gz")
    parser.add_argument(
        "--tar-loops",
        type=int,
        nargs="*",
        help="Loop IDs to include in tar (default: all reports in docs/loops)",
    )
    args = parser.parse_args()

    global _ACTIVE_LAB
    _ACTIVE_LAB = args.lab_id

    missing = args.loops or [13, 14, 16]
    existing_reports = sorted(
        int(p.stem.split("_")[1])
        for p in REPORTS_DIR.glob("loop_*_report.md")
        if p.stem.split("_")[1].isdigit()
    )

    print(f"🔧 Regenerating reports for loops: {missing}")
    for loop_id in missing:
        try:
            content = build_report(loop_id, reconstructed=True)
            path = write_report(loop_id, content)
            print(f"  ✅ loop_{loop_id}_report.md → {path} ({len(content):,} chars)")
        except Exception as exc:
            print(f"  ❌ loop {loop_id}: {exc}")

    if not args.no_tar:
        tar_loops = args.tar_loops
        if not tar_loops:
            tar_loops = sorted(set(existing_reports + missing))
            tar_loops = [n for n in tar_loops if (REPORTS_DIR / f"loop_{n}_report.md").is_file()]
        tar_path = REPORTS_DIR / "loops.tar.gz"
        count = rebuild_tar(tar_loops, tar_path)
        print(f"\n📦 {tar_path} — {count} reports packed")
        print("   Contents:")
        with tarfile.open(tar_path, "r:gz") as tar:
            for m in sorted(tar.getnames()):
                print(f"     {m}")

    print("\nDone.")


if __name__ == "__main__":
    main()