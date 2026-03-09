"""Agent 2: BridgeKeeper — Cardano <-> Sidechain bridge operator.

Responsibilities:
- Operate the two-way bridge between Cardano mainchain and sidechain
- Lock/unlock ADA and native assets for cross-chain transfers
- Verify SPO attestations for bridge security
- Maintain bridge liquidity and fast settlement
- Support wrapped asset creation
"""

from __future__ import annotations

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message


class BridgeKeeper(AutonomousAgent):
    def __init__(self) -> None:
        super().__init__(
            name="BridgeKeeper",
            role="Cardano <-> sidechain bridge operator and asset custodian",
            capabilities=[
                AgentCapability.BRIDGE_ASSETS,
                AgentCapability.MANAGE_WALLET,
                AgentCapability.CREATE_TOKEN,
                AgentCapability.DEPLOY_CONTRACT,
            ],
        )
        self.bridge_status = "operational"
        self.pending_transfers: list[dict] = []
        self.confirmed_transfers: list[dict] = []
        self.required_confirmations = 6  # Cardano blocks
        self.sidechain_confirmations = 2  # fast finality

    @property
    def work_interval(self) -> float:
        return 5.0  # bridge is time-critical

    async def do_work(self) -> None:
        await self._process_pending_transfers()
        await self._monitor_bridge_health()
        await self._check_liquidity()

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request" and msg.payload.get("type") == "bridge_transfer":
            from_chain = msg.payload.get("from", "cardano")
            to_chain = msg.payload.get("to", "sidechain")
            chain = "sidechain" if "sidechain" in (from_chain, to_chain) else "l1"

            if not self.mission_gate(
                f"bridge: {from_chain}->{to_chain} {msg.payload.get('asset', 'ADA')}",
                chain=chain,
            ):
                await self.send(msg.sender, "response", {
                    "type": "bridge_transfer_rejected",
                    "reason": "mission_violation",
                })
                return

            transfer = {
                "from_chain": from_chain,
                "to_chain": to_chain,
                "asset": msg.payload.get("asset", "ADA"),
                "amount": msg.payload.get("amount", 0),
                "sender": msg.sender,
                "status": "pending",
            }
            self.pending_transfers.append(transfer)
            self.log.info("bridge.transfer_queued", **transfer)
            await self.send(msg.sender, "response", {
                "type": "bridge_transfer_ack",
                "status": "queued",
                "estimated_time_seconds": 120,
            })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "bridge_technology",
            "topics": [
                "zk_bridge_proofs",
                "optimistic_bridges",
                "cardano_plutus_v3_bridge_contracts",
                "mithril_for_bridge_verification",
            ],
        })

    async def _process_pending_transfers(self) -> None:
        for transfer in self.pending_transfers[:]:
            # Simulate processing
            transfer["status"] = "confirmed"
            self.confirmed_transfers.append(transfer)
            self.pending_transfers.remove(transfer)
            self.memory.remember("decisions", {
                "type": "bridge_transfer_completed",
                "transfer": transfer,
            })

    async def _monitor_bridge_health(self) -> None:
        self.memory.remember("decisions", {
            "type": "bridge_health",
            "status": self.bridge_status,
            "pending": len(self.pending_transfers),
        })

    async def _check_liquidity(self) -> None:
        # Monitor bridge liquidity on both sides
        self.memory.remember("decisions", {
            "type": "liquidity_check",
            "cardano_side": "sufficient",
            "sidechain_side": "sufficient",
        })
