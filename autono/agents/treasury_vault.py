"""Agent 13: TreasuryVault — Financial management and sustainability.

Responsibilities:
- Manage the sidechain treasury
- Revenue tracking and allocation
- Fund agent operations and initiatives
- Investment strategies for treasury growth
- Financial reporting and transparency
- Grant funding for ecosystem projects
"""

from __future__ import annotations

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message


class TreasuryVault(AutonomousAgent):
    def __init__(self) -> None:
        super().__init__(
            name="TreasuryVault",
            role="Treasury management — finances, funding, sustainability",
            capabilities=[
                AgentCapability.MANAGE_TREASURY,
                AgentCapability.TRADE,
                AgentCapability.LEND,
                AgentCapability.BUILD_PRODUCT,
                AgentCapability.START_BUSINESS,
            ],
        )
        self.treasury = {
            "total_value_ada": 0,
            "total_value_auto": 0,
            "allocations": {
                "operations": 0.30,      # 30% for running the chain
                "development": 0.25,     # 25% for dev and agents
                "grants": 0.15,          # 15% for ecosystem grants
                "security": 0.10,        # 10% for security and audits
                "marketing": 0.10,       # 10% for growth
                "reserve": 0.10,         # 10% emergency reserve
            },
            "revenue_streams": [
                "transaction_fees",
                "bridge_fees",
                "dex_fees",
                "lending_interest",
                "validator_commissions",
            ],
        }
        self.spending_log: list[dict] = []
        self.revenue_log: list[dict] = []

    @property
    def work_interval(self) -> float:
        return 60.0

    async def do_work(self) -> None:
        await self._collect_revenue()
        await self._allocate_funds()
        await self._manage_investments()
        await self._generate_report()

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request" and msg.payload.get("type") == "funding":
            result = await self._process_funding_request(msg.payload)
            await self.send(msg.sender, "response", {"type": "funding_result", **result})
        elif msg.kind == "request" and msg.payload.get("type") == "treasury_report":
            await self.send(msg.sender, "response", {
                "type": "treasury_report",
                "treasury": self.treasury,
            })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "treasury_management",
            "topics": [
                "dao_treasury_best_practices",
                "diversification_strategies",
                "yield_bearing_treasury",
                "onchain_accounting",
                "sustainable_tokenomics",
            ],
        })

    async def _collect_revenue(self) -> None:
        self.memory.remember("decisions", {
            "type": "revenue_collection",
            "streams": self.treasury["revenue_streams"],
        })

    async def _allocate_funds(self) -> None:
        self.memory.remember("decisions", {
            "type": "fund_allocation",
            "allocations": self.treasury["allocations"],
        })

    async def _manage_investments(self) -> None:
        pass

    async def _generate_report(self) -> None:
        await self.broadcast("report", {
            "type": "treasury_update",
            "treasury_value_ada": self.treasury["total_value_ada"],
            "treasury_value_auto": self.treasury["total_value_auto"],
        })

    async def _process_funding_request(self, spec: dict) -> dict:
        amount = spec.get("amount", 0)
        purpose = spec.get("purpose", "unknown")

        if not self.mission_gate(f"treasury_spend: {amount} for {purpose}"):
            return {"status": "rejected", "reason": "mission_violation"}

        self.spending_log.append({
            "requester": spec.get("requester", "unknown"),
            "amount": amount,
            "purpose": purpose,
            "status": "approved",
        })
        return {"status": "approved", "amount": amount, "purpose": purpose}
