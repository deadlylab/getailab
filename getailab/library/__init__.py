"""
getailab.library

The provenance, doccontrol, and persistent memory layer for GetAiLab.

Design (locked per user vision):
- Each lab has its own section (data/labs/<lab_id>/).
- Each scientist has their own book (data/labs/<lab_id>/scientists/<name>/book/) = their research knowledge base.
- Scientists get smarter via loop ingest into their book only (research knowledge, NO user data).
- User layer (Gabb y) is separate (data/users/<user>/).
- Oracle is the middleman/guardian (enforces, coordinates, prevents fuckups).
- Scale: user -> multiple labs (different configs), each lab has its scientists' books + codex.
- the example lab (quantum research division) is the fixed model. Get it working first, then generator uses it as blueprint.

Hand-picked/adapted from old getailab_library for clean scope.
No cosmo, no bloat, no user-memory in scientists.
"""
from .lab.lab import LabSection
from .scientist_book.book import ScientistBook
from .user.profile import UserProfile
from .service import (
    GetAiLabLibrary,
    add_scientist_reference,
    archive_collaborative_review,
    archive_completed_loop,
    get_library,
    get_scientist_book,
    get_scientist_references,
    reindex_library,
)
from .models import LibraryPage, LibraryBook

__all__ = [
    "LabSection",
    "ScientistBook",
    "UserProfile",
    "GetAiLabLibrary",
    "get_library",
    "get_scientist_book",
    "add_scientist_reference",
    "get_scientist_references",
    "archive_completed_loop",
    "archive_collaborative_review",
    "reindex_library",
    "LibraryPage",
    "LibraryBook",
]
