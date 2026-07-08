#!/usr/bin/env python3
"""
getailab.tickets — Job ticket lifecycle for research loops.

Adapted from CryptO'Brien autonomous-core (03_executive_workforce).
SQLite-backed: draft → assigned → in_progress → review → completed + escalation.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


def _default_db_path() -> str:
    env = os.getenv("JOB_TICKETS_DB", "").strip()
    if env:
        return env
    root = Path(__file__).resolve().parents[2]
    lab_id = os.getenv("LAB_ID", "chimera")
    path = root / "data" / "labs" / lab_id / "job_tickets.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)


class TicketPriority(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TicketStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    NEEDS_INFO = "needs_info"
    REJECTED = "rejected"
    APPROVED = "approved"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    ESCALATED = "escalated"
    REVIEW = "review"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EscalationType(str, Enum):
    API_KEY = "api_key"
    RESOURCE = "resource"
    BUDGET = "budget"
    LEGAL = "legal"
    TECHNICAL = "technical"
    EXTERNAL = "external"
    CLARIFICATION = "clarification"
    OTHER = "other"


class TicketType(str, Enum):
    TASK = "task"
    BUG = "bug"
    FEATURE = "feature"
    RESEARCH = "research"
    DOCUMENT = "document"
    MEETING = "meeting"
    REVIEW = "review"
    MAINTENANCE = "maintenance"


@dataclass
class JobTicket:
    title: str
    description: str
    assignee: str
    ticket_type: str = "task"
    priority: str = "medium"
    status: str = "draft"
    due_date: Optional[str] = None
    estimated_hours: Optional[float] = None
    tags: Optional[List[str]] = None
    created_by: str = "system"
    notes: Optional[str] = None


class JobTicketSystem:
    """SQLite-backed job ticket system with workflow history + escalation."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or _default_db_path()
        self._is_memory = self.db_path == ":memory:"
        self._memory_conn = None
        self._init_db()

    def _get_conn(self):
        if self._is_memory:
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(self.db_path, timeout=5)
                self._memory_conn.row_factory = sqlite3.Row
                self._memory_conn.execute("PRAGMA busy_timeout = 5000")
            return self._memory_conn
        conn = sqlite3.connect(self.db_path, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA busy_timeout = 5000")
        return conn

    def _init_db(self):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS tickets (
                    ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT,
                    assignee TEXT,
                    ticket_type TEXT DEFAULT 'task',
                    priority TEXT DEFAULT 'medium',
                    status TEXT DEFAULT 'draft',
                    due_date TEXT,
                    estimated_hours REAL,
                    tags TEXT,
                    created_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ticket_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER,
                    old_status TEXT,
                    new_status TEXT,
                    changed_by TEXT,
                    notes TEXT,
                    timestamp TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS escalations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket_id INTEGER,
                    escalation_type TEXT,
                    description TEXT,
                    escalated_by TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    resolved_at TEXT
                )
            """)
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

        try:
            c2 = self._get_conn()
            c2.execute("PRAGMA journal_mode=WAL")
            c2.execute("PRAGMA busy_timeout=8000")
            if not self._is_memory:
                c2.close()
        except Exception:
            pass

    def create_ticket(self, ticket: JobTicket) -> int:
        conn = self._get_conn()
        ticket_id = None
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO tickets (title, description, assignee, ticket_type, priority,
                                     status, due_date, estimated_hours, tags, created_by, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                ticket.title, ticket.description, ticket.assignee, ticket.ticket_type,
                ticket.priority, ticket.status, ticket.due_date, ticket.estimated_hours,
                json.dumps(ticket.tags or []), ticket.created_by, ticket.notes,
            ))
            ticket_id = cur.lastrowid
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()
        if ticket_id:
            self._log_history(ticket_id, None, ticket.status, ticket.created_by, "created")
        return int(ticket_id)

    def get_ticket(self, ticket_id: int) -> Optional[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
            row = cur.fetchone()
        finally:
            if not self._is_memory:
                conn.close()
        if row:
            d = dict(row)
            d["tags"] = json.loads(d.get("tags") or "[]")
            return d
        return None

    def list_tickets(
        self,
        *,
        assignee: Optional[str] = None,
        status: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            query = "SELECT * FROM tickets"
            clauses: List[str] = []
            params: List[Any] = []
            if assignee:
                clauses.append("assignee = ?")
                params.append(assignee)
            if status:
                clauses.append("status = ?")
                params.append(status)
            if tag:
                clauses.append("tags LIKE ?")
                params.append(f"%{tag}%")
            if clauses:
                query += " WHERE " + " AND ".join(clauses)
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = [dict(r) for r in conn.execute(query, params).fetchall()]
        finally:
            if not self._is_memory:
                conn.close()
        for r in rows:
            r["tags"] = json.loads(r.get("tags") or "[]")
        return rows

    def get_ticket_history(self, ticket_id: int) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            rows = conn.execute(
                "SELECT * FROM ticket_history WHERE ticket_id = ? ORDER BY timestamp ASC",
                (ticket_id,),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            if not self._is_memory:
                conn.close()

    def update_ticket_status(
        self,
        ticket_id: int,
        new_status: str,
        changed_by: str,
        notes: Optional[str] = None,
    ) -> bool:
        old = self.get_ticket(ticket_id)
        if not old:
            return False
        old_status = old["status"]
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE tickets SET status = ?, updated_at = CURRENT_TIMESTAMP, notes = COALESCE(?, notes)
                WHERE ticket_id = ?
            """, (new_status, notes, ticket_id))
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()
        self._log_history(ticket_id, old_status, new_status, changed_by, notes)
        return True

    def escalate_ticket(
        self, ticket_id: int, escalation_type: str, description: str, by: str
    ) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO escalations (ticket_id, escalation_type, description, escalated_by)
                VALUES (?, ?, ?, ?)
            """, (ticket_id, escalation_type, description, by))
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()
        self.update_ticket_status(
            ticket_id, TicketStatus.ESCALATED.value, by, f"Escalated: {escalation_type}"
        )
        return {"ticket_id": ticket_id, "escalation_type": escalation_type}

    def get_pending_tickets(self, assignee: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            if assignee:
                cur.execute("""
                    SELECT * FROM tickets
                    WHERE assignee = ? AND status IN ('approved','assigned')
                    ORDER BY
                        CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                        created_at
                """, (assignee,))
            else:
                cur.execute("""
                    SELECT * FROM tickets
                    WHERE status IN ('approved','assigned')
                    ORDER BY
                        CASE priority WHEN 'critical' THEN 0 WHEN 'high' THEN 1 WHEN 'medium' THEN 2 ELSE 3 END,
                        created_at
                """)
            rows = [dict(r) for r in cur.fetchall()]
        finally:
            if not self._is_memory:
                conn.close()
        for r in rows:
            r["tags"] = json.loads(r.get("tags") or "[]")
        return rows

    def get_daily_summary(self) -> Dict[str, Any]:
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            today = datetime.now().strftime("%Y-%m-%d")
            cur.execute("SELECT COUNT(*) FROM tickets WHERE date(created_at) = ?", (today,))
            created = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM tickets WHERE date(updated_at) = ? AND status = 'completed'",
                (today,),
            )
            completed = cur.fetchone()[0]
            cur.execute("SELECT status, COUNT(*) FROM tickets GROUP BY status")
            by_status = {r[0]: r[1] for r in cur.fetchall()}
            cur.execute("""
                SELECT priority, COUNT(*) FROM tickets
                WHERE status NOT IN ('completed','cancelled') GROUP BY priority
            """)
            by_pri = {r[0]: r[1] for r in cur.fetchall()}
        finally:
            if not self._is_memory:
                conn.close()
        return {
            "date": today,
            "created_today": created,
            "completed_today": completed,
            "pending_total": sum(by_status.values()) if by_status else 0,
            "by_status": by_status,
            "by_priority": by_pri,
            "db_path": self.db_path,
        }

    def _log_history(
        self, ticket_id: int, old: Optional[str], new: str, by: str, notes: Optional[str]
    ):
        conn = self._get_conn()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO ticket_history (ticket_id, old_status, new_status, changed_by, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (ticket_id, old, new, by, notes))
            conn.commit()
        finally:
            if not self._is_memory:
                conn.close()

    def print_ticket(self, ticket: Dict[str, Any]):
        print(f"\n{'═' * 60}")
        print(f"  TICKET #{ticket['ticket_id']}")
        print(f"{'═' * 60}")
        print(f"  Title:     {ticket['title']}")
        print(f"  Assignee:  {ticket.get('assignee')}")
        print(f"  Priority:  {ticket['priority']}   Status: {ticket['status']}")
        print(f"  Tags:      {', '.join(ticket.get('tags') or [])}")
        print(f"\n  {ticket['description']}")
        if ticket.get("notes"):
            print(f"\n  Notes: {ticket['notes']}")
        print(f"{'═' * 60}\n")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="GetAiLab Job Ticket System")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("create")
    p.add_argument("--title", "-t", required=True)
    p.add_argument("--desc", "-d", required=True)
    p.add_argument("--assignee", "-a", required=True)
    p.add_argument("--type", default="research")
    p.add_argument("--priority", "-p", default="medium")
    p.add_argument("--tag", action="append", default=[])

    p = sub.add_parser("list")
    p.add_argument("--assignee", "-a")
    p.add_argument("--status", "-s")
    p.add_argument("--tag")
    p.add_argument("--all", action="store_true")

    p = sub.add_parser("view")
    p.add_argument("ticket_id", type=int)

    p = sub.add_parser("summary")

    p = sub.add_parser("loop")
    p.add_argument("loop_id", type=int)

    p = sub.add_parser("backfill")
    p.add_argument("--lab", default="chimera")

    args = parser.parse_args()
    sys = JobTicketSystem()

    if args.command == "create":
        t = JobTicket(
            title=args.title,
            description=args.desc,
            assignee=args.assignee,
            ticket_type=args.type,
            priority=args.priority,
            status=TicketStatus.ASSIGNED.value,
            tags=args.tag,
            created_by="cli",
        )
        tid = sys.create_ticket(t)
        print(f"Created ticket #{tid}")
        row = sys.get_ticket(tid)
        if row:
            sys.print_ticket(row)
    elif args.command == "list":
        if args.all:
            rows = sys.list_tickets(limit=500)
        else:
            rows = sys.list_tickets(
                assignee=args.assignee, status=args.status, tag=args.tag, limit=200
            )
        for t in rows:
            print(
                f"{t['ticket_id']:>4} | {t['priority']:8} | {t['status']:12} | "
                f"{t.get('assignee', ''):12} | {t['title'][:40]}"
            )
    elif args.command == "view":
        row = sys.get_ticket(args.ticket_id)
        if row:
            sys.print_ticket(row)
    elif args.command == "summary":
        print(json.dumps(sys.get_daily_summary(), indent=2))
    elif args.command == "loop":
        from getailab.tickets.loop_tracker import LoopTicketTracker
        tracker = LoopTicketTracker()
        print(json.dumps(tracker.get_loop_summary(args.loop_id), indent=2))
    elif args.command == "backfill":
        from getailab.tickets.backfill import backfill_loop_tickets_from_vault
        print(json.dumps(backfill_loop_tickets_from_vault(args.lab), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()