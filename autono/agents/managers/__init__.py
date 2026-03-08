"""Manager agents — the operating system of the knowledge layer.

Managers run asynchronously, maintaining the Links & Locks network.
The main chain agents never have to think about database administration.

THE MANAGERS:
1. ThrottleManager  — Watches SYSTEM resources, controls agent spawning
2. EmbedManager     — Validates embeddings, scores volatility, daily pulse
3. ExpansionManager — Prunes stale data, watches for .md file updates
4. ResearchManager  — Scrapes new data, creates .md files for embedding
5. LinkManager      — Stitches cross-domain shortcuts (the Doctor)
6. LockManager      — Seals deterministic facts, manages mLocks (the Healer)
"""

from autono.agents.managers.throttle_manager import ThrottleManager
from autono.agents.managers.embed_manager import EmbedManager
from autono.agents.managers.expansion_manager import ExpansionManager
from autono.agents.managers.research_manager import ResearchManager
from autono.agents.managers.link_manager import LinkManager
from autono.agents.managers.lock_manager import LockManager

ALL_MANAGERS = [
    ThrottleManager,
    EmbedManager,
    ExpansionManager,
    ResearchManager,
    LinkManager,
    LockManager,
]

__all__ = [
    "ThrottleManager", "EmbedManager", "ExpansionManager",
    "ResearchManager", "LinkManager", "LockManager",
    "ALL_MANAGERS",
]
