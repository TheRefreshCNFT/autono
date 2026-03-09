"""Core types for the Links & Locks knowledge system.

Architecture:
- KnowledgeNode: A point of knowledge with embedding coordinates
- Link: A stitched shortcut between two nodes (the cut pulled together)
- Lock: A sealed, deterministic fact (the wound fully healed)
- mLock: Multi-lock — many paths converge to one absolute truth

Volatility determines how often the EmbedManager re-validates a node.
Low volatility = math, protocol rules. High volatility = API endpoints, politics.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VolatilityTier(str, Enum):
    """How often a fact needs re-validation by the EmbedManager."""
    PERMANENT = "permanent"     # 1+1=2, never changes. score ~0.01
    STABLE = "stable"           # Protocol rules, CIP standards. score ~0.1
    MODERATE = "moderate"       # Library versions, API patterns. score ~0.5
    VOLATILE = "volatile"       # Prices, endpoints, current events. score ~0.9
    REALTIME = "realtime"       # Live data, must check every query. score ~1.0


# Validation intervals per tier (seconds)
VOLATILITY_INTERVALS: dict[VolatilityTier, int] = {
    VolatilityTier.PERMANENT: 0,            # never re-validate
    VolatilityTier.STABLE: 604_800,         # weekly
    VolatilityTier.MODERATE: 86_400,        # daily
    VolatilityTier.VOLATILE: 3_600,         # hourly
    VolatilityTier.REALTIME: 0,             # every access
}


class NodeStatus(str, Enum):
    """State of a knowledge node."""
    ACTIVE = "active"           # live and valid
    STALE = "stale"             # needs re-validation
    PRUNED = "pruned"           # marked for removal
    SHATTERED = "shattered"     # lock broken by new data


class LinkRelationship(str, Enum):
    """How two nodes relate across domains."""
    REQUIRES = "requires"               # A needs B to function
    COMMONLY_PAIRED = "commonly_paired"  # seen together often
    ALTERNATIVE = "alternative"         # B is another way to achieve A's goal
    DERIVES_FROM = "derives_from"       # B is the source/origin of A
    CONTRADICTS = "contradicts"         # B invalidates A (triggers shatter)
    RESULTS_IN = "results_in"           # A produces B as output


@dataclass
class Link:
    """A stitched connection between two knowledge nodes.

    The doctor pulling the cut together — not yet healed, but the gap
    is bridged. If the link proves reliable over time, it can be sealed
    into a Lock by the LockManager.
    """
    id: str = field(default_factory=lambda: f"link_{uuid.uuid4().hex[:12]}")
    source_node_id: str = ""
    target_node_id: str = ""
    relationship: LinkRelationship = LinkRelationship.COMMONLY_PAIRED
    shortcut_weight: float = 0.5            # 0.0 = weak, 1.0 = absolute
    compute_cost: str = "LOW"               # LOW, MEDIUM, HIGH
    success_rate: float = 1.0               # how often this path works
    use_count: int = 0                      # times traversed
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_used: str = ""
    description: str = ""

    def record_use(self, success: bool = True) -> None:
        """Track usage for the LinkManager to evaluate promotion to Lock."""
        self.use_count += 1
        self.last_used = datetime.now(timezone.utc).isoformat()
        if success:
            # success rate trends toward 1.0 with consistent success
            self.success_rate = (self.success_rate * 0.9) + (0.1 if success else 0.0)
        else:
            self.success_rate = self.success_rate * 0.8

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for backup."""
        return {
            "id": self.id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relationship": self.relationship.value,
            "shortcut_weight": self.shortcut_weight,
            "compute_cost": self.compute_cost,
            "success_rate": self.success_rate,
            "use_count": self.use_count,
            "created_at": self.created_at,
            "last_used": self.last_used,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Link:
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            source_node_id=data.get("source_node_id", ""),
            target_node_id=data.get("target_node_id", ""),
            relationship=LinkRelationship(data.get("relationship", "commonly_paired")),
            shortcut_weight=data.get("shortcut_weight", 0.5),
            compute_cost=data.get("compute_cost", "LOW"),
            success_rate=data.get("success_rate", 1.0),
            use_count=data.get("use_count", 0),
            created_at=data.get("created_at", ""),
            last_used=data.get("last_used", ""),
            description=data.get("description", ""),
        )


@dataclass
class Lock:
    """A sealed, deterministic fact. The wound fully healed.

    When an agent hits a Lock, inference is BYPASSED entirely.
    The agent returns the locked payload immediately.
    Zero GPU. 100% accuracy.

    Locks are shattered by the LockManager when underlying data changes
    (detected via dependency_hash mismatch or EmbedManager STATE_CHANGE events).
    """
    id: str = field(default_factory=lambda: f"lock_{uuid.uuid4().hex[:12]}")
    node_id: str = ""                       # the node this lock seals
    status: NodeStatus = NodeStatus.ACTIVE
    absolute_answer: Any = None             # the deterministic payload
    answer_type: str = "string"             # string, integer, json, address, etc.
    verification_source: str = ""           # CIP-25, BIP-44, math, etc.
    dependency_hash: str = ""               # hash of source data for staleness check
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_validated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    shattered_at: str = ""
    shattered_reason: str = ""

    def compute_dependency_hash(self, *source_data: str) -> str:
        """Hash the source material this lock depends on."""
        combined = "|".join(str(s) for s in source_data)
        self.dependency_hash = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return self.dependency_hash

    def validate_hash(self, *current_data: str) -> bool:
        """Check if source data has changed since lock was created."""
        current_hash = hashlib.sha256(
            "|".join(str(s) for s in current_data).encode()
        ).hexdigest()[:16]
        return current_hash == self.dependency_hash

    def shatter(self, reason: str) -> None:
        """Break the seal. Forces inference on next access."""
        self.status = NodeStatus.SHATTERED
        self.shattered_at = datetime.now(timezone.utc).isoformat()
        self.shattered_reason = reason

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for backup."""
        return {
            "id": self.id,
            "node_id": self.node_id,
            "status": self.status.value,
            "absolute_answer": self.absolute_answer,
            "answer_type": self.answer_type,
            "verification_source": self.verification_source,
            "dependency_hash": self.dependency_hash,
            "created_at": self.created_at,
            "last_validated": self.last_validated,
            "shattered_at": self.shattered_at,
            "shattered_reason": self.shattered_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Lock:
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            node_id=data.get("node_id", ""),
            status=NodeStatus(data.get("status", "active")),
            absolute_answer=data.get("absolute_answer"),
            answer_type=data.get("answer_type", "string"),
            verification_source=data.get("verification_source", ""),
            dependency_hash=data.get("dependency_hash", ""),
            created_at=data.get("created_at", ""),
            last_validated=data.get("last_validated", ""),
            shattered_at=data.get("shattered_at", ""),
            shattered_reason=data.get("shattered_reason", ""),
        )


@dataclass
class MLock:
    """Multi-Lock — many paths converge to one absolute truth.

    1+1=2 → Lock. Then 3-1=2 → same answer. Upgrade to mLock.
    4/2=2 → another path. Append to incoming_links.

    Works both ways:
    - Forward: "I have 1+1, what does it equal?" → 2
    - Backward: "I need 2, what are my options?" → [1+1, 3-1, 4/2]
    """
    id: str = field(default_factory=lambda: f"mlock_{uuid.uuid4().hex[:12]}")
    status: NodeStatus = NodeStatus.ACTIVE
    payload: Any = None                     # the absolute value
    payload_type: str = "string"
    description: str = ""
    verification_source: str = ""

    # Volatility for the EmbedManager
    volatility: VolatilityTier = VolatilityTier.PERMANENT
    last_validated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # All paths that lead to this answer (backward chaining)
    incoming_links: list[IncomingPath] = field(default_factory=list)

    # Hash of all dependencies for staleness detection
    dependency_hash: str = ""

    def add_path(self, source_embed_id: str, method: str,
                 compute_cost: str = "LOW") -> None:
        """Register a new way to reach this mLock's payload."""
        path = IncomingPath(
            source_embed_id=source_embed_id,
            method=method,
            compute_cost=compute_cost,
        )
        # Don't duplicate
        for existing in self.incoming_links:
            if existing.source_embed_id == source_embed_id:
                return
        self.incoming_links.append(path)

    def best_path(self) -> IncomingPath | None:
        """Return the cheapest, most reliable path (backward chaining)."""
        if not self.incoming_links:
            return None
        cost_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        return min(
            self.incoming_links,
            key=lambda p: (cost_order.get(p.compute_cost, 3), -p.success_rate)
        )

    def shatter(self, reason: str) -> None:
        """Break all locks. Underlying truth changed."""
        self.status = NodeStatus.SHATTERED

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for backup."""
        return {
            "id": self.id,
            "status": self.status.value,
            "payload": self.payload,
            "payload_type": self.payload_type,
            "description": self.description,
            "verification_source": self.verification_source,
            "volatility": self.volatility.value,
            "last_validated": self.last_validated,
            "incoming_links": [p.to_dict() for p in self.incoming_links],
            "dependency_hash": self.dependency_hash,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MLock:
        """Deserialize from dictionary."""
        mlock = cls(
            id=data.get("id", ""),
            status=NodeStatus(data.get("status", "active")),
            payload=data.get("payload"),
            payload_type=data.get("payload_type", "string"),
            description=data.get("description", ""),
            verification_source=data.get("verification_source", ""),
            volatility=VolatilityTier(data.get("volatility", "permanent")),
            last_validated=data.get("last_validated", ""),
            dependency_hash=data.get("dependency_hash", ""),
        )
        for path_data in data.get("incoming_links", []):
            mlock.incoming_links.append(IncomingPath.from_dict(path_data))
        return mlock


@dataclass
class IncomingPath:
    """One path that leads to an mLock's payload."""
    source_embed_id: str = ""
    method: str = ""                    # addition, subtraction, derivation, etc.
    compute_cost: str = "LOW"
    success_rate: float = 1.0
    use_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for backup."""
        return {
            "source_embed_id": self.source_embed_id,
            "method": self.method,
            "compute_cost": self.compute_cost,
            "success_rate": self.success_rate,
            "use_count": self.use_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> IncomingPath:
        """Deserialize from dictionary."""
        return cls(
            source_embed_id=data.get("source_embed_id", ""),
            method=data.get("method", ""),
            compute_cost=data.get("compute_cost", "LOW"),
            success_rate=data.get("success_rate", 1.0),
            use_count=data.get("use_count", 0),
        )


@dataclass
class KnowledgeNode:
    """A single point of knowledge in the graph.

    This is the fundamental unit. It holds content, an embedding vector
    (or hash reference to one), metadata for the managers, and references
    to its links/locks.
    """
    id: str = field(default_factory=lambda: f"node_{uuid.uuid4().hex[:12]}")
    content: str = ""                       # the actual knowledge text
    domain: str = ""                        # cardano, bitcoin, charms, math, etc.
    subdomain: str = ""                     # protocol, wallet, bridge, etc.
    status: NodeStatus = NodeStatus.ACTIVE

    # Embedding reference (vector stored externally or inline)
    embedding_hash: str = ""                # hash reference to vector store
    embedding_model: str = ""               # which model generated it

    # Manager metadata
    volatility: VolatilityTier = VolatilityTier.STABLE
    last_validated: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_file: str = ""                   # .md file that generated this node
    source_hash: str = ""                   # hash of source for change detection

    # Graph connections
    link_ids: list[str] = field(default_factory=list)
    lock_id: str = ""                       # if locked, the Lock/mLock id
    is_locked: bool = False
    is_mlocked: bool = False

    # Agent access metadata
    bypass_llm: bool = False                # if true, skip inference entirely
    priority_score: int = 50                # 0-100, higher = more important

    # Tags for search
    tags: list[str] = field(default_factory=list)

    def compute_source_hash(self, source_content: str) -> str:
        """Hash the source material for change detection."""
        self.source_hash = hashlib.sha256(source_content.encode()).hexdigest()[:16]
        return self.source_hash

    def mark_stale(self) -> None:
        """Flag for re-validation by EmbedManager."""
        self.status = NodeStatus.STALE

    def prune(self) -> None:
        """Mark for removal by ExpansionManager."""
        self.status = NodeStatus.PRUNED

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary for backup."""
        return {
            "id": self.id,
            "content": self.content,
            "domain": self.domain,
            "subdomain": self.subdomain,
            "status": self.status.value,
            "embedding_hash": self.embedding_hash,
            "embedding_model": self.embedding_model,
            "volatility": self.volatility.value,
            "last_validated": self.last_validated,
            "created_at": self.created_at,
            "source_file": self.source_file,
            "source_hash": self.source_hash,
            "link_ids": self.link_ids,
            "lock_id": self.lock_id,
            "is_locked": self.is_locked,
            "is_mlocked": self.is_mlocked,
            "bypass_llm": self.bypass_llm,
            "priority_score": self.priority_score,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> KnowledgeNode:
        """Deserialize from dictionary."""
        return cls(
            id=data.get("id", ""),
            content=data.get("content", ""),
            domain=data.get("domain", ""),
            subdomain=data.get("subdomain", ""),
            status=NodeStatus(data.get("status", "active")),
            embedding_hash=data.get("embedding_hash", ""),
            embedding_model=data.get("embedding_model", ""),
            volatility=VolatilityTier(data.get("volatility", "stable")),
            last_validated=data.get("last_validated", ""),
            created_at=data.get("created_at", ""),
            source_file=data.get("source_file", ""),
            source_hash=data.get("source_hash", ""),
            link_ids=data.get("link_ids", []),
            lock_id=data.get("lock_id", ""),
            is_locked=data.get("is_locked", False),
            is_mlocked=data.get("is_mlocked", False),
            bypass_llm=data.get("bypass_llm", False),
            priority_score=data.get("priority_score", 50),
            tags=data.get("tags", []),
        )
