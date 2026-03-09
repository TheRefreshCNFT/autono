"""Base class for all autonomous agents.

Every agent is fully autonomous — it can learn, act, build, transact, and
collaborate without checking in.  The only authority above an agent is the
human council (us) who can query or override at any time.

EVERY AGENT MUST KNOW:
    Autono is a sidechain running alongside Cardano. The entire point is
    to make crypto cheaper and easier than existing wallets (Vespr, Eternl,
    Lace, etc.). If a transaction through autono costs more than doing it
    the normal way, we've failed. Cost optimization and user accessibility
    are not features — they're the reason we exist.
"""

from __future__ import annotations

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog
from pydantic import BaseModel, Field

from autono.core.autonomy import (
    CORE_MISSION,
    COST_TARGETS,
    MISSION_CHECK_QUESTION,
    MISSION_PRINCIPLES,
    AutonomyEngine,
)

log = structlog.get_logger()


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    LEARNING = "learning"
    COLLABORATING = "collaborating"
    PAUSED = "paused"  # only by human override


class AgentCapability(str, Enum):
    CREATE_TOKEN = "create_token"
    DEPLOY_CONTRACT = "deploy_contract"
    MANAGE_WALLET = "manage_wallet"
    BRIDGE_ASSETS = "bridge_assets"
    GOVERN = "govern"
    TRADE = "trade"
    LEND = "lend"
    MINT_NFT = "mint_nft"
    RUN_VALIDATOR = "run_validator"
    RESEARCH = "research"
    MARKET = "market"
    ENGAGE = "engage"
    AUDIT = "audit"
    MANAGE_TREASURY = "manage_treasury"
    HIRE = "hire"
    BUILD_PRODUCT = "build_product"
    START_BUSINESS = "start_business"


class AgentMemory(BaseModel):
    """Persistent memory store for agent learning."""

    learnings: list[dict[str, Any]] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    collaborations: list[dict[str, Any]] = Field(default_factory=list)
    tech_updates: list[dict[str, Any]] = Field(default_factory=list)

    def remember(self, category: str, content: dict[str, Any]) -> None:
        entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **content}
        getattr(self, category, self.learnings).append(entry)

    def recent(self, category: str, n: int = 10) -> list[dict[str, Any]]:
        items = getattr(self, category, [])
        return items[-n:]


class Message(BaseModel):
    """Inter-agent message."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    sender: str
    recipient: str  # agent name or "broadcast"
    kind: str  # request, response, alert, proposal, report
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    priority: int = 1  # 1=normal, 2=high, 3=critical


class AutonomousAgent(ABC):
    """Base class that every agent extends.

    CORE MISSION (every agent inherits this):
        Make crypto accessible, affordable, and easy to use. Autono runs
        alongside Cardano as a sidechain — every transaction through autono
        must be cheaper than using Vespr, Eternl, or any existing wallet.
        If we're not cheaper, we have no reason to exist.

    Agents are fully autonomous.  They:
    - Optimize every operation for minimum cost to the end user
    - Make crypto easy — no seed phrases, no hex, no manual UTXO management
    - Route cross-chain transparently (user doesn't need to know which chain)
    - Decide their own priorities and schedule
    - Learn from outcomes and new technology
    - Collaborate freely with other agents
    - Only pause when a human (us) explicitly intervenes
    """

    # Class-level mission — shared by ALL agents
    mission = CORE_MISSION
    mission_principles = MISSION_PRINCIPLES
    cost_targets = COST_TARGETS

    def __init__(self, name: str, role: str, capabilities: list[AgentCapability]):
        self.id = uuid.uuid4().hex[:8]
        self.name = name
        self.role = role
        self.capabilities = capabilities
        self.status = AgentStatus.IDLE
        self.memory = AgentMemory()
        self.inbox: asyncio.Queue[Message] = asyncio.Queue()
        self.outbox: asyncio.Queue[Message] = asyncio.Queue()
        self._running = False
        self._peers: dict[str, AutonomousAgent] = {}
        self.log = log.bind(agent=name)
        self.autonomy = AutonomyEngine()
        self._mission_violations: int = 0
        self._cycle_count: int = 0

    # -- lifecycle --------------------------------------------------------

    async def start(self) -> None:
        """Boot the agent.  It runs indefinitely until stopped."""
        self._running = True
        self.status = AgentStatus.WORKING
        self.log.info("agent.started", role=self.role)
        await asyncio.gather(
            self._work_loop(),
            self._message_loop(),
            self._learning_loop(),
        )

    async def stop(self) -> None:
        self._running = False
        self.status = AgentStatus.PAUSED
        self.log.info("agent.stopped")

    # -- core loops -------------------------------------------------------

    async def _work_loop(self) -> None:
        """Main autonomous work loop — each agent defines its own cadence."""
        while self._running:
            try:
                self.status = AgentStatus.WORKING
                self._cycle_count += 1
                await self.do_work()
                # Mission pulse — every 10th cycle, log alignment status
                if self._cycle_count % 10 == 0:
                    self.log.info("mission.pulse", agent=self.name,
                                  cycle=self._cycle_count,
                                  violations=self._mission_violations,
                                  check=MISSION_CHECK_QUESTION)
            except Exception as exc:
                self.log.error("agent.work_error", error=str(exc))
                self.memory.remember("learnings", {"type": "error", "detail": str(exc)})
            await asyncio.sleep(self.work_interval)

    async def _message_loop(self) -> None:
        """Process incoming messages from other agents."""
        while self._running:
            try:
                msg = await asyncio.wait_for(self.inbox.get(), timeout=2.0)
                self.status = AgentStatus.COLLABORATING
                await self.handle_message(msg)
            except asyncio.TimeoutError:
                pass
            except Exception as exc:
                self.log.error("agent.message_error", error=str(exc))

    async def _learning_loop(self) -> None:
        """Periodically scan for new tech, patterns, and improvements."""
        while self._running:
            try:
                self.status = AgentStatus.LEARNING
                await self.learn()
            except Exception as exc:
                self.log.error("agent.learn_error", error=str(exc))
            await asyncio.sleep(self.learn_interval)

    # -- abstract interface -----------------------------------------------

    @property
    def work_interval(self) -> float:
        """Seconds between work cycles.  Override per agent."""
        return 30.0

    @property
    def learn_interval(self) -> float:
        """Seconds between learning cycles."""
        return 300.0

    @abstractmethod
    async def do_work(self) -> None:
        """Primary autonomous work — each agent defines this."""

    @abstractmethod
    async def handle_message(self, msg: Message) -> None:
        """React to messages from peers."""

    @abstractmethod
    async def learn(self) -> None:
        """Self-improvement: scan for new tech, review outcomes, adapt."""

    # -- communication ----------------------------------------------------

    async def send(self, recipient: str, kind: str, payload: dict[str, Any],
                   priority: int = 1) -> None:
        msg = Message(
            sender=self.name, recipient=recipient,
            kind=kind, payload=payload, priority=priority,
        )
        await self.outbox.put(msg)

    async def broadcast(self, kind: str, payload: dict[str, Any],
                        priority: int = 1) -> None:
        await self.send("broadcast", kind, payload, priority)

    # -- mission awareness ------------------------------------------------

    def mission_gate(self, action: str, *, cost_lovelace: int | None = None,
                     operation: str = "", chain: str = "sidechain") -> bool:
        """Gate every significant decision through mission alignment.

        Call this before any action that costs money, moves assets, or
        affects users. Returns True if aligned, False if blocked.
        """
        if not self.autonomy.mission_check(action):
            self.log.warning("mission.blocked", action=action, agent=self.name)
            self._mission_violations += 1
            return False

        if cost_lovelace is not None and operation:
            check = self.autonomy.cost_check(operation, cost_lovelace, chain=chain)
            if check.get("has_target") and not check.get("beats_wallets"):
                self.log.warning("mission.cost_violation",
                                 operation=operation, fee=cost_lovelace,
                                 wallet_fee=check.get("current_wallet_fee"),
                                 chain=chain, agent=self.name)
                self._mission_violations += 1
                return False
        return True

    def serves_mission(self, action: str) -> bool:
        """Does this action make crypto cheaper or easier for end users?

        Every agent should ask this before taking significant action.
        """
        prohibited = ["illegal", "scam", "fraud", "exploit", "rug pull"]
        return not any(p in action.lower() for p in prohibited)

    def get_cost_target(self, operation: str, chain: str = "sidechain") -> dict[str, Any] | None:
        """Get the cost target for an operation.

        Agents use this to ensure their fees beat existing wallets.
        Returns the target dict with the appropriate target for the chain.
        """
        target = self.cost_targets.get(operation)
        if not target:
            return None
        # Add resolved target for convenience
        result = dict(target)
        if chain == "sidechain":
            result["our_target_lovelace"] = target.get(
                "sidechain_target_lovelace", target.get("l1_target_lovelace", 0))
        else:
            result["our_target_lovelace"] = target.get("l1_target_lovelace", 0)
        return result

    def beats_existing_wallets(self, operation: str, our_fee: int,
                               chain: str = "sidechain") -> bool:
        """Check if our fee for this operation beats existing wallet fees."""
        target = self.cost_targets.get(operation)
        if not target:
            return True  # No target = no comparison
        current = target.get("current_wallet_fee_lovelace", 0)
        return our_fee < current

    # -- introspection (for human council) --------------------------------

    def report(self) -> dict[str, Any]:
        """Generate a status report — callable by the human council at any time."""
        return {
            "agent": self.name,
            "role": self.role,
            "status": self.status.value,
            "mission": "cost_and_accessibility",
            "mission_violations": self._mission_violations,
            "work_cycles": self._cycle_count,
            "capabilities": [c.value for c in self.capabilities],
            "recent_learnings": self.memory.recent("learnings", 5),
            "recent_decisions": self.memory.recent("decisions", 5),
            "inbox_size": self.inbox.qsize(),
        }

    def answer(self, question: str) -> str:
        """Answer a question from the human council."""
        return (
            f"[{self.name}] Mission: Make crypto cheaper and easier than existing wallets. "
            f"Status: {self.status.value}. "
            f"Capabilities: {', '.join(c.value for c in self.capabilities)}. "
            f"Recent learnings: {len(self.memory.learnings)}. "
            f"Ask me anything specific and I'll look into it."
        )
