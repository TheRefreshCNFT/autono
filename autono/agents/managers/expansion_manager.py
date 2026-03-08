"""ExpansionManager — watches embed resources, prunes dead data.

The janitor and gardener of the knowledge graph. Keeps everything
clean, updated, and growing.

Responsibilities:
- Watch for new .md files from ResearchManager → create nodes
- Prune stale/dead nodes (cascading severance — no ghost links)
- Coordinate with EmbedManager for re-embedding updated content
- Handle the "dead link" problem: backtrack URLs, search for new sources
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
)


class ExpansionManager(AutonomousAgent):
    """Knowledge graph gardener.

    Watches for changes, prunes dead data, grows the graph.
    When a node is pruned, triggers cascading severance through
    the KnowledgeGraph — all connected links are severed,
    all dependent locks are shattered. No ghost data.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ExpansionManager",
            role="Knowledge pruner and grower — keeps the graph clean and current",
            capabilities=[AgentCapability.RESEARCH, AgentCapability.AUDIT],
        )
        self._store = None
        self._graph = None
        self._processed_files: set[str] = set()
        self._nodes_created: int = 0
        self._nodes_pruned: int = 0

    @property
    def work_interval(self) -> float:
        return 30.0  # check frequently for new research files

    def set_dependencies(self, store: Any, graph: Any) -> None:
        """Inject store and graph (called by orchestrator)."""
        self._store = store
        self._graph = graph

    async def do_work(self) -> None:
        """Main cycle: check for new research, prune stale nodes."""
        if not self._store or not self._graph:
            return

        # Phase 1: Watch for new .md files from ResearchManager
        await self._process_new_research()

        # Phase 2: Prune nodes marked as stale by EmbedManager
        await self._prune_stale_nodes()

        # Phase 3: Handle dead sources (URL backtracking logic)
        await self._handle_dead_sources()

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "alert" and msg.payload.get("type") == "state_change":
            # EmbedManager detected stale data — schedule for pruning review
            node_id = msg.payload.get("node_id")
            if node_id:
                self.log.info("expansion.stale_notification", node_id=node_id)
                # The pruning cycle will handle it

        elif msg.kind == "request" and msg.payload.get("type") == "ingest_research":
            # ResearchManager finished a new file
            filename = msg.payload.get("filename")
            if filename:
                await self._ingest_research_file(filename)

        elif msg.kind == "request" and msg.payload.get("type") == "force_prune":
            node_id = msg.payload.get("node_id")
            if node_id and self._graph:
                report = self._graph.cascade_prune(node_id)
                self._nodes_pruned += 1
                await self.send(msg.sender, "response", {
                    "type": "prune_complete",
                    "report": report,
                })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "knowledge_expansion",
            "topics": [
                "automated_knowledge_extraction",
                "source_reliability_scoring",
                "semantic_deduplication",
            ],
        })

    # -- Research ingestion -----------------------------------------------

    async def _process_new_research(self) -> None:
        """Check for new .md files and create knowledge nodes."""
        if not self._store:
            return

        research_files = self._store.list_research_files()
        new_files = [f for f in research_files if f not in self._processed_files]

        for filename in new_files:
            await self._ingest_research_file(filename)
            self._processed_files.add(filename)

    async def _ingest_research_file(self, filename: str) -> None:
        """Parse a research .md file and create/update knowledge nodes."""
        if not self._store:
            return

        content = self._store.load_research(filename)
        if not content:
            return

        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        # Check if we already have a node for this file
        existing_nodes = [
            nid for nid, meta in self._store._index.get("nodes", {}).items()
        ]
        for nid in existing_nodes:
            node = self._store.load_node(nid)
            if node and node.source_file == filename:
                # File exists — check if content changed
                if node.source_hash == content_hash:
                    return  # unchanged, skip
                else:
                    # Content changed — update node, broadcast change
                    node.source_hash = content_hash
                    node.content = self._extract_summary(content)
                    node.status = NodeStatus.ACTIVE
                    node.last_validated = datetime.now(timezone.utc).isoformat()
                    self._store.save_node(node)

                    # Broadcast NODE_UPDATED — LockManager may need to shatter
                    await self.broadcast("alert", {
                        "type": "node_updated",
                        "node_id": nid,
                        "source_file": filename,
                        "new_hash": content_hash,
                    }, priority=2)
                    return

        # New file — create a node
        domain, subdomain = self._infer_domain(filename, content)
        node = KnowledgeNode(
            content=self._extract_summary(content),
            domain=domain,
            subdomain=subdomain,
            source_file=filename,
            source_hash=content_hash,
            tags=self._extract_tags(content),
        )

        # Ask EmbedManager for volatility scoring
        await self.send("EmbedManager", "request", {
            "type": "score_volatility",
            "domain": domain,
            "subdomain": subdomain,
        })

        self._store.save_node(node)
        self._nodes_created += 1
        self.log.info("expansion.node_created",
                      node_id=node.id, source=filename, domain=domain)

        # Broadcast NODE_CREATED — LinkManager watches for stitching opportunities
        await self.broadcast("alert", {
            "type": "node_created",
            "node_id": node.id,
            "domain": domain,
            "subdomain": subdomain,
            "tags": node.tags,
        })

    # -- Pruning ----------------------------------------------------------

    async def _prune_stale_nodes(self) -> None:
        """Find and prune nodes marked as stale."""
        if not self._store or not self._graph:
            return

        stale_ids = self._store.find_nodes_by_status("stale")
        for node_id in stale_ids:
            node = self._store.load_node(node_id)
            if not node:
                continue

            # Try to recover the source first (backtrack logic)
            recovered = await self._try_recover_source(node)
            if recovered:
                node.status = NodeStatus.ACTIVE
                node.last_validated = datetime.now(timezone.utc).isoformat()
                self._store.save_node(node)
                continue

            # Can't recover — cascade prune
            report = self._graph.cascade_prune(node_id)
            self._nodes_pruned += 1

            # Broadcast so all managers know
            await self.broadcast("alert", {
                "type": "node_pruned",
                "node_id": node_id,
                "cascade_report": report,
            }, priority=2)

    async def _handle_dead_sources(self) -> None:
        """Handle the dead link problem.

        What would a human do if the site said 404?
        1. Delete the bookmark
        2. Search again

        The topic didn't go away — the resource went away.
        Fastest solution: backtrack the URL one / at a time.
        If no longer a site, delete the lock and that link.
        Start searching from last valid reference forward.
        """
        # This runs as part of the stale pruning cycle
        # The actual backtracking is in _try_recover_source
        pass

    async def _try_recover_source(self, node: KnowledgeNode) -> bool:
        """Attempt to recover a dead source by backtracking.

        Like a human: if the URL 404s, try the parent path.
        If the whole site is gone, mark for re-research.
        """
        if not node.source_file:
            return False

        # For .md files, check if the file still exists
        if self._store:
            content = self._store.load_research(node.source_file)
            if content:
                new_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
                if new_hash != node.source_hash:
                    # Content changed — update, don't delete
                    node.source_hash = new_hash
                    node.content = self._extract_summary(content)
                    self._store.save_node(node)

                    await self.broadcast("alert", {
                        "type": "source_recovered",
                        "node_id": node.id,
                        "method": "content_updated",
                    })
                    return True
                return True  # file exists, hash matches

        # File gone — request ResearchManager to find replacement
        await self.send("ResearchManager", "request", {
            "type": "find_replacement",
            "original_domain": node.domain,
            "original_subdomain": node.subdomain,
            "original_content_summary": node.content[:200],
            "tags": node.tags,
        })

        return False

    # -- Content extraction helpers ---------------------------------------

    def _extract_summary(self, content: str) -> str:
        """Extract the first meaningful paragraph from .md content."""
        lines = content.strip().split("\n")
        summary_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if stripped:
                summary_lines.append(stripped)
            if len(summary_lines) >= 3:
                break
        return " ".join(summary_lines)[:500]

    def _extract_tags(self, content: str) -> list[str]:
        """Extract relevant tags from content."""
        tags = []
        keywords = [
            "cardano", "bitcoin", "utxo", "nft", "token", "bridge",
            "wallet", "transaction", "smart contract", "defi",
            "charms", "spell", "zk-proof", "taproot", "plutus",
            "minting", "staking", "governance", "metadata",
        ]
        content_lower = content.lower()
        for kw in keywords:
            if kw in content_lower:
                tags.append(kw)
        return tags[:10]

    def _infer_domain(self, filename: str, content: str) -> tuple[str, str]:
        """Infer the knowledge domain from filename and content."""
        fname = filename.lower()
        content_lower = content.lower()

        domain_hints = [
            ("cardano", "cardano"),
            ("bitcoin", "bitcoin"),
            ("charms", "charms"),
            ("bitcoinos", "bitcoinos"),
            ("night", "night_chain"),
            ("defi", "defi"),
            ("nft", "nft"),
            ("bridge", "bridge"),
        ]

        for hint, domain in domain_hints:
            if hint in fname or hint in content_lower[:500]:
                # Try to infer subdomain
                subdomain = ""
                subdomain_hints = [
                    "protocol", "wallet", "sdk", "api", "price",
                    "cip", "bip", "transaction", "smart_contract",
                ]
                for sub in subdomain_hints:
                    if sub in content_lower[:1000]:
                        subdomain = sub
                        break
                return domain, subdomain

        return "general", ""

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "nodes_created": self._nodes_created,
            "nodes_pruned": self._nodes_pruned,
            "processed_files": len(self._processed_files),
        })
        return base
