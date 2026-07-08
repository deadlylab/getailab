"""
Loop Ticket Tracker — one JobTicket per phase contribution in a research loop.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from getailab.tickets.tickets import (
    JobTicket,
    JobTicketSystem,
    TicketPriority,
    TicketStatus,
    TicketType,
    _default_db_path,
)

_TRACKER: Optional["LoopTicketTracker"] = None


class LoopTicketTracker:
    """Creates and updates tickets for Chimera dialectic loop phases."""

    def __init__(self, lab_id: Optional[str] = None, db_path: Optional[str] = None):
        self.lab_id = lab_id or os.getenv("LAB_ID", "chimera")
        self.db_path = db_path or _default_db_path()
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.system = JobTicketSystem(db_path=self.db_path)
        self._parent_ticket_id: Optional[int] = None
        self._current_loop_id: Optional[int] = None

    def _tags(self, loop_id: int, phase: str, **extra: str) -> List[str]:
        tags = [f"loop:{loop_id}", f"lab:{self.lab_id}", f"phase:{phase}"]
        for key, val in extra.items():
            if val:
                tags.append(f"{key}:{val}")
        return tags

    def open_loop(self, loop_id: int, problem: str) -> int:
        """Parent ticket for the full dialectic loop."""
        self._current_loop_id = loop_id
        self._parent_ticket_id = self.system.create_ticket(JobTicket(
            title=f"Loop {loop_id} — Research dialectic",
            description=(problem or "")[:4000],
            assignee="oracle",
            ticket_type=TicketType.RESEARCH.value,
            priority=TicketPriority.HIGH.value,
            status=TicketStatus.IN_PROGRESS.value,
            tags=self._tags(loop_id, "loop", role="parent"),
            created_by="run_chimera",
        ))
        return self._parent_ticket_id

    def start_phase(
        self,
        loop_id: int,
        assignee: str,
        phase: str,
        description: str = "",
        *,
        priority: str = TicketPriority.MEDIUM.value,
    ) -> int:
        """Open a phase ticket and mark it in_progress."""
        ticket_id = self.system.create_ticket(JobTicket(
            title=f"Loop {loop_id} — {assignee} — {phase}",
            description=(description or "")[:4000],
            assignee=assignee,
            ticket_type=TicketType.RESEARCH.value,
            priority=priority,
            status=TicketStatus.ASSIGNED.value,
            tags=self._tags(loop_id, phase, scientist=assignee),
            created_by="run_chimera",
        ))
        self.system.update_ticket_status(
            ticket_id, TicketStatus.IN_PROGRESS.value, assignee, f"Started {phase}"
        )
        return ticket_id

    def complete(self, ticket_id: int, changed_by: str, notes: str = "") -> bool:
        return self.system.update_ticket_status(
            ticket_id, TicketStatus.COMPLETED.value, changed_by, notes[:2000]
        )

    def fail(self, ticket_id: int, changed_by: str, notes: str = "") -> bool:
        return self.system.update_ticket_status(
            ticket_id, TicketStatus.BLOCKED.value, changed_by, notes[:2000]
        )

    def close_loop(self, loop_id: int, notes: str = "") -> bool:
        if not self._parent_ticket_id or self._current_loop_id != loop_id:
            parent = self.system.list_tickets(tag=f"loop:{loop_id}", limit=50)
            parents = [
                t for t in parent
                if "phase:loop" in t.get("tags", []) and t.get("status") != TicketStatus.COMPLETED.value
            ]
            if not parents:
                return False
            ticket_id = parents[0]["ticket_id"]
        else:
            ticket_id = self._parent_ticket_id
        return self.complete(ticket_id, "oracle", notes)

    def get_loop_tickets(self, loop_id: int) -> List[Dict[str, Any]]:
        return self.system.list_tickets(tag=f"loop:{loop_id}", limit=500)

    def get_loop_summary(self, loop_id: int) -> Dict[str, Any]:
        tickets = self.get_loop_tickets(loop_id)
        by_phase: Dict[str, int] = {}
        by_status: Dict[str, int] = {}
        by_assignee: Dict[str, int] = {}
        for t in tickets:
            by_status[t["status"]] = by_status.get(t["status"], 0) + 1
            by_assignee[t.get("assignee") or "unknown"] = by_assignee.get(t.get("assignee") or "unknown", 0) + 1
            for tag in t.get("tags", []):
                if tag.startswith("phase:"):
                    phase = tag.split(":", 1)[1]
                    by_phase[phase] = by_phase.get(phase, 0) + 1
        return {
            "loop_id": loop_id,
            "lab_id": self.lab_id,
            "ticket_count": len(tickets),
            "by_phase": by_phase,
            "by_status": by_status,
            "by_assignee": by_assignee,
            "tickets": tickets,
            "db_path": self.db_path,
        }


def get_loop_ticket_tracker(lab_id: Optional[str] = None) -> LoopTicketTracker:
    global _TRACKER
    lid = lab_id or os.getenv("LAB_ID", "chimera")
    if _TRACKER is None or _TRACKER.lab_id != lid:
        _TRACKER = LoopTicketTracker(lab_id=lid)
    return _TRACKER