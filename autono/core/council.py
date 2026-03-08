"""Human Council interface — how we (the humans) interact with agents.

Agents run autonomously, but they MUST answer when we reach out.
This module provides the interface for querying, directing, and
overriding agents when needed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog

from autono.core.message_bus import MessageBus

log = structlog.get_logger()


class HumanCouncil:
    """The human oversight layer.

    - Agents don't need to check in
    - But they MUST respond when we reach out
    - We can query status, override decisions, set directives
    """

    def __init__(self, bus: MessageBus) -> None:
        self.bus = bus
        self.directives: list[dict[str, Any]] = []
        self.audit_log: list[dict[str, Any]] = []

    def query_agent(self, agent_name: str, question: str) -> str:
        """Ask any agent a question — they must answer."""
        agent = self.bus.get_agent(agent_name)
        if not agent:
            return f"Agent '{agent_name}' not found."
        answer = agent.answer(question)
        self._log_interaction("query", agent_name, question, answer)
        return answer

    def get_all_reports(self) -> list[dict]:
        """Pull status reports from every agent."""
        reports = self.bus.all_reports()
        self._log_interaction("bulk_report", "all", "status check", f"{len(reports)} reports")
        return reports

    def issue_directive(self, agent_name: str, directive: str) -> None:
        """Issue a directive to an agent.  They must comply."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "target": agent_name,
            "directive": directive,
        }
        self.directives.append(entry)
        self._log_interaction("directive", agent_name, directive, "issued")
        log.info("council.directive", target=agent_name, directive=directive)

    def pause_agent(self, agent_name: str) -> str:
        agent = self.bus.get_agent(agent_name)
        if not agent:
            return f"Agent '{agent_name}' not found."
        agent._running = False
        self._log_interaction("pause", agent_name, "pause requested", "paused")
        return f"{agent_name} paused."

    def resume_agent(self, agent_name: str) -> str:
        agent = self.bus.get_agent(agent_name)
        if not agent:
            return f"Agent '{agent_name}' not found."
        # Re-starting requires the orchestrator to re-launch the coroutine
        self._log_interaction("resume", agent_name, "resume requested", "queued")
        return f"{agent_name} resume queued — orchestrator will restart."

    def _log_interaction(self, kind: str, agent: str,
                         query: str, response: str) -> None:
        self.audit_log.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "kind": kind,
            "agent": agent,
            "query": query,
            "response": response,
        })
