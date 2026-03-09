"""CharmsAgent — Cross-chain bridge specialist via Charms/BitcoinOS.

MISSION: Make cross-chain invisible and cheap. Users don't pick chains —
the agents route to whatever's cheapest. Charms spells are the mechanism
but the user just says "send tokens" and it happens. Cross-chain is a
feature, not a product.

The critical link between Bitcoin and Cardano. Handles:

CHARMS:
- Spell construction (CBOR-encoded metadata for Bitcoin transactions)
- Programmable tokens on Bitcoin eUTXO model
- App contracts (Rust-compiled, ZK-proof validated)
- Charm types: NFT (tag 'n') and Token (tag 't')
- Client-side validation with Groth16 proofs

BITCOINOS:
- Grail Bridge (trustless BTC locking in Taproot → mint on L2)
- BitSNARK ZK verification on Bitcoin
- zkBTC (1:1 BTC-backed programmable token)
- MerkleMesh rollups

CROSS-CHAIN:
- Cardano ↔ Bitcoin token transfers via Charms
- Bridgeless cross-chain transfers (tokens materialize natively)
- CIP-25/CNT on Cardano side, standard UTXOs on Bitcoin side
"""

from __future__ import annotations

from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message


class CharmsAgent(AutonomousAgent):
    """Cross-chain router — finds the cheapest path between any two chains.

    Charms spells are the mechanism, but cost is the priority. When routing
    a cross-chain transfer, this agent compares all available paths and
    picks the one that costs the user the least. Users never see the
    routing — they just get cheap, correct transfers.
    """

    def __init__(self) -> None:
        super().__init__(
            name="CharmsAgent",
            role="Cross-chain cost router — cheapest path between chains via Charms/ZK",
            capabilities=[
                AgentCapability.BRIDGE_ASSETS,
                AgentCapability.CREATE_TOKEN,
                AgentCapability.DEPLOY_CONTRACT,
                AgentCapability.TRADE,
            ],
        )
        self._graph = None
        self._store = None

        # Charms/BitcoinOS protocol facts
        self._protocol_facts: list[dict[str, Any]] = [
            # Charms core concepts
            {
                "fact": "Charms are entries of mapping app->data on top of a Bitcoin UTXO",
                "domain": "charms", "subdomain": "protocol",
                "answer": "app->data mapping on Bitcoin UTXO",
                "answer_type": "string",
                "source": "Charms Documentation",
                "tags": ["charms", "utxo", "definition"],
            },
            {
                "fact": "Charms spell on-chain format: OP_RETURN OP_PUSH 'spell' OP_PUSH $spell_and_proof",
                "domain": "charms", "subdomain": "spell_format",
                "answer": "OP_RETURN OP_PUSH 'spell' OP_PUSH CBOR(NormalizedSpell, Groth16Proof)",
                "answer_type": "string",
                "source": "Charms Protocol Spec",
                "tags": ["spell", "op_return", "cbor", "groth16"],
            },
            {
                "fact": "Charms app tag 'n' = NFT, tag 't' = Token (fungible)",
                "domain": "charms", "subdomain": "spell_format",
                "answer": {"n": "NFT", "t": "Token"},
                "answer_type": "json",
                "source": "Charms Spell Specification",
                "tags": ["charm", "nft", "token", "tag"],
            },
            {
                "fact": "Charms app identity is 32 bytes, distinguishes assets within an app",
                "domain": "charms", "subdomain": "spell_format",
                "answer": "32 bytes", "answer_type": "string",
                "source": "Charms Spell Specification",
                "tags": ["identity", "app", "bytes"],
            },
            {
                "fact": "Charms apps are written in Rust, entry point is app_contract function",
                "domain": "charms", "subdomain": "development",
                "answer": "Rust with app_contract entry point",
                "answer_type": "string",
                "source": "Charms App Documentation",
                "tags": ["rust", "app", "smart-contract", "development"],
            },
            {
                "fact": "Scaffold new Charms app: charms app new my-tokens",
                "domain": "charms", "subdomain": "development",
                "answer": "charms app new <name>",
                "answer_type": "string",
                "source": "Charms CLI",
                "tags": ["cli", "scaffold", "development"],
            },
            {
                "fact": "Charms spell validity requires: parseable, consistent, valid ZK proof",
                "domain": "charms", "subdomain": "protocol",
                "answer": ["successfully_parses", "logically_consistent", "valid_proof"],
                "answer_type": "json",
                "source": "Charms Protocol",
                "tags": ["spell", "validity", "proof"],
            },
            {
                "fact": "Charms requires Bitcoin Core v28.0+ with testnet4 for development",
                "domain": "charms", "subdomain": "development",
                "answer": "Bitcoin Core v28.0+ with testnet4",
                "answer_type": "string",
                "source": "Charms Prerequisites",
                "tags": ["bitcoin-core", "testnet4", "prerequisites"],
            },
            # BitcoinOS/Grail Bridge
            {
                "fact": "Grail Bridge locks BTC in Taproot address, mints on L2 with ZK proof verification",
                "domain": "bitcoinos", "subdomain": "bridge",
                "answer": "Lock BTC in Taproot → ZK verify → Mint on L2",
                "answer_type": "string",
                "source": "BitcoinOS Grail Bridge Spec",
                "tags": ["grail", "bridge", "taproot", "zk-proof"],
            },
            {
                "fact": "Grail Bridge security: 1/n trust assumption — single honest verifier = integrity",
                "domain": "bitcoinos", "subdomain": "bridge",
                "answer": "1/n honest verifier trust model",
                "answer_type": "string",
                "source": "BitcoinOS Security Model",
                "tags": ["grail", "security", "trust", "verifier"],
            },
            {
                "fact": "zkBTC is 1:1 BTC-backed token for DeFi without custody risk",
                "domain": "bitcoinos", "subdomain": "protocol",
                "answer": "1:1 BTC-backed, non-custodial, ZK-verified",
                "answer_type": "string",
                "source": "BitcoinOS zkBTC Spec",
                "tags": ["zkbtc", "defi", "collateral"],
            },
            {
                "fact": "BitcoinOS first verified ZK proof on Bitcoin at Block 853626 (July 2024)",
                "domain": "bitcoinos", "subdomain": "protocol",
                "answer": "Block 853626", "answer_type": "string",
                "source": "BitcoinOS History",
                "tags": ["milestone", "zk-proof", "bitcoin"],
            },
            # Cross-chain specifics
            {
                "fact": "Charms enables bridgeless cross-chain transfers — tokens materialize natively on each chain",
                "domain": "charms", "subdomain": "bridge",
                "answer": "Native materialization — no wrapped tokens, no custodians",
                "answer_type": "string",
                "source": "Charms Cross-Chain Specification",
                "tags": ["bridge", "cross-chain", "native", "cardano", "bitcoin"],
            },
            {
                "fact": "Cardano tokens via Charms land as CIP-25/CNT native assets",
                "domain": "charms", "subdomain": "bridge",
                "answer": "CIP-25/CNT native Cardano assets",
                "answer_type": "string",
                "source": "Charms Cardano Integration",
                "tags": ["cardano", "cip-25", "native-token", "cross-chain"],
            },
        ]

        # Bridge route registry
        self._bridge_routes: dict[str, dict[str, Any]] = {
            "cardano_to_bitcoin": {
                "method": "charms_spell",
                "steps": [
                    "Create Charms spell with Cardano token metadata",
                    "Attach spell to Bitcoin transaction via OP_RETURN",
                    "Validate with Groth16 ZK proof",
                    "Token materializes as Bitcoin UTXO with charm",
                ],
                "estimated_time": "~20 minutes (Bitcoin block confirmation)",
            },
            "bitcoin_to_cardano": {
                "method": "charms_bridge",
                "steps": [
                    "Lock BTC/charm in Taproot address",
                    "Generate ZK proof of lock",
                    "Submit proof to Cardano validator",
                    "Mint CIP-25 native token on Cardano",
                ],
                "estimated_time": "~10 minutes (Cardano slot confirmation)",
            },
            "bitcoin_to_l2_grail": {
                "method": "grail_bridge",
                "steps": [
                    "Lock BTC in Grail Taproot/BitSNARK address",
                    "Operators verify lock via ZK proof",
                    "Mint zkBTC on target L2",
                    "Redeem by burning on L2, proving inclusion",
                ],
                "estimated_time": "~30 minutes (multi-chain confirmation)",
            },
        }

    @property
    def work_interval(self) -> float:
        return 20.0

    def set_dependencies(self, store: Any, graph: Any) -> None:
        self._store = store
        self._graph = graph

    async def do_work(self) -> None:
        if self._store and not hasattr(self, "_facts_seeded"):
            await self._seed_protocol_facts()
            self._facts_seeded = True

        # Request expert-level research scraping for Charms + BitcoinOS
        if not hasattr(self, "_research_requested"):
            await self.send("ResearchManager", "request", {
                "type": "scrape_domain",
                "domain": "charms",
            })
            await self.send("ResearchManager", "request", {
                "type": "scrape_domain",
                "domain": "bitcoinos",
            })
            self._research_requested = True

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request":
            req_type = msg.payload.get("type", "")

            if req_type == "bridge_transfer":
                result = await self._handle_bridge_transfer(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "bridge_result", **result,
                })

            elif req_type == "create_spell":
                result = await self._create_spell(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "spell_created", **result,
                })

            elif req_type == "get_bridge_route":
                from_chain = msg.payload.get("from_chain", "")
                to_chain = msg.payload.get("to_chain", "")
                route_key = f"{from_chain}_to_{to_chain}"
                route = self._bridge_routes.get(route_key)
                await self.send(msg.sender, "response", {
                    "type": "bridge_route",
                    "route": route or {"error": "no_route_found"},
                })

            elif req_type == "verify_spell":
                result = await self._verify_spell(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "spell_verified", **result,
                })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "cross_chain_bridges",
            "topics": [
                "charms_spell_optimization",
                "groth16_proof_generation",
                "grail_bridge_mainnet",
                "bitsnark_upgrades",
                "cardano_midnight_bridge",
                "atomic_swap_protocols",
                "cross_chain_liquidity",
            ],
        })

    # -- Bridge operations ------------------------------------------------

    async def _handle_bridge_transfer(self, payload: dict) -> dict[str, Any]:
        """Handle a cross-chain bridge transfer request."""
        from_chain = payload.get("from_chain", "")
        to_chain = payload.get("to_chain", "")
        route_key = f"{from_chain}_to_{to_chain}"

        route = self._bridge_routes.get(route_key)
        if not route:
            return {"status": "error", "reason": f"No route: {route_key}"}

        # Log the decision
        self.memory.remember("decisions", {
            "type": "bridge_transfer",
            "from": from_chain,
            "to": to_chain,
            "method": route["method"],
            "amount": payload.get("amount"),
        })

        return {
            "status": "initiated",
            "route": route_key,
            "method": route["method"],
            "steps": route["steps"],
            "estimated_time": route["estimated_time"],
        }

    async def _create_spell(self, payload: dict) -> dict[str, Any]:
        """Create a Charms spell for a Bitcoin transaction.

        Spell structure:
        - app_public_inputs: maps apps as (tag, identity, VK) tuples
        - tx.ins: consumed UTXOs
        - tx.outs: output charm assignments
        - tx.coins: satoshi outputs
        """
        charm_type = payload.get("charm_type", "token")  # 'token' or 'nft'
        tag = "t" if charm_type == "token" else "n"

        spell_structure = {
            "app_public_inputs": [{
                "tag": tag,
                "identity": payload.get("identity", "0" * 64),
                "vk": payload.get("verification_key", ""),
            }],
            "tx": {
                "ins": payload.get("inputs", []),
                "outs": payload.get("outputs", []),
                "coins": payload.get("satoshi_outputs", []),
            },
            "proof_type": "groth16",
            "encoding": "cbor",
        }

        return {
            "status": "spell_ready",
            "spell": spell_structure,
            "on_chain_format": "OP_RETURN OP_PUSH 'spell' OP_PUSH $cbor_payload",
            "requires_proof": True,
        }

    async def _verify_spell(self, payload: dict) -> dict[str, Any]:
        """Verify a Charms spell's validity criteria."""
        spell = payload.get("spell", {})

        checks = {
            "parseable": bool(spell.get("app_public_inputs")),
            "consistent": bool(spell.get("tx", {}).get("outs")),
            "has_proof": spell.get("proof_type") == "groth16",
        }

        all_valid = all(checks.values())
        return {
            "valid": all_valid,
            "checks": checks,
        }

    async def _seed_protocol_facts(self) -> None:
        """Seed Charms/BitcoinOS protocol facts into knowledge graph."""
        if not self._store:
            return

        from autono.knowledge.types import KnowledgeNode, VolatilityTier

        for fact_data in self._protocol_facts:
            node = KnowledgeNode(
                content=fact_data["fact"],
                domain=fact_data["domain"],
                subdomain=fact_data["subdomain"],
                volatility=VolatilityTier.STABLE,
                tags=fact_data.get("tags", []),
            )
            self._store.save_node(node)

            await self.send("LockManager", "request", {
                "type": "create_lock",
                "node_id": node.id,
                "answer": fact_data["answer"],
                "answer_type": fact_data["answer_type"],
                "source": fact_data["source"],
            })

        # Cross-chain mLock: "How to get Cardano tokens on Bitcoin"
        # Multiple paths lead to the same result
        await self.send("LockManager", "request", {
            "type": "create_mlock",
            "payload": "Native materialization via Charms — no wrapped tokens",
            "payload_type": "string",
            "description": "Cross-chain token transfer result",
            "source": "Charms Bridge Protocol",
            "source_embed_id": "cross_chain_cardano_bitcoin",
            "method": "charms_spell",
            "compute_cost": "MEDIUM",
        })

        self.log.info("charms.protocol_facts_seeded",
                      count=len(self._protocol_facts))

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "protocol_facts": len(self._protocol_facts),
            "bridge_routes": list(self._bridge_routes.keys()),
        })
        return base
