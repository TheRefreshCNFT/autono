"""EmbedManager — the brain's pulse. Validates embeddings continuously.

Like a living brain, this manager never stops processing. It validates
existing embeddings against reality based on their volatility scores.

- PERMANENT nodes (1+1=2): checked never or annually
- STABLE nodes (CIP-25 = NFT metadata key 721): checked weekly
- MODERATE nodes (library versions): checked daily
- VOLATILE nodes (US President, API endpoints): checked hourly
- REALTIME nodes: checked every access

When the EmbedManager finds a discrepancy, it broadcasts a STATE_CHANGE
event. The LockManager hears this and shatters affected locks.
No ghost data. Active pruning. Living system.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message
from autono.knowledge.types import (
    KnowledgeNode,
    NodeStatus,
    VolatilityTier,
    VOLATILITY_INTERVALS,
)


class EmbedManager(AutonomousAgent):
    """Embedding validator and volatility manager.

    The immune system of the knowledge graph. Continuously checks
    if what the system "knows" is still true.

    As the system grows, EmbedManager can request ThrottleManager
    to spawn sub-agents for parallel validation work.
    """

    def __init__(self) -> None:
        super().__init__(
            name="EmbedManager",
            role="Embedding validator — scores volatility, validates knowledge currency",
            capabilities=[AgentCapability.RESEARCH, AgentCapability.AUDIT],
        )
        self._store = None  # Set during orchestrator init
        self._graph = None  # For embedding generation
        self._validation_queue: list[str] = []
        self._validated_count: int = 0
        self._stale_found: int = 0
        self._embedded_count: int = 0
        self._batch_size: int = 50  # nodes per validation cycle

    @property
    def work_interval(self) -> float:
        return 60.0  # check every minute

    def set_store(self, store: Any) -> None:
        """Inject the knowledge store (called by orchestrator)."""
        self._store = store

    def set_graph(self, graph: Any) -> None:
        """Inject the knowledge graph for embedding operations."""
        self._graph = graph

    async def do_work(self) -> None:
        """Run validation cycle and embed any unembedded nodes."""
        if not self._store:
            return

        # Phase 0: Embed any nodes missing embeddings
        if self._graph:
            try:
                newly_embedded = self._graph.embed_all_nodes()
            except ImportError:
                newly_embedded = 0  # sentence_transformers not installed; skip silently
            if newly_embedded > 0:
                self._embedded_count += newly_embedded
                self.log.info("embed.batch_complete", count=newly_embedded,
                              total=self._embedded_count)

        now = datetime.now(timezone.utc)
        nodes_checked = 0

        # Get all active nodes from the index
        for node_id, meta in list(self._store._index.get("nodes", {}).items()):
            if nodes_checked >= self._batch_size:
                break

            status = meta.get("status", "active")
            if status in ("pruned", "shattered"):
                continue

            volatility = meta.get("volatility", "stable")

            # Check if this node is due for validation
            if not self._is_due_for_validation(node_id, volatility):
                continue

            # Load and validate
            node = self._store.load_node(node_id)
            if not node:
                continue

            stale = await self._validate_node(node)
            nodes_checked += 1
            self._validated_count += 1

            if stale:
                self._stale_found += 1
                node.mark_stale()
                self._store.save_node(node)

                # Broadcast STATE_CHANGE — LockManager and LinkManager listen
                await self.broadcast("alert", {
                    "type": "state_change",
                    "node_id": node_id,
                    "domain": node.domain,
                    "reason": "validation_failed",
                    "previous_hash": node.source_hash,
                }, priority=2)

                self.log.warning("embed.stale_detected",
                                 node_id=node_id, domain=node.domain)

        if nodes_checked > 0:
            self.memory.remember("decisions", {
                "type": "validation_cycle",
                "nodes_checked": nodes_checked,
                "stale_found": self._stale_found,
                "total_validated": self._validated_count,
            })

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request" and msg.payload.get("type") == "validate_node":
            node_id = msg.payload.get("node_id")
            if node_id and self._store:
                node = self._store.load_node(node_id)
                if node:
                    stale = await self._validate_node(node)
                    await self.send(msg.sender, "response", {
                        "type": "validation_result",
                        "node_id": node_id,
                        "is_stale": stale,
                    })

        elif msg.kind == "request" and msg.payload.get("type") == "embed_node":
            # Request to embed a specific node immediately
            node_id = msg.payload.get("node_id")
            if node_id and self._graph:
                embedding_hash = self._graph.embed_node(node_id)
                self._embedded_count += 1
                await self.send(msg.sender, "response", {
                    "type": "embed_result",
                    "node_id": node_id,
                    "embedding_hash": embedding_hash,
                })

        elif msg.kind == "request" and msg.payload.get("type") == "score_volatility":
            # Other managers can ask EmbedManager to score a new node
            domain = msg.payload.get("domain", "")
            subdomain = msg.payload.get("subdomain", "")
            score = self._score_volatility(domain, subdomain)
            await self.send(msg.sender, "response", {
                "type": "volatility_score",
                "domain": domain,
                "tier": score.value,
            })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "embedding_validation",
            "topics": [
                "semantic_drift_detection",
                "adaptive_volatility_scoring",
                "embedding_model_upgrades",
            ],
        })

    # -- Validation logic -------------------------------------------------

    def _is_due_for_validation(self, node_id: str, volatility: str) -> bool:
        """Check if a node needs re-validation based on its volatility tier."""
        try:
            tier = VolatilityTier(volatility)
        except ValueError:
            tier = VolatilityTier.STABLE

        interval = VOLATILITY_INTERVALS.get(tier, 86_400)
        if interval == 0 and tier == VolatilityTier.PERMANENT:
            return False  # never validate permanent facts

        # Load node to check last_validated timestamp
        node = self._store.load_node(node_id)
        if not node:
            return False

        try:
            last = datetime.fromisoformat(node.last_validated)
            elapsed = (datetime.now(timezone.utc) - last).total_seconds()
            return elapsed >= interval
        except (ValueError, TypeError):
            return True  # if we can't parse, validate it

    async def _validate_node(self, node: KnowledgeNode) -> bool:
        """Validate a node's source data hasn't changed.

        Returns True if the node is STALE (source changed).

        For now, validates by checking if the source .md file hash
        matches the stored hash. Future: scrape and compare live data.
        """
        if not node.source_file or not node.source_hash:
            # No source to validate against — mark as validated
            node.last_validated = datetime.now(timezone.utc).isoformat()
            return False

        # Check if the source file still exists and matches
        if self._store:
            content = self._store.load_research(node.source_file)
            if content is None:
                # Source file gone — the site went away
                # Backtrack: mark stale, don't delete yet (LinkManager handles)
                return True

            current_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
            if current_hash != node.source_hash:
                return True

        # Still valid
        node.last_validated = datetime.now(timezone.utc).isoformat()
        return False

    def _score_volatility(self, domain: str, subdomain: str) -> VolatilityTier:
        """Score the volatility of a knowledge domain.

        This is the intelligence: knowing how fast things change.
        """
        # Domain-based scoring
        volatility_map = {
            # Permanent — math, physics, logic
            ("math", ""): VolatilityTier.PERMANENT,

            # Stable — blockchain protocols, CIP standards, BIP standards
            ("cardano", "protocol"): VolatilityTier.STABLE,
            ("cardano", "cip"): VolatilityTier.STABLE,
            ("bitcoin", "protocol"): VolatilityTier.STABLE,
            ("bitcoin", "bip"): VolatilityTier.STABLE,
            ("charms", "spell_format"): VolatilityTier.STABLE,

            # Moderate — library versions, SDK methods, documentation
            ("cardano", "sdk"): VolatilityTier.MODERATE,
            ("bitcoin", "sdk"): VolatilityTier.MODERATE,
            ("charms", "api"): VolatilityTier.MODERATE,
            ("bitcoinos", "api"): VolatilityTier.MODERATE,

            # Volatile — prices, network state, current events
            ("cardano", "price"): VolatilityTier.VOLATILE,
            ("bitcoin", "price"): VolatilityTier.VOLATILE,
            ("cardano", "network_state"): VolatilityTier.VOLATILE,
            ("bitcoin", "fees"): VolatilityTier.VOLATILE,

            # Realtime — live data feeds
            ("market", "orderbook"): VolatilityTier.REALTIME,
        }

        # Try exact match first
        key = (domain, subdomain)
        if key in volatility_map:
            return volatility_map[key]

        # Try domain-only match
        key = (domain, "")
        if key in volatility_map:
            return volatility_map[key]

        # Default
        return VolatilityTier.MODERATE

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "validated_count": self._validated_count,
            "stale_found": self._stale_found,
            "embedded_count": self._embedded_count,
            "batch_size": self._batch_size,
        })
        return base
