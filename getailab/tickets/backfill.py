"""
Backfill job tickets from archived vault loops (no LLM re-run required).

Creates completed tickets for loops already in data/labs/<lab_id>/manifest.json
so the dossier / dashboard audit trail reflects historical work.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

from getailab.tickets.loop_tracker import LoopTicketTracker
from getailab.tickets.tickets import TicketPriority, TicketStatus, TicketType


def backfill_loop_tickets_from_vault(
    lab_id: str = "chimera",
    *,
    skip_existing: bool = True,
) -> Dict[str, Any]:
    from getailab.library.service import GetAiLabLibrary

    lib = GetAiLabLibrary(lab_id=lab_id, backfill=False)
    manifest_path = lib.lab_path / "manifest.json"
    if not manifest_path.exists():
        return {"error": "no manifest.json", "lab_id": lab_id}

    manifest = json.loads(manifest_path.read_text())
    loop_ids = sorted(manifest.get("loops", []))
    tracker = LoopTicketTracker(lab_id=lab_id)
    created = 0
    skipped = 0
    loops_done: List[int] = []

    for loop_id in loop_ids:
        existing = tracker.get_loop_tickets(loop_id)
        if skip_existing and existing:
            skipped += 1
            continue

        pages = lib.get_loop_as_pages(loop_id)
        problem = ""
        synthesis = ""
        scientists: Set[str] = set()

        for page in pages:
            if page.page_type == "problem" and page.book_id == "codex":
                problem = page.content[:4000]
            elif page.page_type == "synthesis" and page.book_id == "codex":
                synthesis = page.content[:4000]
            elif page.agent and page.agent != "oracle":
                scientists.add(page.agent.lower())

        if not problem:
            problem = f"Archived research loop {loop_id}"

        tracker.open_loop(loop_id, problem)
        created += 1

        for scientist in sorted(scientists):
            hyp_pages = [p for p in pages if p.agent == scientist and p.page_type == "hypothesis"]
            if hyp_pages:
                tid = tracker.start_phase(
                    loop_id, scientist, "hypothesis",
                    hyp_pages[0].content[:800],
                )
                tracker.complete(tid, scientist, "Backfilled from vault")
                created += 1

            art_pages = [p for p in pages if p.agent == scientist and p.page_type == "artifact"]
            if art_pages:
                tid = tracker.start_phase(
                    loop_id, scientist, "implement",
                    f"{len(art_pages)} artifacts archived",
                )
                tracker.complete(tid, scientist, "Backfilled implement")
                created += 1
                tid = tracker.start_phase(
                    loop_id, scientist, "execute",
                    art_pages[0].title[:200],
                )
                tracker.complete(tid, scientist, "Backfilled execute")
                created += 1

        syn_tid = tracker.start_phase(
            loop_id, "oracle", "synthesize",
            synthesis[:800] if synthesis else "Synthesis archived",
        )
        tracker.complete(syn_tid, "oracle", "Backfilled synthesis")
        created += 1

        arch_tid = tracker.start_phase(loop_id, "oracle", "archive", "Library vault ingest")
        tracker.complete(arch_tid, "oracle", f"{len(pages)} pages in vault")
        created += 1

        tracker.close_loop(loop_id, f"Loop {loop_id} backfilled from vault")
        loops_done.append(loop_id)

    return {
        "lab_id": lab_id,
        "loops_processed": len(loops_done),
        "loops_skipped": skipped,
        "tickets_created": created,
        "loop_ids": loops_done,
        "db_path": tracker.db_path,
    }


if __name__ == "__main__":
    import sys
    lab = sys.argv[1] if len(sys.argv) > 1 else "chimera"
    print(json.dumps(backfill_loop_tickets_from_vault(lab), indent=2))