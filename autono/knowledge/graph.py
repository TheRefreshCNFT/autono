"""Knowledge Graph — the wired network of Links & Locks.

This is the navigation layer that sits on top of embeddings.
Agents don't need to "think" their way through — they follow the wires.

The graph supports:
- Forward chaining: "I have X, what does it connect to?"
- Backward chaining: "I need result Y, what paths get me there?"
- Lock checking: "Is there a deterministic answer? Skip inference."
- Link jumping: "What shortcuts exist from this node?"
- Cascading severance: "This node was pruned, sever all connections."

Hop limit: Max 3 hops to prevent context window flooding.
"""

from __future__ import annotations

from typing import Any

import structlog

from autono.knowledge.store import KnowledgeStore
from autono.knowledge.types import (
    KnowledgeNode,
    Link,
    Lock,
    MLock,
    NodeStatus,
)

log = structlog.get_logger()

MAX_HOPS = 3  # hard ceiling on link traversal depth


class QueryResult:
    """Result of a knowledge graph query."""

    def __init__(self) -> None:
        self.hit_lock: bool = False
        self.hit_mlock: bool = False
        self.locked_answer: Any = None
        self.answer_source: str = ""        # lock_id or mlock_id
        self.traversed_nodes: list[str] = []
        self.gathered_context: list[dict[str, Any]] = []
        self.available_paths: list[dict[str, Any]] = []
        self.hops_used: int = 0
        self.bypass_llm: bool = False       # if true, don't send to model

    def as_dict(self) -> dict[str, Any]:
        return {
            "hit_lock": self.hit_lock,
            "hit_mlock": self.hit_mlock,
            "locked_answer": self.locked_answer,
            "answer_source": self.answer_source,
            "traversed_nodes": self.traversed_nodes,
            "context_count": len(self.gathered_context),
            "paths_available": len(self.available_paths),
            "hops_used": self.hops_used,
            "bypass_llm": self.bypass_llm,
        }


class KnowledgeGraph:
    """The wired network. Agents navigate this, they don't build it.

    Managers build and maintain the graph asynchronously:
    - LinkManager stitches connections
    - LockManager seals deterministic facts
    - EmbedManager validates volatility
    - ExpansionManager prunes dead nodes (cascading severance)
    """

    def __init__(self, store: KnowledgeStore) -> None:
        self.store = store

    # -- Primary query interface ------------------------------------------

    def query_node(self, node_id: str) -> QueryResult:
        """Main entry point for agents. Check locks first, then follow links.

        This implements the deterministic-first logic:
        1. Load the node
        2. Check if it has a Lock → return immediately (bypass LLM)
        3. Check if it has an mLock → return with path options
        4. If no lock, follow links up to MAX_HOPS for context
        5. Return gathered context for the agent to reason over
        """
        result = QueryResult()
        node = self.store.load_node(node_id)
        if not node or node.status == NodeStatus.PRUNED:
            return result

        result.traversed_nodes.append(node_id)

        # Step 1: Lock check — the instant answer
        if node.is_locked and node.lock_id:
            lock = self.store.load_lock(node.lock_id)
            if lock and lock.status == NodeStatus.ACTIVE:
                if isinstance(lock, MLock) or node.is_mlocked:
                    result.hit_mlock = True
                else:
                    result.hit_lock = True
                result.locked_answer = lock.absolute_answer
                result.answer_source = lock.id
                result.bypass_llm = True
                log.info("graph.lock_hit", node_id=node_id, lock_id=lock.id)
                return result

        # Step 2: No lock — follow links for context
        self._traverse_links(node, result, depth=0)

        return result

    def backward_chain(self, target_value: Any, mlock_id: str = "") -> QueryResult:
        """Reverse lookup: "I need this result, what paths lead to it?"

        Used when an agent knows WHAT it needs but not HOW to get there.
        The mLock's incoming_links array provides the menu of solutions.
        """
        result = QueryResult()

        if mlock_id:
            # Direct mLock lookup
            lock_data = self.store.load_lock(mlock_id)
            if lock_data:
                result.hit_mlock = True
                result.locked_answer = target_value
                result.answer_source = mlock_id
                result.bypass_llm = True
                return result

        # Scan all mlocks for matching payload
        for mid in self.store._index.get("mlocks", {}):
            lock_path = self.store.base_path / "locks" / f"{mid}.json"
            if lock_path.exists():
                import json
                with open(lock_path) as f:
                    data = json.load(f)
                if data.get("payload") == target_value:
                    result.hit_mlock = True
                    result.locked_answer = target_value
                    result.answer_source = mid
                    # Load incoming paths
                    for path in data.get("incoming_links", []):
                        result.available_paths.append(path)
                    result.bypass_llm = True
                    return result

        return result

    # -- Link traversal ---------------------------------------------------

    def _traverse_links(self, node: KnowledgeNode, result: QueryResult,
                        depth: int) -> None:
        """Follow links from a node, gathering context up to MAX_HOPS."""
        if depth >= MAX_HOPS:
            return

        for link_id in node.link_ids:
            link = self.store.load_link(link_id)
            if not link or link.shortcut_weight < 0.3:
                continue

            # Determine which end we haven't visited
            target_id = (
                link.target_node_id
                if link.source_node_id == node.id
                else link.source_node_id
            )

            if target_id in result.traversed_nodes:
                continue

            target = self.store.load_node(target_id)
            if not target or target.status == NodeStatus.PRUNED:
                continue

            result.traversed_nodes.append(target_id)
            result.hops_used = max(result.hops_used, depth + 1)

            # Check if the linked node has a lock
            if target.is_locked and target.lock_id:
                lock = self.store.load_lock(target.lock_id)
                if lock and lock.status == NodeStatus.ACTIVE:
                    result.gathered_context.append({
                        "node_id": target_id,
                        "content": target.content,
                        "locked_answer": lock.absolute_answer,
                        "relationship": link.relationship.value if hasattr(link.relationship, "value") else link.relationship,
                        "hop": depth + 1,
                    })
                    # Record link usage
                    link.record_use(success=True)
                    self.store.save_link(link)
                    continue

            # No lock — add content as context
            result.gathered_context.append({
                "node_id": target_id,
                "content": target.content,
                "domain": target.domain,
                "relationship": link.relationship.value if hasattr(link.relationship, "value") else link.relationship,
                "hop": depth + 1,
            })

            # Record usage and recurse
            link.record_use(success=True)
            self.store.save_link(link)
            self._traverse_links(target, result, depth + 1)

    # -- Cascading severance (for ExpansionManager) -----------------------

    def cascade_prune(self, node_id: str) -> dict[str, list[str]]:
        """When a node is pruned, sever all connections and shatter locks.

        This is the "immune response" — no ghost links, no dangling pointers.
        Returns a report of everything affected.
        """
        severed_links: list[str] = []
        shattered_locks: list[str] = []
        affected_nodes: list[str] = []

        # Find and sever all links touching this node
        link_ids = self.store.find_links_for_node(node_id)
        for link_id in link_ids:
            link = self.store.load_link(link_id)
            if link:
                # Find the other node and remove this link from its list
                other_id = (
                    link.target_node_id
                    if link.source_node_id == node_id
                    else link.source_node_id
                )
                other_node = self.store.load_node(other_id)
                if other_node and link_id in other_node.link_ids:
                    other_node.link_ids.remove(link_id)
                    self.store.save_node(other_node)
                    affected_nodes.append(other_id)

            self.store.delete_link(link_id)
            severed_links.append(link_id)

        # Shatter any lock on this node
        node = self.store.load_node(node_id)
        if node and node.lock_id:
            lock = self.store.load_lock(node.lock_id)
            if lock:
                lock.shatter(f"dependency_pruned:{node_id}")
                self.store.save_lock(lock)
                shattered_locks.append(node.lock_id)

        # Delete the node itself
        self.store.delete_node(node_id)

        report = {
            "pruned_node": [node_id],
            "severed_links": severed_links,
            "shattered_locks": shattered_locks,
            "affected_nodes": affected_nodes,
        }

        log.info("graph.cascade_prune", **{k: len(v) for k, v in report.items()})
        return report

    # -- Utility ----------------------------------------------------------

    def get_node_neighborhood(self, node_id: str) -> dict[str, Any]:
        """Get a node and all its immediate connections. Debug/inspection."""
        node = self.store.load_node(node_id)
        if not node:
            return {"error": "node_not_found"}

        links = []
        for link_id in node.link_ids:
            link = self.store.load_link(link_id)
            if link:
                links.append({
                    "link_id": link.id,
                    "target": link.target_node_id if link.source_node_id == node_id else link.source_node_id,
                    "relationship": link.relationship.value if hasattr(link.relationship, "value") else link.relationship,
                    "weight": link.shortcut_weight,
                })

        lock_info = None
        if node.lock_id:
            lock = self.store.load_lock(node.lock_id)
            if lock:
                lock_info = {
                    "lock_id": lock.id,
                    "status": lock.status.value if hasattr(lock.status, "value") else lock.status,
                    "answer": lock.absolute_answer,
                }

        return {
            "node": {
                "id": node.id,
                "content": node.content,
                "domain": node.domain,
                "status": node.status.value if hasattr(node.status, "value") else node.status,
                "volatility": node.volatility.value if hasattr(node.volatility, "value") else node.volatility,
                "tags": node.tags,
            },
            "links": links,
            "lock": lock_info,
        }

    def stats(self) -> dict[str, Any]:
        """Graph-level statistics."""
        store_stats = self.store.stats()
        return {
            **store_stats,
            "max_hops": MAX_HOPS,
            "graph_healthy": store_stats["stale_nodes"] == 0,
        }
