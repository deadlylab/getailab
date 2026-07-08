"""
getailab

Clean GetAiLab research lab (getailab_live build).

Key separation (per design):
- Gabby: User talks here. User profile, engagement, personal context. (getailab/gabby/)
- Oracle Guardian: Internal middleman/guardian. Coordinates, enforces, protects environments. (getailab/oracle/)
- Scientists: Research agents only. They have NO concept of the user. Their memory is per-scientist books (research knowledge only).
- Library: Per-lab sections, per-scientist persistent books (the knowledge base that makes scientists smarter), codex, doccontrol/tickets provenance.

Chimera (quantum research division) is the fixed model in this directory.
Get it working as a clean lab.
Then generator uses it as blueprint for new labs (each with own user/labs structure).

All in one directory for the build. No mixing.
"""
from .gabby.gabby import Gabby
from .oracle.guardian import OracleGuardian
from .library.lab.lab import LabSection
from .library.scientist_book.book import ScientistBook
from .tickets import JobTicket, JobTicketSystem, LoopTicketTracker, get_loop_ticket_tracker
from .learning import AdaptiveLearnerService, get_adaptive_learner

__all__ = [
    "Gabby",
    "OracleGuardian",
    "LabSection",
    "ScientistBook",
    "JobTicket",
    "JobTicketSystem",
    "LoopTicketTracker",
    "get_loop_ticket_tracker",
    "AdaptiveLearnerService",
    "get_adaptive_learner",
]
