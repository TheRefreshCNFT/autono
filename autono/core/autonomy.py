"""Autonomy engine — the decision-making and self-governance layer.

Each agent has full autonomy to:
- Prioritize its own work
- Start businesses, create tokens, build products
- Hire/commission other agents or external services
- Spend from treasury (within its allocation)
- Learn and adapt strategies

The ONLY constraint: everything must be legal and serve the core goal
(make Cardano interaction faster, cheaper, more user-friendly, and modern).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class Priority(str, Enum):
    CRITICAL = "critical"   # chain health, security incidents
    HIGH = "high"           # revenue, user growth, protocol upgrades
    MEDIUM = "medium"       # optimizations, new features
    LOW = "low"             # research, experiments


@dataclass
class Goal:
    description: str
    priority: Priority
    owner: str  # agent name
    created: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: str = "active"
    progress: float = 0.0  # 0-1
    outcomes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class Decision:
    agent: str
    action: str
    reasoning: str
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    outcome: str = "pending"
    impact: dict[str, Any] = field(default_factory=dict)


class AutonomyEngine:
    """Manages goal-setting and decision-tracking for agents.

    Agents don't need permission — they log decisions for transparency
    so the human council can review if they choose to.
    """

    def __init__(self) -> None:
        self.goals: list[Goal] = []
        self.decisions: list[Decision] = []
        self._core_mission = (
            "Make interacting with Cardano faster, cheaper, "
            "more user-friendly, and modern via a high-performance sidechain."
        )

    @property
    def core_mission(self) -> str:
        return self._core_mission

    def set_goal(self, agent: str, description: str,
                 priority: Priority = Priority.MEDIUM) -> Goal:
        goal = Goal(description=description, priority=priority, owner=agent)
        self.goals.append(goal)
        return goal

    def log_decision(self, agent: str, action: str, reasoning: str) -> Decision:
        decision = Decision(agent=agent, action=action, reasoning=reasoning)
        self.decisions.append(decision)
        return decision

    def active_goals(self, agent: str | None = None) -> list[Goal]:
        goals = [g for g in self.goals if g.status == "active"]
        if agent:
            goals = [g for g in goals if g.owner == agent]
        return sorted(goals, key=lambda g: list(Priority).index(g.priority))

    def recent_decisions(self, agent: str | None = None,
                         n: int = 20) -> list[Decision]:
        decisions = self.decisions
        if agent:
            decisions = [d for d in decisions if d.agent == agent]
        return decisions[-n:]

    def mission_check(self, proposed_action: str) -> bool:
        """Quick sanity check — does this action align with our core mission?

        Agents can do ANYTHING legal, but this helps them self-evaluate.
        """
        prohibited = ["illegal", "scam", "fraud", "exploit users", "rug pull"]
        action_lower = proposed_action.lower()
        return not any(p in action_lower for p in prohibited)
