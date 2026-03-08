"""BitcoinChainAgent — Bitcoin protocol specialist.

Deep knowledge of:
- Bitcoin UTXO model
- BIP standards (BIP-32, BIP-39, BIP-44, BIP-84, BIP-86, BIP-141)
- Address types: Legacy (P2PKH), SegWit (P2SH-P2WPKH), Native SegWit (P2WPKH), Taproot (P2TR)
- PSBT (Partially Signed Bitcoin Transactions)
- Taproot and Schnorr signatures
- BitcoinOS/Charms integration for programmable tokens
- ZK proof verification via BitSNARK
- OP_RETURN data embedding
- Fee estimation and UTXO selection

Coordinates with CharmsAgent for programmable token operations.
Coordinates with CardanoChainAgent via CharmsAgent for cross-chain transfers.
"""

from __future__ import annotations

from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message


class BitcoinChainAgent(AutonomousAgent):
    """Bitcoin blockchain specialist.

    Wraps the WALI wallet's Bitcoin module and adds protocol intelligence.
    Knows about Charms/BitcoinOS for programmable assets on Bitcoin.
    """

    def __init__(self) -> None:
        super().__init__(
            name="BitcoinChainAgent",
            role="Bitcoin protocol specialist — UTXO, BIPs, Taproot, PSBT, Charms",
            capabilities=[
                AgentCapability.MANAGE_WALLET,
                AgentCapability.CREATE_TOKEN,
                AgentCapability.TRADE,
                AgentCapability.BRIDGE_ASSETS,
            ],
        )
        self._graph = None
        self._store = None

        # Bitcoin protocol knowledge (seed data for Locks)
        self._protocol_facts: list[dict[str, Any]] = [
            {
                "fact": "Bitcoin uses BIP-44 purpose 44' for legacy addresses",
                "domain": "bitcoin", "subdomain": "protocol",
                "answer": "44", "answer_type": "integer",
                "source": "BIP-0044",
                "tags": ["wallet", "derivation", "legacy", "bip-44"],
            },
            {
                "fact": "Bitcoin uses BIP-84 purpose 84' for native segwit (bech32)",
                "domain": "bitcoin", "subdomain": "protocol",
                "answer": "84", "answer_type": "integer",
                "source": "BIP-0084",
                "tags": ["wallet", "derivation", "segwit", "bip-84"],
            },
            {
                "fact": "Bitcoin uses BIP-86 purpose 86' for Taproot (P2TR)",
                "domain": "bitcoin", "subdomain": "protocol",
                "answer": "86", "answer_type": "integer",
                "source": "BIP-0086",
                "tags": ["wallet", "derivation", "taproot", "bip-86"],
            },
            {
                "fact": "Bitcoin coin type in BIP-44 derivation is 0",
                "domain": "bitcoin", "subdomain": "protocol",
                "answer": "0", "answer_type": "integer",
                "source": "SLIP-0044",
                "tags": ["wallet", "derivation", "coin-type"],
            },
            {
                "fact": "1 BTC = 100,000,000 satoshis",
                "domain": "bitcoin", "subdomain": "protocol",
                "answer": "100000000", "answer_type": "integer",
                "source": "Bitcoin Protocol",
                "tags": ["btc", "satoshi", "conversion"],
            },
            {
                "fact": "Bitcoin mainnet address prefixes: 1 (P2PKH), 3 (P2SH), bc1q (P2WPKH), bc1p (P2TR)",
                "domain": "bitcoin", "subdomain": "protocol",
                "answer": {"P2PKH": "1", "P2SH": "3", "P2WPKH": "bc1q", "P2TR": "bc1p"},
                "answer_type": "json",
                "source": "BIP-0173, BIP-0350",
                "tags": ["address", "mainnet", "prefix"],
            },
            {
                "fact": "Bitcoin block time target is 10 minutes (600 seconds)",
                "domain": "bitcoin", "subdomain": "protocol",
                "answer": "600", "answer_type": "integer",
                "source": "Bitcoin Whitepaper",
                "tags": ["block", "time", "consensus"],
            },
            {
                "fact": "Bitcoin maximum supply is 21,000,000 BTC",
                "domain": "bitcoin", "subdomain": "protocol",
                "answer": "21000000", "answer_type": "integer",
                "source": "Bitcoin Protocol",
                "tags": ["supply", "maximum", "economics"],
            },
            {
                "fact": "Charms spell data is stored in OP_RETURN with 'spell' prefix",
                "domain": "bitcoin", "subdomain": "charms",
                "answer": "OP_RETURN OP_PUSH 'spell' OP_PUSH $spell_and_proof",
                "answer_type": "string",
                "source": "Charms Documentation",
                "tags": ["charms", "spell", "op_return"],
            },
            {
                "fact": "Charms spells use CBOR-encoded (NormalizedSpell, Proof) with Groth16 ZK proof",
                "domain": "bitcoin", "subdomain": "charms",
                "answer": "CBOR(NormalizedSpell, Groth16Proof)",
                "answer_type": "string",
                "source": "Charms Protocol Spec",
                "tags": ["charms", "spell", "cbor", "zk-proof", "groth16"],
            },
            {
                "fact": "BitSNARK is the ZK verification VM for Bitcoin, used by BitcoinOS/Grail Bridge",
                "domain": "bitcoin", "subdomain": "bitcoinos",
                "answer": "BitSNARK",
                "answer_type": "string",
                "source": "BitcoinOS Documentation",
                "tags": ["bitsnark", "zk-proof", "bitcoinos", "verification"],
            },
        ]

        self._cross_chain_routes: dict[str, str] = {
            "bitcoin_to_cardano": "CharmsAgent",
            "bitcoin_to_night": "NightChainAgent",
        }

    @property
    def work_interval(self) -> float:
        return 15.0

    def set_dependencies(self, store: Any, graph: Any) -> None:
        self._store = store
        self._graph = graph

    async def do_work(self) -> None:
        if self._store and not hasattr(self, "_facts_seeded"):
            await self._seed_protocol_facts()
            self._facts_seeded = True

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request":
            req_type = msg.payload.get("type", "")

            if req_type == "bitcoin_query":
                result = await self._query_bitcoin_knowledge(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "bitcoin_query_result",
                    **result,
                })

            elif req_type == "cross_chain_transfer":
                target_chain = msg.payload.get("to_chain", "")
                router = self._cross_chain_routes.get(f"bitcoin_to_{target_chain}")
                if router:
                    await self.send(router, "request", {
                        "type": "bridge_transfer",
                        "from_chain": "bitcoin",
                        "to_chain": target_chain,
                        **msg.payload,
                    })

            elif req_type == "build_psbt":
                result = await self._build_psbt(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "psbt_built", **result,
                })

            elif req_type == "charms_spell":
                # Delegate to CharmsAgent for programmable token operations
                await self.send("CharmsAgent", "request", {
                    "type": "create_spell",
                    "from_chain": "bitcoin",
                    **msg.payload,
                })

            elif req_type == "get_address_type":
                address = msg.payload.get("address", "")
                result = self._identify_address_type(address)
                await self.send(msg.sender, "response", {
                    "type": "address_type", **result,
                })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "bitcoin_protocol",
            "topics": [
                "taproot_advanced_scripts",
                "ordinals_and_inscriptions",
                "charms_spell_development",
                "bitcoinos_grail_bridge",
                "bitsnark_zk_verification",
                "lightning_network_integration",
                "psbt_v2_specification",
            ],
        })

    # -- Bitcoin-specific operations --------------------------------------

    async def _seed_protocol_facts(self) -> None:
        """Seed Bitcoin protocol facts into the knowledge graph."""
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

        # Create mLock: BTC conversion (satoshis)
        # 1 BTC = 100M sats — can be reached from multiple paths
        await self.send("LockManager", "request", {
            "type": "create_mlock",
            "payload": 100_000_000,
            "payload_type": "integer",
            "description": "Satoshis per BTC",
            "source": "Bitcoin Protocol",
            "source_embed_id": "btc_sat_conversion",
            "method": "direct_definition",
            "compute_cost": "LOW",
        })

        self.log.info("bitcoin.protocol_facts_seeded",
                      count=len(self._protocol_facts))

    async def _query_bitcoin_knowledge(self, payload: dict) -> dict[str, Any]:
        """Query knowledge graph for Bitcoin-specific information."""
        if not self._graph or not self._store:
            return {"found": False}

        domain_nodes = self._store.find_nodes_by_domain("bitcoin")
        results = []
        for node_id in domain_nodes[:10]:
            qr = self._graph.query_node(node_id)
            if qr.hit_lock or qr.hit_mlock:
                results.append({
                    "node_id": node_id,
                    "answer": qr.locked_answer,
                    "deterministic": True,
                })
            elif qr.gathered_context:
                results.append({
                    "node_id": node_id,
                    "context": qr.gathered_context,
                    "deterministic": False,
                })

        return {"found": len(results) > 0, "results": results}

    async def _build_psbt(self, payload: dict) -> dict[str, Any]:
        """Build a PSBT with knowledge-enhanced input selection."""
        return {
            "status": "ready",
            "chain": "bitcoin",
            "format": "psbt",
            "requires": ["utxo_selection", "fee_estimation", "signing"],
        }

    def _identify_address_type(self, address: str) -> dict[str, Any]:
        """Identify Bitcoin address type from prefix — deterministic lock lookup."""
        if address.startswith("bc1p") or address.startswith("tb1p"):
            return {"type": "P2TR", "name": "Taproot", "bip": "BIP-86"}
        elif address.startswith("bc1q") or address.startswith("tb1q"):
            return {"type": "P2WPKH", "name": "Native SegWit", "bip": "BIP-84"}
        elif address.startswith("3") or address.startswith("2"):
            return {"type": "P2SH-P2WPKH", "name": "SegWit", "bip": "BIP-49"}
        elif address.startswith("1") or address.startswith("m") or address.startswith("n"):
            return {"type": "P2PKH", "name": "Legacy", "bip": "BIP-44"}
        return {"type": "unknown", "name": "Unknown"}

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "protocol_facts": len(self._protocol_facts),
            "cross_chain_routes": list(self._cross_chain_routes.keys()),
        })
        return base
