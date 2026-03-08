"""Orchestrator — boots and manages all 13 agents.

The orchestrator is NOT a boss — it's a launcher and router.
Agents are autonomous once started.  The orchestrator just:
1. Instantiates all 13 agents
2. Connects them via the message bus
3. Starts their async loops
4. Provides the Human Council interface
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

log = structlog.get_logger()


class Orchestrator:
    """Launch pad for the 13 autonomous agents and sidechain infrastructure."""

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

        # Agents — instantiated but not yet started
        self.agents = {}
        for agent_cls in ALL_AGENTS:
            agent = agent_cls()
            self.agents[agent.name] = agent
            self.bus.register(agent)

        log.info("orchestrator.initialized", agent_count=len(self.agents))

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
