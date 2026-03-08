"""Knowledge layer — Links & Locks system for deterministic reasoning.

The brain of the system. Instead of forcing agents to re-infer facts they
already know, the knowledge layer provides:

- **Nodes**: Embedding-indexed knowledge points
- **Links**: Cross-domain shortcuts between related nodes
- **Locks**: Deterministic facts that bypass inference entirely
- **mLocks**: Multi-path locks — many routes to one absolute truth

Managers maintain this graph asynchronously.  The main agents just navigate.
"""

from autono.knowledge.types import (
    KnowledgeNode,
    Link,
    Lock,
    MLock,
    NodeStatus,
    VolatilityTier,
)
from autono.knowledge.graph import KnowledgeGraph
from autono.knowledge.store import KnowledgeStore

__all__ = [
    "KnowledgeNode",
    "Link",
    "Lock",
    "MLock",
    "NodeStatus",
    "VolatilityTier",
    "KnowledgeGraph",
    "KnowledgeStore",
]
