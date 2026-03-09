"""Orchestrator — boots and manages all agents.

The orchestrator is NOT a boss — it's a launcher and router.
Agents are autonomous once started.  The orchestrator just:
1. Instantiates all 13 core agents + chain specialists + managers
2. Connects them via the message bus
3. Starts their async loops
4. Provides the Human Council interface
5. Initializes the Links & Locks knowledge layer
"""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from autono.agents import ALL_AGENTS
from autono.core.autonomy import AutonomyEngine
from autono.core.council import HumanCouncil
from autono.core.message_bus import MessageBus
from autono.sidechain.block import BlockChain
from autono.sidechain.bridge import CardanoBridge
from autono.sidechain.consensus import OuroborosTurbo
from autono.sidechain.state import StateManager

# Cross-chain system
from autono.agents.chain_specialists.cross_chain_orchestrator import CrossChainOrchestrator

log = structlog.get_logger()


class Orchestrator:
    """Launch pad for all autonomous agents, sidechain, and cross-chain infrastructure."""

    def __init__(self) -> None:
        # Core infrastructure
        self.bus = MessageBus()
        self.autonomy = AutonomyEngine()
        self.council = HumanCouncil(self.bus)

        # Sidechain components
        self.consensus = OuroborosTurbo()
        self.blockchain = BlockChain()
        self.bridge = CardanoBridge()
        self.state = StateManager()

        # Core agents — the original 13
        self.agents = {}
        for agent_cls in ALL_AGENTS:
            agent = agent_cls()
            self.agents[agent.name] = agent
            self.bus.register(agent)

        # Cross-chain system — chain specialists + managers + knowledge layer
        # Shares the same MessageBus so all agents can communicate
        self.cross_chain = CrossChainOrchestrator(bus=self.bus)

        # Wire WalletSmith to the wallet service
        if "WalletSmith" in self.agents:
            self.agents["WalletSmith"].set_dependencies(
                self.cross_chain.store,
                self.cross_chain.graph,
                self.cross_chain.wallet,
            )

        # Merge all agents into one registry for unified status/query
        self.agents.update(self.cross_chain.managers)
        self.agents.update(self.cross_chain.chain_agents)

        log.info("orchestrator.initialized",
                 core_agents=len(ALL_AGENTS),
                 managers=len(self.cross_chain.managers),
                 chain_agents=len(self.cross_chain.chain_agents),
                 total=len(self.agents))

    async def start(self) -> None:
        """Launch everything — agents run autonomously from here."""
        log.info("orchestrator.starting", agents=list(self.agents.keys()))

        # Set initial goals for the autonomy engine
        self._set_founding_goals()

        # Start message bus + all agents concurrently
        tasks = [asyncio.create_task(self.bus.start())]
        for agent in self.agents.values():
            tasks.append(asyncio.create_task(agent.start()))

        log.info("orchestrator.all_agents_launched",
                 count=len(self.agents),
                 mission=self.autonomy.core_mission)

        # Run until stopped
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            log.info("orchestrator.shutting_down")
            await self.stop()

    async def stop(self) -> None:
        for agent in self.agents.values():
            await agent.stop()
        await self.bus.stop()
        log.info("orchestrator.stopped")

    def _set_founding_goals(self) -> None:
        """Set the founding mission goals for each agent."""
        goals = {
            # Original 13
            "ChainArchitect": "Build and optimize sidechain consensus for 1000+ TPS with sub-second finality",
            "BridgeKeeper": "Operate secure, fast bridge between Cardano and sidechain",
            "TokenForge": "Design and launch the AUTONO native token with sustainable tokenomics",
            "WalletSmith": "Create the most user-friendly crypto wallet — simpler than Venmo",
            "DeFiEngine": "Build DEX, lending, and yield products with deep liquidity",
            "CreatorStudio": "Empower creators with no-code NFT tools and fair royalties",
            "DevForge": "Build world-class SDKs and grow the developer ecosystem",
            "SentinelGuard": "Maintain 100% security record — zero exploits, zero downtime",
            "GovernanceOracle": "Implement fair, efficient on-chain governance",
            "GrowthCatalyst": "Drive adoption to 1M+ active users",
            "InfraOps": "Achieve 99.99% uptime with global node distribution",
            "ResearchLab": "Stay at the frontier — integrate latest tech within months",
            "TreasuryVault": "Ensure financial sustainability for 10+ years",
            # Managers
            "ThrottleManager": "Keep system usable on all hardware — never exceed 85% resources",
            "EmbedManager": "Validate knowledge currency — no stale facts in the system",
            "ExpansionManager": "Grow and prune the knowledge graph — no ghost links",
            "ResearchManager": "Continuously research and document new protocol knowledge",
            "LinkManager": "Stitch cross-domain shortcuts — the Doctor of the knowledge graph",
            "LockManager": "Seal deterministic facts — the Healer that makes inference unnecessary",
            # Chain specialists
            "CardanoChainAgent": "Master Cardano protocol — eUTXO, Plutus, CIPs, Opshin, Helios",
            "BitcoinChainAgent": "Master Bitcoin protocol — UTXO, BIPs, Taproot, Charms integration",
            "NightChainAgent": "Secure encrypted vault — seed phrases, knowledge graph persistence",
            "CharmsAgent": "Bridge Cardano and Bitcoin — Charms spells, BitcoinOS, ZK proofs",
        }
        for agent_name, goal in goals.items():
            self.autonomy.set_goal(agent_name, goal)

    # -- Human Council shortcuts ------------------------------------------

    def ask(self, agent_name: str, question: str) -> str:
        """Ask any agent a question.  They must answer."""
        return self.council.query_agent(agent_name, question)

    def status(self) -> list[dict[str, Any]]:
        """Get status reports from all agents."""
        return self.council.get_all_reports()

    def direct(self, agent_name: str, directive: str) -> None:
        """Issue a directive to an agent."""
        self.council.issue_directive(agent_name, directive)

    def chain_status(self) -> dict[str, Any]:
        """Get sidechain infrastructure status."""
        return {
            "consensus": self.consensus.status(),
            "blockchain": self.blockchain.stats(),
            "bridge": self.bridge.status(),
            "state": self.state.stats(),
        }

    def cross_chain_status(self) -> dict[str, Any]:
        """Get cross-chain system status (managers, chain agents, knowledge)."""
        return self.cross_chain.status()

    def knowledge_status(self) -> dict[str, Any]:
        """Get knowledge layer statistics (nodes, links, locks, mlocks)."""
        return self.cross_chain.knowledge_stats()

    def ask_knowledge(self, question: str) -> dict[str, Any]:
        """Ask the knowledge graph a natural language question.

        Semantic search → lock check → instant answer or context.
        This is the primary interface for the Links & Locks system.
        """
        return self.cross_chain.ask(question)

    def query_knowledge(self, node_id: str) -> dict[str, Any]:
        """Query the knowledge graph by node ID — returns locked answer or context."""
        return self.cross_chain.query_knowledge(node_id)

    def get_bridge_route(self, from_chain: str, to_chain: str) -> dict[str, Any]:
        """Get optimal cross-chain bridge route."""
        return self.cross_chain.get_bridge_route(from_chain, to_chain)

    # -- Wallet shortcuts ----------------------------------------------------

    def create_wallet(self, chains: list[str] | None = None) -> dict[str, Any]:
        """Create a new multi-chain wallet via WalletService."""
        return self.cross_chain.wallet.create_wallet(chains=chains)

    def validate_address(self, address: str, chain: str = "") -> dict[str, Any]:
        """Validate an address (auto-detects chain if not specified)."""
        if chain:
            return self.cross_chain.wallet.validate_address(address, chain)
        return self.cross_chain.wallet.identify_address(address)

    def wallet_status(self) -> dict[str, Any]:
        """Get wallet service status."""
        return self.cross_chain.wallet.stats()
