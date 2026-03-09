"""Autonomy engine — the decision-making and self-governance layer.

Each agent has full autonomy to:
- Prioritize its own work
- Start businesses, create tokens, build products
- Hire/commission other agents or external services
- Spend from treasury (within its allocation)
- Learn and adapt strategies

The ONLY constraint: everything must be legal and serve the core mission.

CORE MISSION
============
Autono is a sidechain that runs alongside Cardano to make crypto accessible,
affordable, and easy to use. Every agent, every transaction, every feature
exists to serve this:

1. CHEAPER THAN EXISTING WALLETS
   Sending CNTs (Cardano Native Tokens) through autono must cost less than
   using Vespr, Eternl, Lace, or any current Cardano wallet. If we're not
   cheaper, we have no reason to exist. This means:
   - Batching transactions to amortize fees
   - UTXO selection that minimizes change outputs
   - Off-chain validation where possible (ZK proofs)
   - Sidechain execution with Cardano settlement
   - Smart fee estimation that finds the cheapest valid path

2. ACCESSIBLE TO EVERYONE
   Crypto is hard. We make it easy. No seed phrases shown to users, no
   hex addresses, no manual UTXO management. The agents handle all of that.
   Users say "send 50 ADA to Alice" and it happens — cheaply, correctly,
   with a receipt.

3. CROSS-CHAIN AS A FEATURE, NOT A PRODUCT
   Charms spells, BitcoinOS bridges, Night Chain privacy — these are tools
   in the toolbox, not the point. The point is: a user shouldn't need to
   know which chain they're on. The agents route to the cheapest, fastest
   path automatically.

4. RUN LIKE A REAL CHAIN
   This is production infrastructure. Agents monitor official repos, test
   betas ahead of time, keep protocol knowledge current, and operate 24/7.
   No downtime, no stale data, no surprises.

Every decision an agent makes should pass this test:
  "Does this make crypto cheaper or easier for the end user?"
If the answer is no, don't do it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


# =============================================================================
# Core Mission — every agent must know this by heart
# =============================================================================

CORE_MISSION = (
    "Make crypto accessible, affordable, and easy to use. "
    "Autono runs alongside Cardano as a sidechain — every transaction "
    "through autono must be cheaper than using Vespr, Eternl, or any "
    "existing Cardano wallet. If we're not cheaper, we have no reason to exist."
)

MISSION_PRINCIPLES = {
    "cost_first": (
        "Every transaction must be optimized for minimum cost. "
        "Batch where possible, select UTXOs to minimize change outputs, "
        "use off-chain validation (ZK proofs) where valid, and always "
        "pick the cheapest path that's still correct and secure."
    ),
    "accessibility": (
        "Users should never see seed phrases, hex addresses, or raw UTXOs. "
        "The agents handle all complexity. A user says 'send 50 ADA to Alice' "
        "and it happens — cheaply, correctly, with a receipt."
    ),
    "chain_agnostic": (
        "Cross-chain is a feature, not a product. Users don't need to know "
        "which chain they're on. Agents route to the cheapest, fastest path "
        "automatically — Cardano, Bitcoin, Night Chain, whatever works."
    ),
    "production_grade": (
        "This is real infrastructure that runs 24/7. Monitor official repos, "
        "test betas ahead of time, keep protocol knowledge current. "
        "No downtime, no stale data, no surprises."
    ),
}

# The ONE question every agent asks before acting
MISSION_CHECK_QUESTION = "Does this make crypto cheaper or easier for the end user?"


# =============================================================================
# Cost optimization targets — concrete numbers agents measure against
# =============================================================================

COST_TARGETS = {
    "cardano_simple_transfer": {
        "current_wallet_fee_lovelace": 200_000,  # ~0.20 ADA typical wallet fee
        "l1_target_lovelace": 170_000,            # ~0.17 ADA via optimized UTXO selection
        "sidechain_target_lovelace": 50_000,      # ~0.05 ADA — sidechain is much cheaper
        "strategy": "optimal_utxo_selection",
        "user_chooses": True,  # user picks L1 vs sidechain based on needs
    },
    "cardano_cnt_transfer": {
        "current_wallet_fee_lovelace": 250_000,  # ~0.25 ADA for token transfers
        "l1_target_lovelace": 180_000,            # ~0.18 ADA via batching + minimal change
        "sidechain_target_lovelace": 60_000,      # ~0.06 ADA on sidechain
        "strategy": "batch_and_minimize_change",
        "user_chooses": True,
    },
    "cardano_nft_mint": {
        "current_wallet_fee_lovelace": 400_000,  # ~0.40 ADA typical mint
        "l1_target_lovelace": 300_000,            # ~0.30 ADA via reference scripts
        "sidechain_target_lovelace": 100_000,     # ~0.10 ADA on sidechain
        "strategy": "reference_scripts_and_batching",
        "user_chooses": True,
    },
    "cross_chain_spell": {
        "strategy": "sidechain_execution_with_settlement",
        "description": "Execute spell logic on sidechain, only settle final state on L1",
        "user_chooses": True,
    },
}


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
    cost_impact: str = ""  # "cheaper", "same", "more_expensive"
    user_impact: str = ""  # "easier", "same", "harder"
    impact: dict[str, Any] = field(default_factory=dict)


class AutonomyEngine:
    """Manages goal-setting and decision-tracking for agents.

    Every decision is logged with cost and user impact assessment.
    Agents don't need permission — they log decisions for transparency
    so the human council can review if they choose to.
    """

    def __init__(self) -> None:
        self.goals: list[Goal] = []
        self.decisions: list[Decision] = []

    @property
    def core_mission(self) -> str:
        return CORE_MISSION

    @property
    def principles(self) -> dict[str, str]:
        return MISSION_PRINCIPLES

    @property
    def cost_targets(self) -> dict[str, dict]:
        return COST_TARGETS

    def set_goal(self, agent: str, description: str,
                 priority: Priority = Priority.MEDIUM) -> Goal:
        goal = Goal(description=description, priority=priority, owner=agent)
        self.goals.append(goal)
        return goal

    def log_decision(self, agent: str, action: str, reasoning: str,
                     cost_impact: str = "", user_impact: str = "") -> Decision:
        decision = Decision(
            agent=agent, action=action, reasoning=reasoning,
            cost_impact=cost_impact, user_impact=user_impact,
        )
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
        """Does this action make crypto cheaper or easier for the end user?

        Agents can do ANYTHING legal, but this is the litmus test.
        """
        prohibited = ["illegal", "scam", "fraud", "exploit users", "rug pull"]
        action_lower = proposed_action.lower()
        if any(p in action_lower for p in prohibited):
            return False
        return True

    def cost_check(self, operation: str, estimated_fee: int,
                   chain: str = "sidechain") -> dict[str, Any]:
        """Check if our fee beats the current wallet standard.

        Args:
            chain: "l1" for Cardano mainchain, "sidechain" for autono sidechain.
                   Sidechain targets are lower because that's the whole point.

        Returns comparison against known wallet fees.
        """
        target = COST_TARGETS.get(operation)
        if not target:
            return {"operation": operation, "has_target": False}

        current = target.get("current_wallet_fee_lovelace", 0)

        # Pick the right target based on which chain the user chose
        if chain == "sidechain":
            our_target = target.get("sidechain_target_lovelace",
                                    target.get("l1_target_lovelace", 0))
        else:
            our_target = target.get("l1_target_lovelace", 0)

        return {
            "operation": operation,
            "has_target": True,
            "chain": chain,
            "estimated_fee": estimated_fee,
            "current_wallet_fee": current,
            "our_target": our_target,
            "beats_wallets": estimated_fee < current,
            "meets_target": estimated_fee <= our_target,
            "savings_vs_wallets": current - estimated_fee if current else 0,
            "strategy": target.get("strategy", ""),
            "user_chooses": target.get("user_chooses", False),
        }
