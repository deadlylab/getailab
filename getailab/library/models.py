"""Library data models — pages, books, provenance."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class LibraryPage:
    page_id: str
    loop_id: Optional[int]
    page_type: str
    title: str
    content: str
    content_checksum: str
    agent: str = "oracle"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    book_id: str = "codex"

    def to_dict(self, include_content: bool = True) -> Dict[str, Any]:
        d = {
            "page_id": self.page_id,
            "loop_id": self.loop_id,
            "page_type": self.page_type,
            "title": self.title,
            "content_checksum": self.content_checksum,
            "agent": self.agent,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "book_id": self.book_id,
        }
        if include_content:
            d["content"] = self.content
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LibraryPage":
        return cls(
            page_id=data["page_id"],
            loop_id=data.get("loop_id"),
            page_type=data.get("page_type", "general"),
            title=data.get("title", ""),
            content=data.get("content", ""),
            content_checksum=data.get("content_checksum", ""),
            agent=data.get("agent", "oracle"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            book_id=data.get("book_id", "codex"),
        )


@dataclass
class LibraryBook:
    book_id: str
    title: str
    slug: str
    page_ids: List[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)