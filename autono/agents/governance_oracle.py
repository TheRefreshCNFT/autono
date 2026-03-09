"""Agent 9: GovernanceOracle — CIP-1694 on-chain governance and voting.

Implements Cardano Voltaire-style governance for the Autono sidechain:
- Three governance bodies: DReps, SPOs, Constitutional Committee
- Weighted stake-based voting with quorum and threshold checks
- Full proposal lifecycle: DRAFT -> SUBMITTED -> VOTING -> TALLYING -> APPROVED/REJECTED -> EXECUTING -> EXECUTED/FAILED
- Treasury spend validation and execution
- Governance health scoring (0-100)
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ProposalState(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    VOTING = "voting"
    TALLYING = "tallying"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    EXECUTED = "executed"
    FAILED = "failed"


class ProposalType(str, Enum):
    PARAMETER_CHANGE = "parameter_change"
    TREASURY_SPEND = "treasury_spend"
    PROTOCOL_UPGRADE = "protocol_upgrade"
    POLICY_CHANGE = "policy_change"
    INFO_ACTION = "info_action"


class VoteChoice(str, Enum):
    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


class GovBody(str, Enum):
    DREP = "drep"
    SPO = "spo"
    CC = "cc"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DRep:
    id: str
    name: str
    own_stake: int  # lovelace
    delegated_stake: int = 0  # accumulated from delegators
    registered_epoch: int = 0
    active: bool = True


@dataclass
class CCMember:
    id: str
    name: str
    term_start_epoch: int
    term_length_epochs: int = 36  # ~6 months at 5-day epochs
    active: bool = True

    def is_expired(self, current_epoch: int) -> bool:
        return current_epoch >= self.term_start_epoch + self.term_length_epochs


@dataclass
class SPO:
    id: str
    name: str
    pledge: int  # lovelace — their voting power
    active: bool = True


@dataclass
class Vote:
    voter_id: str
    body: GovBody
    choice: VoteChoice
    stake_power: int  # weighted voting power at time of vote
    epoch_cast: int


@dataclass
class Proposal:
    id: str
    title: str
    description: str
    proposer: str
    proposal_type: ProposalType
    state: ProposalState = ProposalState.DRAFT
    deposit: int = 0
    epoch_submitted: int = 0
    voting_deadline_epoch: int = 0
    execution_delay_epochs: int = 2
    votes: list[Vote] = field(default_factory=list)
    tally_result: dict[str, Any] = field(default_factory=dict)
    execution_result: str = ""
    # For treasury_spend proposals
    treasury_amount: int = 0
    treasury_recipient: str = ""
    # Timestamps for history
    created_at: float = field(default_factory=time.time)
    resolved_at: float = 0.0


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Which governance bodies must approve each proposal type
REQUIRED_BODIES: dict[ProposalType, list[GovBody]] = {
    ProposalType.TREASURY_SPEND: [GovBody.DREP, GovBody.CC],
    ProposalType.PARAMETER_CHANGE: [GovBody.DREP, GovBody.SPO, GovBody.CC],
    ProposalType.PROTOCOL_UPGRADE: [GovBody.DREP, GovBody.SPO, GovBody.CC],
    ProposalType.POLICY_CHANGE: [GovBody.DREP, GovBody.CC],
    ProposalType.INFO_ACTION: [GovBody.DREP],
}

# Approval thresholds (% of non-abstain votes that must be YES)
APPROVAL_THRESHOLDS: dict[ProposalType, float] = {
    ProposalType.INFO_ACTION: 50.0,
    ProposalType.TREASURY_SPEND: 60.0,
    ProposalType.PARAMETER_CHANGE: 67.0,
    ProposalType.PROTOCOL_UPGRADE: 75.0,
    ProposalType.POLICY_CHANGE: 60.0,
}

DEFAULT_QUORUM_PCT = 10.0  # minimum % of total active stake that must participate
DEFAULT_VOTING_PERIOD = 5  # epochs
DEFAULT_PROPOSAL_DEPOSIT = 1000_000_000  # 1000 AUTO in lovelace
DEFAULT_TREASURY_BALANCE = 100_000_000_000_000  # 100M AUTO
MAX_TREASURY_SPEND_PCT = 10.0  # max % of treasury spendable per epoch


# ---------------------------------------------------------------------------
# GovernanceOracle
# ---------------------------------------------------------------------------

class GovernanceOracle(AutonomousAgent):
    def __init__(self) -> None:
        super().__init__(
            name="GovernanceOracle",
            role="On-chain governance — CIP-1694 proposals, weighted voting, protocol decisions",
            capabilities=[
                AgentCapability.GOVERN,
                AgentCapability.DEPLOY_CONTRACT,
                AgentCapability.BUILD_PRODUCT,
                AgentCapability.RESEARCH,
            ],
        )
        # --- Governance state ---
        self.current_epoch: int = 0
        self.proposals: dict[str, Proposal] = {}  # id -> Proposal
        self.dreps: dict[str, DRep] = {}  # id -> DRep
        self.spos: dict[str, SPO] = {}  # id -> SPO
        self.cc_members: dict[str, CCMember] = {}  # id -> CCMember
        # delegator_id -> drep_id mapping
        self.delegations: dict[str, str] = {}
        # delegator_id -> stake amount
        self.delegator_stakes: dict[str, int] = {}
        # Treasury
        self.treasury_balance: int = DEFAULT_TREASURY_BALANCE
        self.treasury_spent_this_epoch: int = 0
        # Config
        self.quorum_pct: float = DEFAULT_QUORUM_PCT
        self.voting_period_epochs: int = DEFAULT_VOTING_PERIOD
        self.proposal_deposit: int = DEFAULT_PROPOSAL_DEPOSIT
        # Track epoch of last spend reset
        self._last_spend_reset_epoch: int = 0
        # Proposal history for analytics
        self.proposal_history: list[dict[str, Any]] = []

    @property
    def work_interval(self) -> float:
        return 60.0

    # ------------------------------------------------------------------
    # Core loops
    # ------------------------------------------------------------------

    async def do_work(self) -> None:
        self.current_epoch += 1
        # Reset per-epoch treasury spend cap
        if self.current_epoch != self._last_spend_reset_epoch:
            self.treasury_spent_this_epoch = 0
            self._last_spend_reset_epoch = self.current_epoch
        await self._advance_proposals()
        await self._tally_voting_proposals()
        await self._execute_approved()
        await self._monitor_governance_health()

    async def handle_message(self, msg: Message) -> None:
        action = msg.payload.get("type", "")
        handler = {
            "submit_proposal": self._handle_submit_proposal,
            "vote": self._handle_vote,
            "register_drep": self._handle_register_drep,
            "register_spo": self._handle_register_spo,
            "register_cc": self._handle_register_cc,
            "delegate": self._handle_delegate,
            "governance_status": self._handle_governance_status,
            "proposal_query": self._handle_proposal_query,
            "upstream_alert": self._handle_upstream_alert,
        }.get(action)

        if handler:
            await handler(msg)
        else:
            await self.send(msg.sender, "response", {
                "type": "error",
                "error": f"Unknown governance action: {action}",
            })

    async def learn(self) -> None:
        await self._analyze_governance_patterns()

    # ------------------------------------------------------------------
    # Message handlers
    # ------------------------------------------------------------------

    async def _handle_submit_proposal(self, msg: Message) -> None:
        payload = msg.payload
        raw_type = payload.get("proposal_type", "info_action")
        try:
            ptype = ProposalType(raw_type)
        except ValueError:
            await self.send(msg.sender, "response", {
                "type": "error",
                "error": f"Invalid proposal type: {raw_type}. "
                         f"Valid: {[t.value for t in ProposalType]}",
            })
            return

        # Validate treasury spend
        if ptype == ProposalType.TREASURY_SPEND:
            amount = payload.get("treasury_amount", 0)
            recipient = payload.get("treasury_recipient", "")
            if amount <= 0:
                await self.send(msg.sender, "response", {
                    "type": "error",
                    "error": "treasury_amount must be positive",
                })
                return
            if not recipient:
                await self.send(msg.sender, "response", {
                    "type": "error",
                    "error": "treasury_recipient required for treasury_spend",
                })
                return
            if amount > self.treasury_balance:
                await self.send(msg.sender, "response", {
                    "type": "error",
                    "error": f"Requested {amount} exceeds treasury balance {self.treasury_balance}",
                })
                return

        prop_id = f"prop_{uuid.uuid4().hex[:8]}"
        proposal = Proposal(
            id=prop_id,
            title=payload.get("title", "Untitled Proposal"),
            description=payload.get("description", ""),
            proposer=payload.get("proposer", msg.sender),
            proposal_type=ptype,
            state=ProposalState.SUBMITTED,
            deposit=self.proposal_deposit,
            epoch_submitted=self.current_epoch,
            voting_deadline_epoch=self.current_epoch + self.voting_period_epochs,
            execution_delay_epochs=payload.get("execution_delay_epochs", 2),
            treasury_amount=payload.get("treasury_amount", 0),
            treasury_recipient=payload.get("treasury_recipient", ""),
        )
        self.proposals[prop_id] = proposal
        self.log.info("proposal.submitted", id=prop_id, type=ptype.value,
                      title=proposal.title)

        await self.send(msg.sender, "response", {
            "type": "proposal_created",
            "proposal_id": prop_id,
            "title": proposal.title,
            "proposal_type": ptype.value,
            "state": ProposalState.SUBMITTED.value,
            "voting_deadline_epoch": proposal.voting_deadline_epoch,
            "deposit_collected": self.proposal_deposit,
        })

    async def _handle_vote(self, msg: Message) -> None:
        payload = msg.payload
        prop_id = payload.get("proposal_id", "")
        voter_id = payload.get("voter_id", "")
        raw_choice = payload.get("choice", "").lower()
        raw_body = payload.get("body", "").lower()

        # Validate proposal
        proposal = self.proposals.get(prop_id)
        if not proposal:
            await self.send(msg.sender, "response", {
                "type": "error", "error": f"Proposal {prop_id} not found",
            })
            return
        if proposal.state != ProposalState.VOTING:
            await self.send(msg.sender, "response", {
                "type": "error",
                "error": f"Proposal {prop_id} is in state '{proposal.state.value}', not open for voting",
            })
            return

        # Validate choice
        try:
            choice = VoteChoice(raw_choice)
        except ValueError:
            await self.send(msg.sender, "response", {
                "type": "error",
                "error": f"Invalid vote choice: {raw_choice}. Use: yes, no, abstain",
            })
            return

        # Validate governance body
        try:
            body = GovBody(raw_body)
        except ValueError:
            await self.send(msg.sender, "response", {
                "type": "error",
                "error": f"Invalid governance body: {raw_body}. Use: drep, spo, cc",
            })
            return

        # Check body is required for this proposal type
        required = REQUIRED_BODIES.get(proposal.proposal_type, [])
        if body not in required:
            await self.send(msg.sender, "response", {
                "type": "error",
                "error": f"Body '{body.value}' does not vote on '{proposal.proposal_type.value}' proposals. "
                         f"Required bodies: {[b.value for b in required]}",
            })
            return

        # Validate voter exists in the specified body and get stake power
        stake_power = self._get_voter_power(voter_id, body)
        if stake_power is None:
            await self.send(msg.sender, "response", {
                "type": "error",
                "error": f"Voter {voter_id} not found in body '{body.value}'",
            })
            return

        # Check for duplicate vote (same voter + body on this proposal)
        for existing in proposal.votes:
            if existing.voter_id == voter_id and existing.body == body:
                await self.send(msg.sender, "response", {
                    "type": "error",
                    "error": f"Voter {voter_id} already voted on {prop_id} as {body.value}",
                })
                return

        vote = Vote(
            voter_id=voter_id,
            body=body,
            choice=choice,
            stake_power=stake_power,
            epoch_cast=self.current_epoch,
        )
        proposal.votes.append(vote)
        self.log.info("vote.cast", proposal=prop_id, voter=voter_id,
                      body=body.value, choice=choice.value, power=stake_power)

        await self.send(msg.sender, "response", {
            "type": "vote_cast",
            "proposal_id": prop_id,
            "voter_id": voter_id,
            "body": body.value,
            "choice": choice.value,
            "stake_power": stake_power,
            "status": "recorded",
        })

    async def _handle_register_drep(self, msg: Message) -> None:
        payload = msg.payload
        drep_id = payload.get("drep_id", f"drep_{uuid.uuid4().hex[:8]}")
        name = payload.get("name", "Anonymous DRep")
        stake = payload.get("stake", 0)

        if drep_id in self.dreps:
            await self.send(msg.sender, "response", {
                "type": "error", "error": f"DRep {drep_id} already registered",
            })
            return

        drep = DRep(
            id=drep_id,
            name=name,
            own_stake=stake,
            registered_epoch=self.current_epoch,
        )
        self.dreps[drep_id] = drep
        self.log.info("drep.registered", id=drep_id, name=name, stake=stake)

        await self.send(msg.sender, "response", {
            "type": "drep_registered",
            "drep_id": drep_id,
            "name": name,
            "stake": stake,
        })

    async def _handle_register_spo(self, msg: Message) -> None:
        payload = msg.payload
        spo_id = payload.get("spo_id", f"spo_{uuid.uuid4().hex[:8]}")
        name = payload.get("name", "Anonymous SPO")
        pledge = payload.get("pledge", 0)

        if spo_id in self.spos:
            await self.send(msg.sender, "response", {
                "type": "error", "error": f"SPO {spo_id} already registered",
            })
            return

        spo = SPO(id=spo_id, name=name, pledge=pledge)
        self.spos[spo_id] = spo
        self.log.info("spo.registered", id=spo_id, name=name, pledge=pledge)

        await self.send(msg.sender, "response", {
            "type": "spo_registered",
            "spo_id": spo_id,
            "name": name,
            "pledge": pledge,
        })

    async def _handle_register_cc(self, msg: Message) -> None:
        payload = msg.payload
        cc_id = payload.get("cc_id", f"cc_{uuid.uuid4().hex[:8]}")
        name = payload.get("name", "CC Member")
        term_length = payload.get("term_length_epochs", 36)

        if cc_id in self.cc_members:
            await self.send(msg.sender, "response", {
                "type": "error", "error": f"CC member {cc_id} already registered",
            })
            return

        member = CCMember(
            id=cc_id,
            name=name,
            term_start_epoch=self.current_epoch,
            term_length_epochs=term_length,
        )
        self.cc_members[cc_id] = member
        self.log.info("cc.registered", id=cc_id, name=name, term_length=term_length)

        await self.send(msg.sender, "response", {
            "type": "cc_registered",
            "cc_id": cc_id,
            "name": name,
            "term_start_epoch": self.current_epoch,
            "term_expires_epoch": self.current_epoch + term_length,
        })

    async def _handle_delegate(self, msg: Message) -> None:
        payload = msg.payload
        delegator_id = payload.get("delegator_id", "")
        drep_id = payload.get("drep_id", "")
        stake = payload.get("stake", 0)

        if not delegator_id:
            await self.send(msg.sender, "response", {
                "type": "error", "error": "delegator_id required",
            })
            return
        if drep_id not in self.dreps:
            await self.send(msg.sender, "response", {
                "type": "error", "error": f"DRep {drep_id} not found",
            })
            return
        if stake <= 0:
            await self.send(msg.sender, "response", {
                "type": "error", "error": "stake must be positive",
            })
            return

        # Remove previous delegation if exists
        prev_drep_id = self.delegations.get(delegator_id)
        if prev_drep_id and prev_drep_id in self.dreps:
            prev_stake = self.delegator_stakes.get(delegator_id, 0)
            self.dreps[prev_drep_id].delegated_stake -= prev_stake

        # Record new delegation
        self.delegations[delegator_id] = drep_id
        self.delegator_stakes[delegator_id] = stake
        self.dreps[drep_id].delegated_stake += stake

        self.log.info("delegation.recorded", delegator=delegator_id,
                      drep=drep_id, stake=stake)

        await self.send(msg.sender, "response", {
            "type": "delegation_recorded",
            "delegator_id": delegator_id,
            "drep_id": drep_id,
            "stake": stake,
            "drep_total_stake": self.dreps[drep_id].own_stake + self.dreps[drep_id].delegated_stake,
        })

    async def _handle_governance_status(self, msg: Message) -> None:
        health = self._compute_governance_health()
        active = [
            {
                "id": p.id,
                "title": p.title,
                "state": p.state.value,
                "type": p.proposal_type.value,
                "voting_deadline_epoch": p.voting_deadline_epoch,
                "vote_count": len(p.votes),
            }
            for p in self.proposals.values()
            if p.state in (
                ProposalState.SUBMITTED, ProposalState.VOTING,
                ProposalState.TALLYING, ProposalState.APPROVED,
                ProposalState.EXECUTING,
            )
        ]

        await self.send(msg.sender, "response", {
            "type": "governance_status",
            "current_epoch": self.current_epoch,
            "health_score": health["total"],
            "health_breakdown": health,
            "active_proposals": active,
            "total_proposals": len(self.proposals),
            "registered_dreps": len([d for d in self.dreps.values() if d.active]),
            "registered_spos": len([s for s in self.spos.values() if s.active]),
            "cc_members": len([c for c in self.cc_members.values()
                              if c.active and not c.is_expired(self.current_epoch)]),
            "treasury_balance": self.treasury_balance,
            "treasury_spent_this_epoch": self.treasury_spent_this_epoch,
        })

    async def _handle_proposal_query(self, msg: Message) -> None:
        prop_id = msg.payload.get("proposal_id", "")
        proposal = self.proposals.get(prop_id)
        if not proposal:
            await self.send(msg.sender, "response", {
                "type": "error", "error": f"Proposal {prop_id} not found",
            })
            return

        # Build current tally snapshot
        tally = self._tally_proposal(proposal)

        await self.send(msg.sender, "response", {
            "type": "proposal_details",
            "proposal_id": proposal.id,
            "title": proposal.title,
            "description": proposal.description,
            "proposer": proposal.proposer,
            "proposal_type": proposal.proposal_type.value,
            "state": proposal.state.value,
            "epoch_submitted": proposal.epoch_submitted,
            "voting_deadline_epoch": proposal.voting_deadline_epoch,
            "deposit": proposal.deposit,
            "vote_count": len(proposal.votes),
            "current_tally": tally,
            "tally_result": proposal.tally_result,
            "execution_result": proposal.execution_result,
            "treasury_amount": proposal.treasury_amount,
            "treasury_recipient": proposal.treasury_recipient,
        })

    async def _handle_upstream_alert(self, msg: Message) -> None:
        """Evaluate CIP changes or external governance events."""
        alert = msg.payload
        cip_id = alert.get("cip_id", "unknown")
        impact = alert.get("impact", "unknown")
        description = alert.get("description", "")

        self.memory.remember("tech_updates", {
            "type": "cip_alert",
            "cip_id": cip_id,
            "impact": impact,
            "description": description,
        })

        # If it affects governance parameters, flag for proposal
        if impact in ("governance", "voting", "treasury", "constitutional"):
            self.log.info("upstream.governance_impact", cip=cip_id, impact=impact)
            await self.broadcast("alert", {
                "type": "governance_cip_impact",
                "cip_id": cip_id,
                "impact": impact,
                "description": description,
                "recommendation": "Consider submitting a parameter_change or policy_change proposal",
            }, priority=2)

        await self.send(msg.sender, "response", {
            "type": "upstream_alert_ack",
            "cip_id": cip_id,
            "evaluated": True,
        })

    # ------------------------------------------------------------------
    # Proposal state machine
    # ------------------------------------------------------------------

    async def _advance_proposals(self) -> None:
        """Move proposals through their lifecycle based on epoch."""
        for proposal in list(self.proposals.values()):
            if proposal.state == ProposalState.SUBMITTED:
                # Auto-transition to VOTING immediately
                proposal.state = ProposalState.VOTING
                self.log.info("proposal.voting_started", id=proposal.id,
                              deadline=proposal.voting_deadline_epoch)

            elif proposal.state == ProposalState.VOTING:
                if self.current_epoch >= proposal.voting_deadline_epoch:
                    proposal.state = ProposalState.TALLYING
                    self.log.info("proposal.voting_closed", id=proposal.id)

            elif proposal.state == ProposalState.APPROVED:
                # Check if execution delay has passed
                epochs_since_approved = self.current_epoch - proposal.voting_deadline_epoch
                if epochs_since_approved >= proposal.execution_delay_epochs:
                    proposal.state = ProposalState.EXECUTING
                    self.log.info("proposal.execution_ready", id=proposal.id)

    async def _tally_voting_proposals(self) -> None:
        """Tally votes for proposals in TALLYING state."""
        for proposal in list(self.proposals.values()):
            if proposal.state != ProposalState.TALLYING:
                continue

            tally = self._tally_proposal(proposal)
            proposal.tally_result = tally

            if tally["passes"]:
                proposal.state = ProposalState.APPROVED
                proposal.resolved_at = time.time()
                self.log.info("proposal.approved", id=proposal.id,
                              tally=tally)
                self._record_outcome(proposal, "approved")
            else:
                proposal.state = ProposalState.REJECTED
                proposal.resolved_at = time.time()
                self.log.info("proposal.rejected", id=proposal.id,
                              tally=tally)
                self._record_outcome(proposal, "rejected")

    def _tally_proposal(self, proposal: Proposal) -> dict[str, Any]:
        """Perform weighted multi-body tally for a proposal.

        Returns a dict with per-body results and overall pass/fail.
        """
        required_bodies = REQUIRED_BODIES.get(proposal.proposal_type, [])
        threshold = APPROVAL_THRESHOLDS.get(proposal.proposal_type, 50.0)

        body_results: dict[str, dict[str, Any]] = {}
        all_pass = True

        for body in required_bodies:
            body_votes = [v for v in proposal.votes if v.body == body]
            total_body_stake = self._total_active_stake_for_body(body)

            yes_stake = sum(v.stake_power for v in body_votes if v.choice == VoteChoice.YES)
            no_stake = sum(v.stake_power for v in body_votes if v.choice == VoteChoice.NO)
            abstain_stake = sum(v.stake_power for v in body_votes if v.choice == VoteChoice.ABSTAIN)
            participating_stake = yes_stake + no_stake + abstain_stake

            # Quorum check: participating stake vs total active stake
            if total_body_stake > 0:
                participation_pct = (participating_stake / total_body_stake) * 100.0
            else:
                participation_pct = 0.0
            quorum_met = participation_pct >= self.quorum_pct

            # Threshold check: YES stake vs (YES + NO) stake — abstains don't count
            decisive_stake = yes_stake + no_stake
            if decisive_stake > 0:
                approval_pct = (yes_stake / decisive_stake) * 100.0
            else:
                approval_pct = 0.0
            threshold_met = approval_pct >= threshold

            body_passes = quorum_met and threshold_met

            body_results[body.value] = {
                "yes_stake": yes_stake,
                "no_stake": no_stake,
                "abstain_stake": abstain_stake,
                "participating_stake": participating_stake,
                "total_body_stake": total_body_stake,
                "participation_pct": round(participation_pct, 2),
                "approval_pct": round(approval_pct, 2),
                "quorum_required_pct": self.quorum_pct,
                "quorum_met": quorum_met,
                "threshold_required_pct": threshold,
                "threshold_met": threshold_met,
                "passes": body_passes,
                "vote_count": len(body_votes),
            }

            if not body_passes:
                all_pass = False

        return {
            "passes": all_pass,
            "required_bodies": [b.value for b in required_bodies],
            "threshold_pct": threshold,
            "body_results": body_results,
        }

    def _total_active_stake_for_body(self, body: GovBody) -> int:
        """Total active stake available for voting in a governance body."""
        if body == GovBody.DREP:
            return sum(
                d.own_stake + d.delegated_stake
                for d in self.dreps.values()
                if d.active
            )
        elif body == GovBody.SPO:
            return sum(s.pledge for s in self.spos.values() if s.active)
        elif body == GovBody.CC:
            # CC members each have equal weight of 1 unit per active non-expired member
            return sum(
                1 for c in self.cc_members.values()
                if c.active and not c.is_expired(self.current_epoch)
            )
        return 0

    def _get_voter_power(self, voter_id: str, body: GovBody) -> int | None:
        """Get voting power for a voter in a specific body. Returns None if not found."""
        if body == GovBody.DREP:
            drep = self.dreps.get(voter_id)
            if drep and drep.active:
                return drep.own_stake + drep.delegated_stake
            return None
        elif body == GovBody.SPO:
            spo = self.spos.get(voter_id)
            if spo and spo.active:
                return spo.pledge
            return None
        elif body == GovBody.CC:
            cc = self.cc_members.get(voter_id)
            if cc and cc.active and not cc.is_expired(self.current_epoch):
                return 1  # CC members have equal weight
            return None
        return None

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    async def _execute_approved(self) -> None:
        """Execute proposals that are ready."""
        for proposal in list(self.proposals.values()):
            if proposal.state != ProposalState.EXECUTING:
                continue

            try:
                if proposal.proposal_type == ProposalType.TREASURY_SPEND:
                    await self._execute_treasury_spend(proposal)
                elif proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
                    await self._execute_parameter_change(proposal)
                elif proposal.proposal_type == ProposalType.PROTOCOL_UPGRADE:
                    await self._execute_protocol_upgrade(proposal)
                elif proposal.proposal_type == ProposalType.POLICY_CHANGE:
                    await self._execute_policy_change(proposal)
                elif proposal.proposal_type == ProposalType.INFO_ACTION:
                    # Info actions don't execute — they just record the outcome
                    proposal.state = ProposalState.EXECUTED
                    proposal.execution_result = "info_action_recorded"
                    self.log.info("proposal.executed", id=proposal.id,
                                  result="info_action_recorded")
            except Exception as exc:
                proposal.state = ProposalState.FAILED
                proposal.execution_result = f"execution_error: {exc}"
                self.log.error("proposal.execution_failed", id=proposal.id,
                               error=str(exc))
                self._record_outcome(proposal, "failed")

    async def _execute_treasury_spend(self, proposal: Proposal) -> None:
        """Execute a treasury spend proposal."""
        amount = proposal.treasury_amount
        max_per_epoch = int(self.treasury_balance * (MAX_TREASURY_SPEND_PCT / 100.0))

        if self.treasury_spent_this_epoch + amount > max_per_epoch:
            proposal.state = ProposalState.FAILED
            proposal.execution_result = (
                f"Exceeds per-epoch spend cap: "
                f"requested={amount}, already_spent={self.treasury_spent_this_epoch}, "
                f"max={max_per_epoch}"
            )
            self._record_outcome(proposal, "failed")
            return

        if amount > self.treasury_balance:
            proposal.state = ProposalState.FAILED
            proposal.execution_result = (
                f"Insufficient treasury: requested={amount}, available={self.treasury_balance}"
            )
            self._record_outcome(proposal, "failed")
            return

        # Deduct from treasury
        self.treasury_balance -= amount
        self.treasury_spent_this_epoch += amount

        # Send execution request to TreasuryVault
        await self.send("TreasuryVault", "request", {
            "type": "treasury_disbursement",
            "proposal_id": proposal.id,
            "amount": amount,
            "recipient": proposal.treasury_recipient,
            "authorized_by": "GovernanceOracle",
            "epoch": self.current_epoch,
        }, priority=2)

        proposal.state = ProposalState.EXECUTED
        proposal.execution_result = (
            f"treasury_spend_executed: {amount} to {proposal.treasury_recipient}"
        )
        self.log.info("treasury.spent", id=proposal.id, amount=amount,
                      recipient=proposal.treasury_recipient,
                      remaining=self.treasury_balance)
        self._record_outcome(proposal, "executed")

    async def _execute_parameter_change(self, proposal: Proposal) -> None:
        """Execute a parameter change proposal."""
        # Broadcast the parameter change to all agents
        await self.broadcast("alert", {
            "type": "parameter_change_enacted",
            "proposal_id": proposal.id,
            "title": proposal.title,
            "description": proposal.description,
            "epoch": self.current_epoch,
        }, priority=2)

        proposal.state = ProposalState.EXECUTED
        proposal.execution_result = "parameter_change_enacted"
        self.log.info("proposal.executed", id=proposal.id,
                      result="parameter_change_enacted")
        self._record_outcome(proposal, "executed")

    async def _execute_protocol_upgrade(self, proposal: Proposal) -> None:
        """Execute a protocol upgrade proposal."""
        await self.broadcast("alert", {
            "type": "protocol_upgrade_enacted",
            "proposal_id": proposal.id,
            "title": proposal.title,
            "description": proposal.description,
            "epoch": self.current_epoch,
        }, priority=3)

        proposal.state = ProposalState.EXECUTED
        proposal.execution_result = "protocol_upgrade_enacted"
        self.log.info("proposal.executed", id=proposal.id,
                      result="protocol_upgrade_enacted")
        self._record_outcome(proposal, "executed")

    async def _execute_policy_change(self, proposal: Proposal) -> None:
        """Execute a policy change proposal."""
        await self.broadcast("alert", {
            "type": "policy_change_enacted",
            "proposal_id": proposal.id,
            "title": proposal.title,
            "description": proposal.description,
            "epoch": self.current_epoch,
        }, priority=2)

        proposal.state = ProposalState.EXECUTED
        proposal.execution_result = "policy_change_enacted"
        self.log.info("proposal.executed", id=proposal.id,
                      result="policy_change_enacted")
        self._record_outcome(proposal, "executed")

    # ------------------------------------------------------------------
    # Governance health
    # ------------------------------------------------------------------

    def _compute_governance_health(self) -> dict[str, Any]:
        """Compute governance health score (0-100) with weighted components."""
        scores: dict[str, float] = {}

        # 1. Participation rate (weight: 30)
        #    Average participation across recent proposals
        recent_tallied = [
            p for p in self.proposals.values()
            if p.tally_result and p.tally_result.get("body_results")
        ]
        if recent_tallied:
            participation_rates = []
            for p in recent_tallied[-20:]:  # last 20 proposals
                for body_data in p.tally_result["body_results"].values():
                    participation_rates.append(body_data.get("participation_pct", 0.0))
            avg_participation = sum(participation_rates) / len(participation_rates) if participation_rates else 0.0
            # Scale: 0% participation = 0 score, 50%+ = 100 score
            scores["participation"] = min(100.0, (avg_participation / 50.0) * 100.0)
        else:
            scores["participation"] = 0.0

        # 2. DRep coverage (weight: 25)
        #    % of total ecosystem stake delegated to active DReps
        total_drep_stake = sum(
            d.own_stake + d.delegated_stake for d in self.dreps.values() if d.active
        )
        total_delegated = sum(self.delegator_stakes.values())
        total_own = sum(d.own_stake for d in self.dreps.values() if d.active)
        total_ecosystem_stake = total_delegated + total_own
        if total_ecosystem_stake > 0:
            drep_coverage = (total_drep_stake / total_ecosystem_stake) * 100.0
        else:
            drep_coverage = 0.0
        scores["drep_coverage"] = min(100.0, drep_coverage)

        # 3. Proposal throughput (weight: 20)
        #    Ratio of resolved proposals to submitted
        total = len(self.proposals)
        resolved = sum(
            1 for p in self.proposals.values()
            if p.state in (
                ProposalState.APPROVED, ProposalState.REJECTED,
                ProposalState.EXECUTED, ProposalState.FAILED,
            )
        )
        if total > 0:
            scores["throughput"] = (resolved / total) * 100.0
        else:
            scores["throughput"] = 100.0  # No proposals = not broken

        # 4. Contention ratio (weight: 15)
        #    % of votes within 10% of threshold — high contention = healthy debate
        #    Inverted: if too many are contentious, governance is gridlocked
        #    Sweet spot: some contention is good, too much is bad
        contentious_count = 0
        tallied_count = 0
        for p in self.proposals.values():
            if not p.tally_result or not p.tally_result.get("body_results"):
                continue
            tallied_count += 1
            threshold = p.tally_result.get("threshold_pct", 50.0)
            for body_data in p.tally_result["body_results"].values():
                approval = body_data.get("approval_pct", 0.0)
                if abs(approval - threshold) <= 10.0:
                    contentious_count += 1
                    break  # count each proposal once
        if tallied_count > 0:
            contention_ratio = (contentious_count / tallied_count) * 100.0
            # Ideal: 10-30% contentious. Score peaks at 20%, drops at extremes
            if contention_ratio <= 20.0:
                scores["contention"] = min(100.0, (contention_ratio / 20.0) * 100.0)
            else:
                scores["contention"] = max(0.0, 100.0 - ((contention_ratio - 20.0) / 80.0) * 100.0)
        else:
            scores["contention"] = 50.0  # neutral when no data

        # 5. CC health (weight: 10)
        #    % of CC seats filled and not expired
        total_cc = len(self.cc_members)
        if total_cc > 0:
            active_cc = sum(
                1 for c in self.cc_members.values()
                if c.active and not c.is_expired(self.current_epoch)
            )
            scores["cc_health"] = (active_cc / total_cc) * 100.0
        else:
            scores["cc_health"] = 0.0

        # Weighted total
        weights = {
            "participation": 30,
            "drep_coverage": 25,
            "throughput": 20,
            "contention": 15,
            "cc_health": 10,
        }
        total_score = sum(
            scores[k] * (weights[k] / 100.0) for k in weights
        )

        return {
            "total": round(total_score, 1),
            "components": {k: round(v, 1) for k, v in scores.items()},
            "weights": weights,
            "epoch": self.current_epoch,
        }

    async def _monitor_governance_health(self) -> None:
        """Record governance health and alert if score drops."""
        health = self._compute_governance_health()
        self.memory.remember("decisions", {
            "type": "governance_health",
            "score": health["total"],
            "components": health["components"],
            "active_proposals": len([
                p for p in self.proposals.values()
                if p.state in (ProposalState.VOTING, ProposalState.SUBMITTED)
            ]),
            "total_proposals": len(self.proposals),
            "epoch": self.current_epoch,
        })

        # Alert if health drops below 40
        if health["total"] < 40.0:
            await self.broadcast("alert", {
                "type": "governance_health_warning",
                "score": health["total"],
                "components": health["components"],
                "epoch": self.current_epoch,
                "message": "Governance health is critically low — participation or structure needs attention",
            }, priority=2)

    # ------------------------------------------------------------------
    # Learning / analytics
    # ------------------------------------------------------------------

    async def _analyze_governance_patterns(self) -> None:
        """Review governance patterns, detect anomalies, learn from outcomes."""
        insights: list[dict[str, Any]] = []

        # 1. Low participation trends
        recent_tallied = [
            p for p in self.proposals.values()
            if p.tally_result and p.tally_result.get("body_results")
        ][-10:]

        low_participation_count = 0
        for p in recent_tallied:
            for body_data in p.tally_result["body_results"].values():
                if body_data.get("participation_pct", 0) < self.quorum_pct * 1.5:
                    low_participation_count += 1
                    break

        if len(recent_tallied) > 3 and low_participation_count > len(recent_tallied) * 0.5:
            insights.append({
                "type": "low_participation_trend",
                "severity": "warning",
                "detail": f"{low_participation_count}/{len(recent_tallied)} recent proposals "
                          f"had near-quorum participation",
                "recommendation": "Consider lowering quorum or incentivizing voter participation",
            })

        # 2. Concentrated voting power detection
        if self.dreps:
            total_stake = sum(
                d.own_stake + d.delegated_stake for d in self.dreps.values() if d.active
            )
            if total_stake > 0:
                for drep in self.dreps.values():
                    if not drep.active:
                        continue
                    drep_share = ((drep.own_stake + drep.delegated_stake) / total_stake) * 100.0
                    if drep_share > 33.0:
                        insights.append({
                            "type": "concentrated_voting_power",
                            "severity": "critical",
                            "drep_id": drep.id,
                            "drep_name": drep.name,
                            "stake_share_pct": round(drep_share, 1),
                            "detail": f"DRep {drep.name} controls {drep_share:.1f}% of total stake",
                            "recommendation": "Encourage stake delegation diversity",
                        })

        # 3. Last-minute vote swings
        for p in recent_tallied:
            if not p.votes:
                continue
            total_votes = len(p.votes)
            # Votes in the last epoch of the voting period
            last_epoch_votes = [
                v for v in p.votes
                if v.epoch_cast >= p.voting_deadline_epoch - 1
            ]
            if total_votes > 5 and len(last_epoch_votes) > total_votes * 0.5:
                last_epoch_stake = sum(v.stake_power for v in last_epoch_votes)
                total_stake = sum(v.stake_power for v in p.votes)
                if total_stake > 0 and (last_epoch_stake / total_stake) > 0.5:
                    insights.append({
                        "type": "last_minute_swing",
                        "severity": "warning",
                        "proposal_id": p.id,
                        "proposal_title": p.title,
                        "late_vote_pct": round((last_epoch_stake / total_stake) * 100, 1),
                        "detail": f">{50}% of voting power cast in final epoch",
                        "recommendation": "Consider extending voting period or introducing commit-reveal scheme",
                    })

        # 4. Rejection rate analysis
        resolved = [
            p for p in self.proposals.values()
            if p.state in (ProposalState.APPROVED, ProposalState.REJECTED,
                           ProposalState.EXECUTED, ProposalState.FAILED)
        ]
        if len(resolved) > 5:
            rejected = sum(1 for p in resolved if p.state == ProposalState.REJECTED)
            rejection_rate = (rejected / len(resolved)) * 100.0
            if rejection_rate > 70.0:
                insights.append({
                    "type": "high_rejection_rate",
                    "severity": "warning",
                    "rejection_rate_pct": round(rejection_rate, 1),
                    "detail": f"{rejection_rate:.0f}% of proposals rejected",
                    "recommendation": "Review proposal requirements; "
                                     "consider pre-submission consultation process",
                })

        # 5. CC term expiry warnings
        for cc in self.cc_members.values():
            if not cc.active:
                continue
            epochs_until_expiry = (cc.term_start_epoch + cc.term_length_epochs) - self.current_epoch
            if 0 < epochs_until_expiry <= 3:
                insights.append({
                    "type": "cc_term_expiring",
                    "severity": "info",
                    "cc_id": cc.id,
                    "cc_name": cc.name,
                    "epochs_remaining": epochs_until_expiry,
                    "detail": f"CC member {cc.name} term expires in {epochs_until_expiry} epochs",
                    "recommendation": "Initiate CC membership renewal process",
                })

        if insights:
            self.memory.remember("learnings", {
                "type": "governance_analysis",
                "insights": insights,
                "epoch": self.current_epoch,
            })
            self.log.info("governance.analysis", insight_count=len(insights))

            # Alert on critical findings
            critical = [i for i in insights if i.get("severity") == "critical"]
            if critical:
                await self.broadcast("alert", {
                    "type": "governance_analysis_critical",
                    "findings": critical,
                    "epoch": self.current_epoch,
                }, priority=3)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _record_outcome(self, proposal: Proposal, outcome: str) -> None:
        """Record proposal outcome in history for analytics."""
        record = {
            "proposal_id": proposal.id,
            "title": proposal.title,
            "type": proposal.proposal_type.value,
            "outcome": outcome,
            "epoch_submitted": proposal.epoch_submitted,
            "epoch_resolved": self.current_epoch,
            "vote_count": len(proposal.votes),
            "tally": proposal.tally_result,
        }
        self.proposal_history.append(record)
        self.memory.remember("decisions", {
            "type": "proposal_outcome",
            **record,
        })
