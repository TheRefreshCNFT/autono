"""CardanoChainAgent — Cardano protocol specialist.

MISSION: Make Cardano transactions cheaper than any existing wallet.
Every CNT transfer, every NFT mint, every ADA send through autono must
cost less than doing it through Vespr, Eternl, or Lace. This agent
exists to prove that a sidechain can make Cardano accessible and affordable.

HOW WE'RE CHEAPER:
- Optimal UTXO selection (fewest inputs = lowest fee)
- Minimize change outputs (less data = smaller tx = lower fee)
- Batch multiple operations into single transactions where possible
- Use reference scripts instead of including script in every tx
- Smart fee estimation — never overpay, always use minimum valid fee
- Off-chain validation via ZK proofs for complex operations

Deep knowledge of:
- Cardano UTXO model and extended UTXO (eUTXO)
- CIP standards (CIP-25 for NFTs, CIP-30 for dApp connector, etc.)
- Plutus smart contracts (V1, V2, V3)
- MeshJS SDK for browser-native Cardano operations
- Blockfrost/Koios API integration
- ADA Handle resolution
- Minting policies and metadata standards
- Opshin (Python smart contracts for Cardano)
- Helios (JavaScript smart contract toolkit)

Coordinates with BitcoinChainAgent and CharmsAgent for cross-chain operations.
Uses Links & Locks for instant protocol fact lookups.
"""

from __future__ import annotations

from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message
from autono.services.blockfrost import BlockfrostClient, BlockfrostError


class CardanoChainAgent(AutonomousAgent):
    """Cardano blockchain specialist — cost optimization is job #1.

    Every transaction this agent builds must be cheaper than what Vespr,
    Eternl, or any existing Cardano wallet would produce for the same
    operation. This means optimal UTXO selection, minimal change outputs,
    batching where possible, and never overpaying fees.

    Uses Blockfrost for live chain queries. API key from environment only.
    """

    def __init__(self) -> None:
        super().__init__(
            name="CardanoChainAgent",
            role="Cardano cost optimizer — cheaper CNT transfers than any existing wallet",
            capabilities=[
                AgentCapability.MANAGE_WALLET,
                AgentCapability.CREATE_TOKEN,
                AgentCapability.DEPLOY_CONTRACT,
                AgentCapability.MINT_NFT,
                AgentCapability.TRADE,
            ],
        )
        self._graph = None
        self._store = None
        self._blockfrost = BlockfrostClient()
        self._chain_synced = False

        # Cardano-specific protocol knowledge (seed data for Locks)
        self._protocol_facts: list[dict[str, Any]] = [
            {
                "fact": "CIP-25 metadata key for NFTs is 721",
                "domain": "cardano", "subdomain": "cip",
                "answer": "721", "answer_type": "integer",
                "source": "CIP-0025",
                "tags": ["nft", "metadata", "cip-25"],
            },
            {
                "fact": "Cardano uses BIP-1852 purpose for key derivation",
                "domain": "cardano", "subdomain": "protocol",
                "answer": "1852", "answer_type": "integer",
                "source": "CIP-1852",
                "tags": ["wallet", "derivation", "bip-1852"],
            },
            {
                "fact": "Cardano coin type in BIP-44 derivation is 1815",
                "domain": "cardano", "subdomain": "protocol",
                "answer": "1815", "answer_type": "integer",
                "source": "SLIP-0044",
                "tags": ["wallet", "derivation", "coin-type"],
            },
            {
                "fact": "Cardano mainnet address prefix is addr1",
                "domain": "cardano", "subdomain": "protocol",
                "answer": "addr1", "answer_type": "string",
                "source": "CIP-0019",
                "tags": ["address", "mainnet", "bech32"],
            },
            {
                "fact": "Cardano testnet address prefix is addr_test1",
                "domain": "cardano", "subdomain": "protocol",
                "answer": "addr_test1", "answer_type": "string",
                "source": "CIP-0019",
                "tags": ["address", "testnet", "bech32"],
            },
            {
                "fact": "Minimum UTXO value on Cardano is approximately 1 ADA",
                "domain": "cardano", "subdomain": "protocol",
                "answer": "1000000", "answer_type": "lovelace",
                "source": "Cardano Protocol Parameters",
                "tags": ["utxo", "minimum", "lovelace"],
            },
            {
                "fact": "1 ADA = 1,000,000 Lovelace",
                "domain": "cardano", "subdomain": "protocol",
                "answer": "1000000", "answer_type": "integer",
                "source": "Cardano Specification",
                "tags": ["ada", "lovelace", "conversion"],
            },
            {
                "fact": "Plutus V3 is the current smart contract language version",
                "domain": "cardano", "subdomain": "protocol",
                "answer": "PlutusV3", "answer_type": "string",
                "source": "Chang Hard Fork",
                "tags": ["plutus", "smart-contract", "version"],
            },
            {
                "fact": "Opshin compiles Python to Plutus Core for Cardano smart contracts",
                "domain": "cardano", "subdomain": "sdk",
                "answer": "opshin", "answer_type": "string",
                "source": "https://github.com/OpShin/opshin",
                "tags": ["opshin", "python", "smart-contract", "plutus"],
            },
            {
                "fact": "Helios is a JavaScript/TypeScript toolkit for Cardano smart contracts",
                "domain": "cardano", "subdomain": "sdk",
                "answer": "helios", "answer_type": "string",
                "source": "https://github.com/Hyperion-BT/helios",
                "tags": ["helios", "javascript", "smart-contract"],
            },
        ]

        # Cross-chain routing awareness
        self._cross_chain_routes: dict[str, str] = {
            "cardano_to_bitcoin": "CharmsAgent",
            "cardano_to_night": "NightChainAgent",
            "bitcoin_to_cardano": "CharmsAgent",
        }

    @property
    def work_interval(self) -> float:
        return 15.0

    def set_dependencies(self, store: Any, graph: Any) -> None:
        self._store = store
        self._graph = graph

    async def do_work(self) -> None:
        """Monitor Cardano chain state and seed protocol knowledge."""
        # On first run, seed protocol facts into the knowledge graph
        if self._store and not hasattr(self, "_facts_seeded"):
            await self._seed_protocol_facts()
            self._facts_seeded = True

        # Request expert-level research scraping for Cardano domain
        if not hasattr(self, "_research_requested"):
            await self.send("ResearchManager", "request", {
                "type": "scrape_domain",
                "domain": "cardano",
            })
            self._research_requested = True

        # Sync chain tip and protocol params periodically
        if self._blockfrost.is_configured:
            await self._sync_chain_state()

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request":
            req_type = msg.payload.get("type", "")

            if req_type == "cardano_query":
                # Query Cardano-specific knowledge
                result = await self._query_cardano_knowledge(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "cardano_query_result",
                    **result,
                })

            elif req_type == "cross_chain_transfer":
                # Route cross-chain requests to appropriate agent
                target_chain = msg.payload.get("to_chain", "")
                router = self._cross_chain_routes.get(
                    f"cardano_to_{target_chain}"
                )
                if router:
                    await self.send(router, "request", {
                        "type": "bridge_transfer",
                        "from_chain": "cardano",
                        "to_chain": target_chain,
                        **msg.payload,
                    })
                    await self.send(msg.sender, "response", {
                        "type": "transfer_routed",
                        "routed_to": router,
                    })

            elif req_type == "build_transaction":
                result = await self._build_cardano_tx(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "transaction_built",
                    **result,
                })

            # --- Live chain queries via Blockfrost ---

            elif req_type == "get_balance":
                address = msg.payload.get("address", "")
                result = await self._get_balance(address)
                await self.send(msg.sender, "response", {
                    "type": "balance_result", **result,
                })

            elif req_type == "get_utxos":
                address = msg.payload.get("address", "")
                asset = msg.payload.get("asset")
                result = await self._get_utxos(address, asset)
                await self.send(msg.sender, "response", {
                    "type": "utxo_result", **result,
                })

            elif req_type == "get_tx":
                tx_hash = msg.payload.get("tx_hash", "")
                result = await self._get_transaction(tx_hash)
                await self.send(msg.sender, "response", {
                    "type": "tx_result", **result,
                })

            elif req_type == "get_asset":
                asset_id = msg.payload.get("asset_id", "")
                result = await self._get_asset(asset_id)
                await self.send(msg.sender, "response", {
                    "type": "asset_result", **result,
                })

            elif req_type == "submit_tx":
                tx_cbor = msg.payload.get("tx_cbor", b"")
                result = await self._submit_transaction(tx_cbor)
                await self.send(msg.sender, "response", {
                    "type": "tx_submitted", **result,
                })

            elif req_type == "chain_tip":
                result = await self._get_chain_tip()
                await self.send(msg.sender, "response", {
                    "type": "chain_tip_result", **result,
                })

            elif req_type == "get_protocol_param":
                # Instant lookup via knowledge graph
                param = msg.payload.get("param", "")
                result = self._lookup_protocol_param(param)
                await self.send(msg.sender, "response", {
                    "type": "protocol_param",
                    "param": param,
                    **result,
                })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "cardano_protocol",
            "topics": [
                "plutus_v3_capabilities",
                "midnight_sidechain_integration",
                "hydra_layer2_scaling",
                "mithril_light_client",
                "opshin_python_contracts",
                "helios_typescript_contracts",
                "meshjs_latest_features",
            ],
        })

    # -- Cardano-specific operations --------------------------------------

    async def _seed_protocol_facts(self) -> None:
        """Seed known Cardano protocol facts into the knowledge graph."""
        if not self._store:
            return

        from autono.knowledge.types import KnowledgeNode, VolatilityTier

        for fact_data in self._protocol_facts:
            # Create node
            node = KnowledgeNode(
                content=fact_data["fact"],
                domain=fact_data["domain"],
                subdomain=fact_data["subdomain"],
                volatility=VolatilityTier.STABLE,
                tags=fact_data.get("tags", []),
            )
            self._store.save_node(node)

            # Request lock creation
            await self.send("LockManager", "request", {
                "type": "create_lock",
                "node_id": node.id,
                "answer": fact_data["answer"],
                "answer_type": fact_data["answer_type"],
                "source": fact_data["source"],
            })

        self.log.info("cardano.protocol_facts_seeded",
                      count=len(self._protocol_facts))

    async def _query_cardano_knowledge(self, payload: dict) -> dict[str, Any]:
        """Query the knowledge graph for Cardano-specific information."""
        if not self._graph:
            return {"found": False, "reason": "graph_not_initialized"}

        query = payload.get("query", "")
        domain_nodes = self._store.find_nodes_by_domain("cardano") if self._store else []

        results = []
        for node_id in domain_nodes[:10]:
            qr = self._graph.query_node(node_id)
            if qr.hit_lock or qr.hit_mlock:
                results.append({
                    "node_id": node_id,
                    "answer": qr.locked_answer,
                    "source": qr.answer_source,
                    "deterministic": True,
                })
            elif qr.gathered_context:
                results.append({
                    "node_id": node_id,
                    "context": qr.gathered_context,
                    "deterministic": False,
                })

        return {"found": len(results) > 0, "results": results}

    def _lookup_protocol_param(self, param: str) -> dict[str, Any]:
        """Fast lookup of a Cardano protocol parameter."""
        param_lower = param.lower()

        # Check seeded facts first (fastest path)
        for fact in self._protocol_facts:
            if param_lower in fact["fact"].lower():
                return {
                    "found": True,
                    "answer": fact["answer"],
                    "source": fact["source"],
                    "deterministic": True,
                }

        return {"found": False}

    async def _build_cardano_tx(self, payload: dict) -> dict[str, Any]:
        """Build a Cardano transaction — optimized for MINIMUM COST.

        Cost optimization strategy:
        1. Fetch protocol params (min_fee_a, min_fee_b) for exact fee calc
        2. Select UTXOs to minimize inputs (fewer inputs = smaller tx = lower fee)
        3. Minimize change outputs (try to find exact-match UTXOs)
        4. Calculate minimum valid fee — never overpay
        5. Compare against existing wallet fees to verify we're cheaper

        The fee formula: min_fee = min_fee_a * tx_size_bytes + min_fee_b
        We minimize tx_size_bytes by selecting optimal UTXOs.
        """
        address = payload.get("from_address", "")
        amount = int(payload.get("amount", 0))  # lovelace
        is_token = bool(payload.get("tokens"))

        try:
            params = await self._blockfrost.protocol_params()
            utxos = await self._blockfrost.address_utxos(address) if address else []
        except BlockfrostError as e:
            return {"status": "error", "error": str(e)}

        if not params or not utxos:
            return {
                "status": "ready",
                "chain": "cardano",
                "utxo_count": len(utxos),
                "protocol_params_available": bool(params),
                "requires": ["utxo_selection", "fee_calculation", "signing"],
                "cross_chain": payload.get("to_chain", "") != "",
            }

        # Protocol fee parameters
        min_fee_a = int(params.get("min_fee_a", 44))  # lovelace per byte
        min_fee_b = int(params.get("min_fee_b", 155381))  # base fee

        # UTXO selection — minimize inputs for lowest fee
        selected, total_input = self._select_utxos_optimal(utxos, amount)

        # Estimate tx size based on input/output count
        # ~300 bytes base + ~150 per input + ~80 per output
        estimated_inputs = len(selected)
        estimated_outputs = 2 if total_input > amount else 1  # change output?
        estimated_size = 300 + (estimated_inputs * 150) + (estimated_outputs * 80)

        # Minimum valid fee — never overpay
        min_fee = min_fee_a * estimated_size + min_fee_b

        # Compare against existing wallets
        op_type = "cardano_cnt_transfer" if is_token else "cardano_simple_transfer"
        beats_wallets = self.beats_existing_wallets(op_type, min_fee)
        cost_target = self.get_cost_target(op_type)

        return {
            "status": "ready",
            "chain": "cardano",
            "utxo_count": len(utxos),
            "selected_utxos": estimated_inputs,
            "estimated_outputs": estimated_outputs,
            "estimated_size_bytes": estimated_size,
            "estimated_fee_lovelace": min_fee,
            "estimated_fee_ada": min_fee / 1_000_000,
            "beats_existing_wallets": beats_wallets,
            "wallet_comparison": {
                "our_fee": min_fee,
                "typical_wallet_fee": cost_target.get("current_wallet_fee_lovelace", 0) if cost_target else 0,
                "savings_lovelace": (cost_target.get("current_wallet_fee_lovelace", 0) - min_fee) if cost_target else 0,
            },
            "optimization": {
                "strategy": "minimal_utxo_selection",
                "inputs_used": estimated_inputs,
                "inputs_available": len(utxos),
                "change_output": estimated_outputs > 1,
            },
            "requires": ["signing"],
            "cross_chain": payload.get("to_chain", "") != "",
        }

    def _select_utxos_optimal(
        self, utxos: list[dict], target_lovelace: int
    ) -> tuple[list[dict], int]:
        """Select UTXOs to minimize transaction size (= minimize fee).

        Strategy:
        1. Try to find a single UTXO that covers the target (1 input, no change = cheapest)
        2. If not, find the smallest set of UTXOs that covers target + estimated fee
        3. Sort by value descending so we use fewer, larger UTXOs
        """
        if not utxos or target_lovelace <= 0:
            return [], 0

        # Extract lovelace values
        valued = []
        for utxo in utxos:
            lovelace = 0
            for amt in utxo.get("amount", []):
                if amt.get("unit") == "lovelace":
                    lovelace = int(amt["quantity"])
                    break
            valued.append((lovelace, utxo))

        # Sort largest first — fewer large UTXOs = smaller tx = lower fee
        valued.sort(key=lambda x: x[0], reverse=True)

        # Strategy 1: exact match (no change output needed = even cheaper)
        estimated_fee = 180_000  # conservative estimate
        target_with_fee = target_lovelace + estimated_fee

        for lovelace, utxo in valued:
            if lovelace >= target_with_fee and lovelace <= target_with_fee * 1.1:
                return [utxo], lovelace

        # Strategy 2: single large UTXO (1 input + 1 change output)
        for lovelace, utxo in valued:
            if lovelace >= target_with_fee:
                return [utxo], lovelace

        # Strategy 3: accumulate smallest set
        selected = []
        total = 0
        for lovelace, utxo in valued:
            selected.append(utxo)
            total += lovelace
            if total >= target_with_fee:
                break

        return selected, total

    # -- Blockfrost-backed chain queries ------------------------------------

    async def _sync_chain_state(self) -> None:
        """Periodically sync chain tip and protocol params into knowledge."""
        try:
            tip = await self._blockfrost.tip()
            if tip and self._store:
                from autono.knowledge.types import KnowledgeNode, VolatilityTier

                # Store chain tip as a volatile node (changes every ~20s)
                node = KnowledgeNode(
                    content=f"Cardano chain tip: block {tip.get('block')}, "
                            f"slot {tip.get('slot')}, epoch {tip.get('epoch')}",
                    domain="cardano",
                    subdomain="chain_state",
                    volatility=VolatilityTier.REALTIME,
                    tags=["chain_tip", "block", "slot", "epoch"],
                )
                self._store.save_node(node)

                if not self._chain_synced:
                    self.log.info("cardano.chain_synced",
                                 block=tip.get("block"),
                                 epoch=tip.get("epoch"),
                                 network=self._blockfrost.network)
                    self._chain_synced = True

        except BlockfrostError as e:
            self.log.warning("cardano.sync_failed", error=str(e))

    async def _get_balance(self, address: str) -> dict[str, Any]:
        """Get ADA balance and native tokens for an address."""
        try:
            lovelace = await self._blockfrost.get_ada_balance(address)
            tokens = await self._blockfrost.get_native_tokens(address)
            ada = lovelace / 1_000_000
            return {
                "address": address,
                "lovelace": lovelace,
                "ada": ada,
                "native_tokens": len(tokens),
                "tokens": tokens[:50],  # cap response size
            }
        except BlockfrostError as e:
            return {"address": address, "error": str(e)}

    async def _get_utxos(
        self, address: str, asset: str | None = None
    ) -> dict[str, Any]:
        """Get UTXOs at an address."""
        try:
            utxos = await self._blockfrost.address_utxos(address, asset)
            return {
                "address": address,
                "utxo_count": len(utxos),
                "utxos": utxos,
            }
        except BlockfrostError as e:
            return {"address": address, "error": str(e)}

    async def _get_transaction(self, tx_hash: str) -> dict[str, Any]:
        """Get transaction details."""
        try:
            tx_data = await self._blockfrost.tx(tx_hash)
            if not tx_data:
                return {"tx_hash": tx_hash, "found": False}
            tx_utxos = await self._blockfrost.tx_utxos(tx_hash)
            metadata = await self._blockfrost.tx_metadata(tx_hash)
            return {
                "tx_hash": tx_hash,
                "found": True,
                "tx": tx_data,
                "utxos": tx_utxos,
                "metadata": metadata,
            }
        except BlockfrostError as e:
            return {"tx_hash": tx_hash, "error": str(e)}

    async def _get_asset(self, asset_id: str) -> dict[str, Any]:
        """Get asset/token information."""
        try:
            asset_data = await self._blockfrost.asset(asset_id)
            if not asset_data:
                return {"asset_id": asset_id, "found": False}
            return {
                "asset_id": asset_id,
                "found": True,
                **asset_data,
            }
        except BlockfrostError as e:
            return {"asset_id": asset_id, "error": str(e)}

    async def _submit_transaction(self, tx_cbor: bytes) -> dict[str, Any]:
        """Submit a signed transaction to the Cardano network."""
        try:
            tx_hash = await self._blockfrost.tx_submit(tx_cbor)
            self.log.info("cardano.tx_submitted", tx_hash=tx_hash)
            return {"submitted": True, "tx_hash": tx_hash}
        except BlockfrostError as e:
            self.log.error("cardano.tx_submit_failed", error=str(e))
            return {"submitted": False, "error": str(e)}

    async def _get_chain_tip(self) -> dict[str, Any]:
        """Get current chain tip."""
        try:
            return await self._blockfrost.tip()
        except BlockfrostError as e:
            return {"error": str(e)}

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "protocol_facts": len(self._protocol_facts),
            "cross_chain_routes": list(self._cross_chain_routes.keys()),
            "facts_seeded": getattr(self, "_facts_seeded", False),
            "blockfrost": self._blockfrost.stats(),
            "chain_synced": self._chain_synced,
        })
        return base

    async def stop(self) -> None:
        """Shut down and close Blockfrost client."""
        await self._blockfrost.close()
        await super().stop()
