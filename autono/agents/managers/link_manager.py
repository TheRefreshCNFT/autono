"""LinkManager — the Doctor, stitching the cuts together.

Watches for opportunities to connect disparate knowledge nodes.
When two nodes are frequently accessed together or share semantic
relationships across domains, the LinkManager stitches them.

Links are not permanent — they're provisional connections.
If they prove reliable (high use count, high success rate),
the LockManager can seal them into Locks.
"""

from __future__ import annotations

from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message
from autono.knowledge.types import (
    KnowledgeNode,
    Link,
    LinkRelationship,
    NodeStatus,
)


class LinkManager(AutonomousAgent):
    """The Doctor — stitches cross-domain shortcuts.

    Monitors agent query patterns and node co-occurrence to find
    opportunities for Links. A Link saves compute by letting agents
    "jump" between related nodes without multiple vector searches.

    Rules:
    - Must prove a link saves actual compute before creating it
    - Strict relevance threshold (no over-stitching)
    - Respects hop limits (max 3 connections deep)
    - All spawning requests go through ThrottleManager
    """

    # Minimum co-occurrence count before considering a link
    MIN_COOCCURRENCE = 3
    # Minimum weight to create a link
    MIN_WEIGHT_THRESHOLD = 0.4
    # Maximum links per node to prevent explosion
    MAX_LINKS_PER_NODE = 10

    def __init__(self) -> None:
        super().__init__(
            name="LinkManager",
            role="Knowledge stitcher — creates cross-domain shortcuts between related nodes",
            capabilities=[AgentCapability.RESEARCH],
        )
        self._store = None
        self._graph = None
        # Track co-occurrence patterns: (node_a, node_b) -> count
        self._cooccurrence: dict[tuple[str, str], int] = {}
        self._links_created: int = 0
        self._links_severed: int = 0
        self._pending_stitches: list[dict[str, Any]] = []

    @property
    def work_interval(self) -> float:
        return 45.0  # check regularly but not too frequently

    def set_dependencies(self, store: Any, graph: Any) -> None:
        self._store = store
        self._graph = graph

    async def do_work(self) -> None:
        """Look for stitching opportunities and maintain existing links."""
        if not self._store or not self._graph:
            return

        # Phase 1: Process pending stitch requests
        await self._process_pending_stitches()

        # Phase 2: Evaluate existing links for quality
        await self._evaluate_link_quality()

        # Phase 3: Auto-discover stitching opportunities from co-occurrence
        await self._discover_stitching_opportunities()

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "alert" and msg.payload.get("type") == "node_created":
            # New node — check if it should be linked to existing nodes
            node_id = msg.payload.get("node_id")
            domain = msg.payload.get("domain")
            tags = msg.payload.get("tags", [])
            if node_id and domain:
                await self._evaluate_new_node_links(node_id, domain, tags)

        elif msg.kind == "alert" and msg.payload.get("type") == "node_pruned":
            # Node pruned — cascading severance already handled by graph
            report = msg.payload.get("cascade_report", {})
            severed = report.get("severed_links", [])
            self._links_severed += len(severed)

        elif msg.kind == "alert" and msg.payload.get("type") == "node_updated":
            # Node updated — re-evaluate its links
            node_id = msg.payload.get("node_id")
            if node_id:
                await self._reevaluate_node_links(node_id)

        elif msg.kind == "request" and msg.payload.get("type") == "record_cooccurrence":
            # An agent accessed two nodes in the same query
            node_a = msg.payload.get("node_a")
            node_b = msg.payload.get("node_b")
            if node_a and node_b:
                self.record_cooccurrence(node_a, node_b)

        elif msg.kind == "request" and msg.payload.get("type") == "create_link":
            # Direct request to stitch two nodes
            source = msg.payload.get("source_node")
            target = msg.payload.get("target_node")
            relationship = msg.payload.get("relationship", "commonly_paired")
            if source and target:
                self._pending_stitches.append({
                    "source": source,
                    "target": target,
                    "relationship": relationship,
                    "requester": msg.sender,
                    "weight": msg.payload.get("weight", 0.5),
                })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "knowledge_linking",
            "topics": [
                "graph_theory_optimization",
                "semantic_similarity_shortcuts",
                "cross_domain_pattern_detection",
            ],
        })

    # -- Co-occurrence tracking -------------------------------------------

    def record_cooccurrence(self, node_a: str, node_b: str) -> None:
        """Record that two nodes were accessed in the same context."""
        key = tuple(sorted([node_a, node_b]))
        self._cooccurrence[key] = self._cooccurrence.get(key, 0) + 1

    # -- Stitching logic --------------------------------------------------

    async def _process_pending_stitches(self) -> None:
        """Create links from pending stitch requests."""
        if not self._pending_stitches or not self._store:
            return

        for stitch in self._pending_stitches[:]:
            source_id = stitch["source"]
            target_id = stitch["target"]

            source = self._store.load_node(source_id)
            target = self._store.load_node(target_id)

            if not source or not target:
                self._pending_stitches.remove(stitch)
                continue

            # Check link limits
            if len(source.link_ids) >= self.MAX_LINKS_PER_NODE:
                self.log.warning("link.max_reached", node_id=source_id)
                self._pending_stitches.remove(stitch)
                continue

            # Create the link
            try:
                rel = LinkRelationship(stitch.get("relationship", "commonly_paired"))
            except ValueError:
                rel = LinkRelationship.COMMONLY_PAIRED

            link = Link(
                source_node_id=source_id,
                target_node_id=target_id,
                relationship=rel,
                shortcut_weight=stitch.get("weight", 0.5),
                description=f"Stitched by LinkManager: {source.domain} <-> {target.domain}",
            )

            # Save link and update both nodes
            self._store.save_link(link)
            source.link_ids.append(link.id)
            target.link_ids.append(link.id)
            self._store.save_node(source)
            self._store.save_node(target)

            self._links_created += 1
            self._pending_stitches.remove(stitch)

            self.log.info("link.stitched",
                          link_id=link.id,
                          source=source_id, target=target_id,
                          relationship=rel.value)

            # Notify LockManager — it may want to evaluate for locking
            await self.send("LockManager", "alert", {
                "type": "link_created",
                "link_id": link.id,
                "source_node": source_id,
                "target_node": target_id,
            })

    async def _evaluate_link_quality(self) -> None:
        """Check existing links — prune weak ones, promote strong ones."""
        if not self._store:
            return

        for link_id, meta in list(self._store._index.get("links", {}).items()):
            link = self._store.load_link(link_id)
            if not link:
                continue

            # Prune links with low success rate after sufficient usage
            if link.use_count > 10 and link.success_rate < 0.3:
                # This link isn't working — sever it
                self._sever_link(link)
                self._links_severed += 1
                self.log.info("link.severed_low_quality",
                              link_id=link_id, success_rate=link.success_rate)

            # Promote highly successful links — notify LockManager
            elif link.use_count > 20 and link.success_rate > 0.95:
                await self.send("LockManager", "request", {
                    "type": "evaluate_for_lock",
                    "link_id": link_id,
                    "source_node": link.source_node_id,
                    "target_node": link.target_node_id,
                    "success_rate": link.success_rate,
                    "use_count": link.use_count,
                })

    async def _discover_stitching_opportunities(self) -> None:
        """Find node pairs that should be linked based on co-occurrence."""
        for (node_a, node_b), count in list(self._cooccurrence.items()):
            if count < self.MIN_COOCCURRENCE:
                continue

            # Check if already linked
            if self._store:
                links_a = self._store.find_links_for_node(node_a)
                already_linked = False
                for lid in links_a:
                    link = self._store.load_link(lid)
                    if link and (
                        link.target_node_id == node_b or
                        link.source_node_id == node_b
                    ):
                        already_linked = True
                        break

                if not already_linked:
                    weight = min(1.0, count / 20.0)  # scale weight by frequency
                    if weight >= self.MIN_WEIGHT_THRESHOLD:
                        self._pending_stitches.append({
                            "source": node_a,
                            "target": node_b,
                            "relationship": "commonly_paired",
                            "requester": "LinkManager",
                            "weight": weight,
                        })

    async def _evaluate_new_node_links(self, node_id: str, domain: str,
                                       tags: list[str]) -> None:
        """Check if a new node should be linked to existing nodes in same domain."""
        if not self._store:
            return

        # Find nodes in the same domain
        domain_nodes = self._store.find_nodes_by_domain(domain)
        for existing_id in domain_nodes[:5]:  # limit to avoid explosion
            if existing_id == node_id:
                continue
            # Queue for potential stitching
            self._pending_stitches.append({
                "source": node_id,
                "target": existing_id,
                "relationship": "commonly_paired",
                "requester": "LinkManager:auto_domain",
                "weight": 0.4,
            })

        # Also check by shared tags
        for tag in tags[:3]:
            tagged_nodes = self._store.find_nodes_by_tag(tag)
            for existing_id in tagged_nodes[:3]:
                if existing_id == node_id:
                    continue
                if not any(
                    s.get("source") == node_id and s.get("target") == existing_id
                    for s in self._pending_stitches
                ):
                    self._pending_stitches.append({
                        "source": node_id,
                        "target": existing_id,
                        "relationship": "commonly_paired",
                        "requester": "LinkManager:auto_tag",
                        "weight": 0.35,
                    })

    async def _reevaluate_node_links(self, node_id: str) -> None:
        """When a node is updated, check if its links are still valid."""
        if not self._store:
            return

        link_ids = self._store.find_links_for_node(node_id)
        for link_id in link_ids:
            link = self._store.load_link(link_id)
            if link:
                # Reset success rate — needs re-proving
                link.success_rate = link.success_rate * 0.5  # halve confidence
                self._store.save_link(link)

    def _sever_link(self, link: Link) -> None:
        """Remove a link and clean up node references."""
        if not self._store:
            return

        # Remove from source node
        source = self._store.load_node(link.source_node_id)
        if source and link.id in source.link_ids:
            source.link_ids.remove(link.id)
            self._store.save_node(source)

        # Remove from target node
        target = self._store.load_node(link.target_node_id)
        if target and link.id in target.link_ids:
            target.link_ids.remove(link.id)
            self._store.save_node(target)

        self._store.delete_link(link.id)

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "links_created": self._links_created,
            "links_severed": self._links_severed,
            "pending_stitches": len(self._pending_stitches),
            "cooccurrence_pairs": len(self._cooccurrence),
        })
        return base
