"""Cross-Chain Orchestrator — coordinates all chain specialists and managers.

This is NOT a boss — it's a launcher and router (same philosophy as the
main Orchestrator). Chain agents and managers are autonomous once started.

The orchestrator:
1. Boots all managers and chain specialist agents
2. Injects the shared KnowledgeStore and KnowledgeGraph
3. Connects everything via the existing MessageBus
4. Seeds initial protocol knowledge
5. Provides a unified interface for cross-chain queries

Architecture:
    ┌──────────────────────────────────────────────────────────────────┐
    │                    CrossChainOrchestrator                        │
    │  (launcher + router — agents are autonomous once started)       │
    └───────────┬──────────────────────────────────────────────────────┘
                │
    ┌───────────┼───────────────────────────────┐
    │           │                               │
    ▼           ▼                               ▼
  ┌──────────────────┐  ┌───────────────────┐  ┌──────────────────────┐
  │  Knowledge Layer  │  │    Managers        │  │  Chain Specialists   │
  │  ├─ Store (JSON)  │  │  ├─ Throttle      │  │  ├─ Cardano          │
  │  ├─ Graph         │  │  ├─ Embed         │  │  ├─ Bitcoin          │
  │  ├─ Links/Locks   │  │  ├─ Expansion     │  │  ├─ Night            │
  │  ├─ Protocol Facts│  │  ├─ Research      │  │  ├─ Charms           │
  │  ├─ Repo Registry │  │  ├─ Link (Doctor) │  │  ├─ RepoWatcher      │
  │  └─ Expansion Eng │  │  └─ Lock (Healer) │  │  └─ SpellCaster      │
  └──────────────────┘  └───────────────────┘  └──────────────────────┘
"""

from __future__ import annotations

from typing import Any

import structlog

from autono.core.message_bus import MessageBus
from autono.knowledge.graph import KnowledgeGraph
from autono.knowledge.store import KnowledgeStore
from autono.knowledge.expansion import KnowledgeExpansionEngine
from autono.services.blockfrost import BlockfrostClient
from autono.services.scraper import Scraper
from autono.services.wallet_service import WalletService

# Managers
from autono.agents.managers import ALL_MANAGERS

# Chain specialists
from autono.agents.chain_specialists import ALL_CHAIN_SPECIALISTS

log = structlog.get_logger()


class CrossChainOrchestrator:
    """Launcher and router for the cross-chain agent system.

    Integrates with the main Orchestrator's MessageBus to allow
    chain specialists to communicate with the original 13 agents.
    """

    def __init__(self, bus: MessageBus | None = None,
                 knowledge_path: str | None = None,
                 network: str | None = None) -> None:
        # Use existing bus or create new one
        self.bus = bus or MessageBus()

        # Knowledge layer — the brain
        self.store = KnowledgeStore(base_path=knowledge_path)
        self.graph = KnowledgeGraph(store=self.store)

        # Blockfrost client — the eyes (chain data)
        self.blockfrost = BlockfrostClient()

        # Wallet service — the hands
        self.wallet = WalletService(
            network=network or self.blockfrost.network
        )
        self.wallet.set_dependencies(self.store, self.graph)

        # Boot managers
        self.managers: dict[str, Any] = {}
        for manager_cls in ALL_MANAGERS:
            manager = manager_cls()
            self.managers[manager.name] = manager
            self.bus.register(manager)

        # Boot chain specialists
        self.chain_agents: dict[str, Any] = {}
        for agent_cls in ALL_CHAIN_SPECIALISTS:
            agent = agent_cls()
            self.chain_agents[agent.name] = agent
            self.bus.register(agent)

        # Knowledge expansion engine — fills the brain
        self.scraper = Scraper()
        self.expansion = KnowledgeExpansionEngine(
            store=self.store,
            scraper=self.scraper,
            graph=self.graph,
        )

        # Inject dependencies
        self._inject_dependencies()

        log.info("cross_chain.initialized",
                 managers=list(self.managers.keys()),
                 chain_agents=list(self.chain_agents.keys()),
                 knowledge_stats=self.store.stats())

    def _inject_dependencies(self) -> None:
        """Wire up the knowledge layer to all agents that need it."""
        # Managers
        if "EmbedManager" in self.managers:
            self.managers["EmbedManager"].set_store(self.store)
            self.managers["EmbedManager"].set_graph(self.graph)

        if "ExpansionManager" in self.managers:
            self.managers["ExpansionManager"].set_dependencies(
                self.store, self.graph
            )

        if "ResearchManager" in self.managers:
            self.managers["ResearchManager"].set_store(self.store)

        if "LinkManager" in self.managers:
            self.managers["LinkManager"].set_dependencies(
                self.store, self.graph
            )

        if "LockManager" in self.managers:
            self.managers["LockManager"].set_dependencies(
                self.store, self.graph
            )

        # Chain specialists
        for agent in self.chain_agents.values():
            if hasattr(agent, "set_dependencies"):
                agent.set_dependencies(self.store, self.graph)

        # WalletSmith gets the wallet service too
        # (WalletSmith is in the main Orchestrator's agent list, not here,
        #  so it's wired from the main Orchestrator via self.wallet)

    async def start(self) -> None:
        """Launch all managers and chain specialists."""
        import asyncio

        log.info("cross_chain.starting",
                 total_agents=len(self.managers) + len(self.chain_agents))

        tasks = []

        # Start managers first (they set up infrastructure)
        for manager in self.managers.values():
            tasks.append(asyncio.create_task(manager.start()))

        # Then chain specialists
        for agent in self.chain_agents.values():
            tasks.append(asyncio.create_task(agent.start()))

        log.info("cross_chain.all_launched",
                 managers=len(self.managers),
                 chain_agents=len(self.chain_agents))

        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            await self.stop()

    async def stop(self) -> None:
        """Shut down all agents gracefully."""
        for agent in self.chain_agents.values():
            await agent.stop()
        for manager in self.managers.values():
            await manager.stop()
        log.info("cross_chain.stopped")

    # -- Query interface --------------------------------------------------

    def ask(self, question: str, top_k: int = 5) -> dict[str, Any]:
        """Ask a natural language question. Semantic search + lock check.

        This is THE primary interface. Agents ask questions in plain English,
        the graph finds the nearest nodes by embedding similarity, checks
        for locks (instant deterministic answers), and returns either a
        locked answer or gathered context.
        """
        result = self.graph.ask(question, top_k=top_k)
        return result.as_dict()

    def query_knowledge(self, node_id: str) -> dict[str, Any]:
        """Query the knowledge graph for a specific node by ID.

        Returns deterministic answer if locked, or gathered context
        for the agent to reason over.
        """
        result = self.graph.query_node(node_id)
        return result.as_dict()

    def backward_chain(self, target_value: Any) -> dict[str, Any]:
        """Reverse lookup: "I need this result, what paths get me there?" """
        result = self.graph.backward_chain(target_value)
        return result.as_dict()

    def get_bridge_route(self, from_chain: str, to_chain: str) -> dict[str, Any]:
        """Get the optimal bridge route between two chains."""
        if "CharmsAgent" in self.chain_agents:
            agent = self.chain_agents["CharmsAgent"]
            route_key = f"{from_chain}_to_{to_chain}"
            return agent._bridge_routes.get(route_key, {"error": "no_route"})
        return {"error": "charms_agent_not_found"}

    # -- Brain expansion --------------------------------------------------

    def seed_brain(self) -> dict[str, Any]:
        """Seed all 162+ protocol facts into the knowledge graph as Locks.

        This is the first step to 100% brain coverage. Call this on first boot.
        """
        return self.expansion.seed_all_facts()

    def expand_brain(self) -> dict[str, Any]:
        """Run full brain expansion: seed, scrape, link, validate, gap-check."""
        return self.expansion.run_full_expansion()

    def brain_status(self) -> dict[str, Any]:
        """Get brain coverage report — how close to 100%."""
        return self.expansion.get_brain_status()

    # -- Spell interface --------------------------------------------------

    def cast_spell(self, spell_type: str, **kwargs: Any) -> dict[str, Any]:
        """Create and queue a cross-chain spell via SpellCasterAgent.

        Example:
            orchestrator.cast_spell("btc_to_ada",
                inputs=[{"txid": "abc...", "vout": 0}],
                outputs=[{"address": "addr1...", "chain": "cardano"}])
        """
        if "SpellCasterAgent" not in self.chain_agents:
            return {"error": "spell_caster_not_found"}

        # Use template if it exists, otherwise raw spell type
        from autono.agents.chain_specialists.spell_caster import SPELL_TEMPLATES
        if spell_type in SPELL_TEMPLATES:
            payload = {**SPELL_TEMPLATES[spell_type], **kwargs}
        else:
            payload = {"spell_type": spell_type, **kwargs}

        # Synchronous spell creation (bypasses message bus for direct calls)
        caster = self.chain_agents["SpellCasterAgent"]
        import asyncio
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Can't await in sync context — queue it
            return {"status": "queued", "spell_type": spell_type,
                    "message": "Spell queued. Use message bus for async creation."}
        return loop.run_until_complete(caster._on_create_spell(payload))

    def spell_status(self) -> dict[str, Any]:
        """Get status of all active spells."""
        if "SpellCasterAgent" in self.chain_agents:
            return self.chain_agents["SpellCasterAgent"].report()
        return {"error": "spell_caster_not_found"}

    # -- Status -----------------------------------------------------------

    def status(self) -> dict[str, Any]:
        """Get status of the entire cross-chain system."""
        return {
            "knowledge": self.store.stats(),
            "graph_healthy": self.graph.stats().get("graph_healthy", False),
            "managers": {
                name: m.report() for name, m in self.managers.items()
            },
            "chain_agents": {
                name: a.report() for name, a in self.chain_agents.items()
            },
            "throttle": (
                self.managers["ThrottleManager"].report()
                if "ThrottleManager" in self.managers
                else {}
            ),
        }

    def knowledge_stats(self) -> dict[str, Any]:
        """Get knowledge layer statistics."""
        return {
            "store": self.store.stats(),
            "graph": self.graph.stats(),
        }
