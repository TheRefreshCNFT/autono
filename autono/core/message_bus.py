"""Central message bus that routes messages between agents.

Agents communicate freely — no permissions required.  The bus just delivers.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from autono.core.agent_base import AutonomousAgent, Message

log = structlog.get_logger()


class MessageBus:
    """Routes messages between all agents in the swarm."""

    def __init__(self) -> None:
        self._agents: dict[str, AutonomousAgent] = {}
        self._running = False

    def register(self, agent: AutonomousAgent) -> None:
        self._agents[agent.name] = agent
        agent._peers = self._agents
        log.info("bus.registered", agent=agent.name)

    async def start(self) -> None:
        self._running = True
        log.info("bus.started", agent_count=len(self._agents))
        while self._running:
            for agent in list(self._agents.values()):
                await self._drain_outbox(agent)
            await asyncio.sleep(0.1)

    async def stop(self) -> None:
        self._running = False

    async def _drain_outbox(self, agent: AutonomousAgent) -> None:
        while not agent.outbox.empty():
            try:
                msg = agent.outbox.get_nowait()
                await self._deliver(msg)
            except asyncio.QueueEmpty:
                break

    async def _deliver(self, msg: Message) -> None:
        if msg.recipient == "broadcast":
            for name, agent in self._agents.items():
                if name != msg.sender:
                    await agent.inbox.put(msg)
            log.debug("bus.broadcast", sender=msg.sender, kind=msg.kind)
        elif msg.recipient in self._agents:
            await self._agents[msg.recipient].inbox.put(msg)
            log.debug("bus.delivered", sender=msg.sender, to=msg.recipient)
        else:
            log.warning("bus.unknown_recipient", recipient=msg.recipient)

    def get_agent(self, name: str) -> AutonomousAgent | None:
        return self._agents.get(name)

    def all_reports(self) -> list[dict]:
        return [a.report() for a in self._agents.values()]
