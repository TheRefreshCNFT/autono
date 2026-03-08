"""LockManager — the Healer, sealing the cuts permanently.

When the Doctor (LinkManager) stitches a cut and it proves reliable,
the Healer seals it. A Lock means: this is an absolute truth.
No inference needed. The agent follows the wire and gets the answer.

mLock = Multi-Lock. Multiple paths converge to one truth.
1+1=2 → Lock. 3-1=2 → same answer → upgrade to mLock.
"I need 2" → here are ALL the ways to get it (backward chaining).

The LockManager watches for:
1. STATE_CHANGE events from EmbedManager → shatter affected locks
2. NODE_PRUNED events from ExpansionManager → cascading shatter
3. High-success links from LinkManager → evaluate for lock promotion
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message
from autono.knowledge.types import (
    KnowledgeNode,
    Lock,
    MLock,
    NodeStatus,
    VolatilityTier,
)


class LockManager(AutonomousAgent):
    """The Healer — seals deterministic facts for instant retrieval.

    Rules for locking:
    1. Node must have been accessed successfully N times without correction
    2. Source data must be verifiable (has dependency_hash)
    3. Volatility must be STABLE or lower (volatile data can't be locked)
    4. EmbedManager has authority to force shatter via STATE_CHANGE
    5. ExpansionManager prune events trigger immediate shatter

    The LockManager doesn't defend stale locks. When the EmbedManager
    says "the floor you're standing on was just deleted," the lock
    shatters instantly. No questions asked.
    """

    # Minimum successful accesses before considering a lock
    MIN_SUCCESS_COUNT = 5
    # Minimum success rate for lock promotion
    MIN_SUCCESS_RATE = 0.95

    def __init__(self) -> None:
        super().__init__(
            name="LockManager",
            role="Knowledge sealer — creates deterministic fact locks for instant retrieval",
            capabilities=[AgentCapability.AUDIT],
        )
        self._store = None
        self._graph = None
        self._locks_created: int = 0
        self._locks_shattered: int = 0
        self._mlocks_created: int = 0
        self._evaluation_queue: list[dict[str, Any]] = []

    @property
    def work_interval(self) -> float:
        return 60.0  # sealing is deliberate, not rushed

    def set_dependencies(self, store: Any, graph: Any) -> None:
        self._store = store
        self._graph = graph

    async def do_work(self) -> None:
        """Evaluate lock candidates and maintain existing locks."""
        if not self._store:
            return

        # Phase 1: Process lock evaluation requests
        await self._process_evaluation_queue()

        # Phase 2: Check existing locks for integrity
        await self._validate_existing_locks()

    async def handle_message(self, msg: Message) -> None:
        # STATE_CHANGE from EmbedManager — shatter affected locks
        if msg.kind == "alert" and msg.payload.get("type") == "state_change":
            node_id = msg.payload.get("node_id")
            if node_id:
                await self._shatter_node_lock(node_id, "state_change")

        # NODE_PRUNED from ExpansionManager — cascading shatter
        elif msg.kind == "alert" and msg.payload.get("type") == "node_pruned":
            cascade = msg.payload.get("cascade_report", {})
            for lock_id in cascade.get("shattered_locks", []):
                self._locks_shattered += 1
                self.log.info("lock.cascade_shattered", lock_id=lock_id)

        # NODE_UPDATED — re-evaluate the lock
        elif msg.kind == "alert" and msg.payload.get("type") == "node_updated":
            node_id = msg.payload.get("node_id")
            new_hash = msg.payload.get("new_hash")
            if node_id:
                await self._handle_node_update(node_id, new_hash)

        # Link promotion request from LinkManager
        elif msg.kind == "request" and msg.payload.get("type") == "evaluate_for_lock":
            self._evaluation_queue.append({
                "link_id": msg.payload.get("link_id"),
                "source_node": msg.payload.get("source_node"),
                "target_node": msg.payload.get("target_node"),
                "success_rate": msg.payload.get("success_rate", 0),
                "use_count": msg.payload.get("use_count", 0),
                "requester": msg.sender,
            })

        # Direct lock request (for seeding known facts)
        elif msg.kind == "request" and msg.payload.get("type") == "create_lock":
            await self._create_lock_direct(msg.payload)

        # Direct mLock request
        elif msg.kind == "request" and msg.payload.get("type") == "create_mlock":
            await self._create_mlock_direct(msg.payload)

        # Contradiction detection from main agent
        elif msg.kind == "alert" and msg.payload.get("type") == "stale_flag":
            node_id = msg.payload.get("node_id")
            reason = msg.payload.get("reason", "user_contradiction")
            if node_id:
                await self._shatter_node_lock(node_id, reason)
                # Also notify ResearchManager to investigate
                await self.send("ResearchManager", "request", {
                    "type": "research_topic",
                    "topic": f"verify:{msg.payload.get('content', '')}",
                    "domain": msg.payload.get("domain", ""),
                    "priority": 3,  # high priority — user contradiction
                })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "deterministic_caching",
            "topics": [
                "lock_promotion_criteria",
                "mlock_convergence_patterns",
                "dependency_hash_validation",
            ],
        })

    # -- Lock creation ----------------------------------------------------

    async def _process_evaluation_queue(self) -> None:
        """Evaluate candidates for lock promotion."""
        if not self._evaluation_queue or not self._store:
            return

        for candidate in self._evaluation_queue[:]:
            success_rate = candidate.get("success_rate", 0)
            use_count = candidate.get("use_count", 0)

            # Must meet minimum thresholds
            if use_count < self.MIN_SUCCESS_COUNT:
                continue
            if success_rate < self.MIN_SUCCESS_RATE:
                continue

            source_id = candidate.get("source_node")
            target_id = candidate.get("target_node")
            if not source_id or not target_id:
                self._evaluation_queue.remove(candidate)
                continue

            source = self._store.load_node(source_id)
            target = self._store.load_node(target_id)

            if not source or not target:
                self._evaluation_queue.remove(candidate)
                continue

            # Don't lock volatile nodes
            if source.volatility in (VolatilityTier.VOLATILE, VolatilityTier.REALTIME):
                self._evaluation_queue.remove(candidate)
                continue

            # Check if target already has a lock we can upgrade to mLock
            if target.is_locked and target.lock_id:
                existing = self._store.load_lock(target.lock_id)
                if existing and existing.status == NodeStatus.ACTIVE:
                    # Potential mLock upgrade
                    self.log.info("lock.mlock_candidate",
                                  source=source_id, target=target_id)

            self._evaluation_queue.remove(candidate)

    async def _create_lock_direct(self, payload: dict[str, Any]) -> None:
        """Create a lock from a direct request (seeding known facts)."""
        if not self._store:
            return

        node_id = payload.get("node_id", "")
        node = self._store.load_node(node_id) if node_id else None
        if not node:
            return

        lock = Lock(
            node_id=node_id,
            absolute_answer=payload.get("answer"),
            answer_type=payload.get("answer_type", "string"),
            verification_source=payload.get("source", "direct_seed"),
        )

        # Compute dependency hash
        source_data = str(payload.get("answer", ""))
        lock.compute_dependency_hash(source_data)

        self._store.save_lock(lock)

        # Update the node
        node.is_locked = True
        node.lock_id = lock.id
        node.bypass_llm = True
        self._store.save_node(node)

        self._locks_created += 1
        self.log.info("lock.created",
                      lock_id=lock.id, node_id=node_id,
                      answer_type=lock.answer_type)

    async def _create_mlock_direct(self, payload: dict[str, Any]) -> None:
        """Create or update an mLock from a direct request."""
        if not self._store:
            return

        # Check if an mLock for this payload already exists
        target_value = payload.get("payload")
        existing_mlock_id = payload.get("mlock_id")

        if existing_mlock_id:
            # Adding a new path to existing mLock
            # Load from file since it may be an MLock stored as lock
            lock_path = self._store.base_path / "locks" / f"{existing_mlock_id}.json"
            if lock_path.exists():
                import json
                with open(lock_path) as f:
                    data = json.load(f)

                # Add new incoming path
                new_path = {
                    "source_embed_id": payload.get("source_embed_id", ""),
                    "method": payload.get("method", ""),
                    "compute_cost": payload.get("compute_cost", "LOW"),
                    "success_rate": 1.0,
                    "use_count": 0,
                }
                paths = data.get("incoming_links", [])
                paths.append(new_path)
                data["incoming_links"] = paths

                with open(lock_path, "w") as f:
                    json.dump(data, f, indent=2)

                self.log.info("mlock.path_added",
                              mlock_id=existing_mlock_id,
                              method=new_path["method"])
                return

        # Create new mLock
        mlock = MLock(
            payload=target_value,
            payload_type=payload.get("payload_type", "string"),
            description=payload.get("description", ""),
            verification_source=payload.get("source", "direct_seed"),
            volatility=VolatilityTier.PERMANENT,
        )

        # Add initial incoming path
        mlock.add_path(
            source_embed_id=payload.get("source_embed_id", ""),
            method=payload.get("method", ""),
            compute_cost=payload.get("compute_cost", "LOW"),
        )

        self._store.save_mlock(mlock)
        self._mlocks_created += 1

        self.log.info("mlock.created",
                      mlock_id=mlock.id,
                      payload=str(target_value)[:50])

        # If there's a node to attach to, update it
        node_id = payload.get("node_id")
        if node_id:
            node = self._store.load_node(node_id)
            if node:
                node.is_locked = True
                node.is_mlocked = True
                node.lock_id = mlock.id
                node.bypass_llm = True
                self._store.save_node(node)

    # -- Lock maintenance -------------------------------------------------

    async def _validate_existing_locks(self) -> None:
        """Check active locks for integrity via dependency hash."""
        if not self._store:
            return

        active_locks = self._store.find_locks_by_status("active")
        for lock_id in active_locks[:20]:  # batch limit
            lock = self._store.load_lock(lock_id)
            if not lock:
                continue

            # Verify the node still exists
            if hasattr(lock, "node_id") and lock.node_id:
                node = self._store.load_node(lock.node_id)
                if not node or node.status == NodeStatus.PRUNED:
                    lock.shatter("node_pruned")
                    self._store.save_lock(lock)
                    self._locks_shattered += 1

    async def _shatter_node_lock(self, node_id: str, reason: str) -> None:
        """Shatter the lock on a specific node."""
        if not self._store:
            return

        node = self._store.load_node(node_id)
        if not node or not node.is_locked:
            return

        lock = self._store.load_lock(node.lock_id)
        if lock and lock.status == NodeStatus.ACTIVE:
            lock.shatter(reason)
            self._store.save_lock(lock)
            self._locks_shattered += 1

            # Update node
            node.is_locked = False
            node.bypass_llm = False
            self._store.save_node(node)

            self.log.warning("lock.shattered",
                             lock_id=lock.id, node_id=node_id, reason=reason)

            await self.broadcast("alert", {
                "type": "lock_shattered",
                "lock_id": lock.id,
                "node_id": node_id,
                "reason": reason,
            })

    async def _handle_node_update(self, node_id: str, new_hash: str | None) -> None:
        """When a node's content changes, verify or shatter its lock."""
        if not self._store:
            return

        node = self._store.load_node(node_id)
        if not node or not node.is_locked:
            return

        lock = self._store.load_lock(node.lock_id)
        if not lock:
            return

        # If we have a new hash, compare with lock's dependency
        if new_hash and lock.dependency_hash:
            if new_hash != lock.dependency_hash:
                await self._shatter_node_lock(node_id, "dependency_hash_mismatch")
                return

        # No hash comparison possible — shatter to be safe
        await self._shatter_node_lock(node_id, "source_updated_no_hash")

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "locks_created": self._locks_created,
            "locks_shattered": self._locks_shattered,
            "mlocks_created": self._mlocks_created,
            "evaluation_queue": len(self._evaluation_queue),
        })
        return base
