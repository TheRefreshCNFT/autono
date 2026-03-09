"""BitcoinChainAgent — Bitcoin protocol specialist.

MISSION: Enable cheap cross-chain operations between Bitcoin and Cardano.
Bitcoin is the settlement layer — Charms spells execute on Bitcoin, but
the user never needs to know. When autono routes through Bitcoin, it must
still be cheaper and easier than the alternative.

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

from datetime import datetime, timezone
from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message

from autono.agents.chain_specialists.compatibility_harness import (
    CompatibilityTestMixin,
    check_api_endpoint_exists,
    check_config_key_exists,
)


class BitcoinChainAgent(CompatibilityTestMixin, AutonomousAgent):
    """Bitcoin specialist — cheapest cross-chain path via Charms/BitcoinOS.

    When the cheapest route between chains goes through Bitcoin, this agent
    handles it. Optimizes UTXO selection and fee estimation for minimum cost.
    Users never see Bitcoin complexity — they just get cheap, fast transfers.
    """

    def __init__(self) -> None:
        super().__init__(
            name="BitcoinChainAgent",
            role="Bitcoin cost optimizer — cheapest cross-chain path via Charms",
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

        # UTXO format reference used for compatibility checks
        self._utxo_format: dict[str, Any] = {
            "txid": "hex_string_64",
            "vout": "uint32",
            "value": "satoshis_int",
            "scriptPubKey": {"type": "string", "hex": "string"},
        }

        # Repos whose releases directly affect fee estimation and routing
        self._fee_relevant_repos: set[str] = {
            "bitcoin/bitcoin",
            "romanz/electrs",
            "nickkuk/electrs",  # alternate electrs fork
            "blockstream/electrs",
        }
        self._charms_relevant_repos: set[str] = {
            "charms-dev/charms",
            "ArmadaChain/charms",
            "ArmadaChain/bitcoin-os",
        }

        # In-memory log of upstream updates received from RepoWatcherAgent
        self._upstream_updates: list[dict[str, Any]] = []

        # Register compatibility checks for upstream repos
        self.register_compatibility_check(
            "bitcoin/bitcoin",
            "bitcoin_rpc_endpoint",
            check_api_endpoint_exists("http://127.0.0.1:8332"),
        )
        self.register_compatibility_check(
            "bitcoin/bitcoin",
            "utxo_format_compat",
            check_config_key_exists(self._utxo_format, "scriptPubKey.type"),
        )

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

        # Request expert-level research scraping for Bitcoin domain
        if not hasattr(self, "_research_requested"):
            await self.send("ResearchManager", "request", {
                "type": "scrape_domain",
                "domain": "bitcoin",
            })
            self._research_requested = True

    async def handle_message(self, msg: Message) -> None:
        # ---- Alerts from RepoWatcherAgent --------------------------------
        if msg.kind == "alert":
            alert_type = msg.payload.get("type", "")

            if alert_type == "repo_new_release":
                await self._handle_new_release(msg.payload)
                return

            if alert_type == "repo_breaking_change":
                await self._handle_breaking_change(msg.payload)
                return

            if alert_type == "repo_beta_test_results":
                await self.handle_beta_test_alert(msg)
                return

            if alert_type == "security_advisory":
                await self._handle_security_advisory(msg.payload)
                return

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

    # -- Repo-watcher alert handlers -----------------------------------------

    async def _handle_new_release(self, payload: dict[str, Any]) -> None:
        """Handle a ``repo_new_release`` alert from RepoWatcherAgent.

        Tracks fee estimation API changes (bitcoin-core, electrs) and
        assesses impact on cross-chain routing via Charms.
        """
        repo = payload.get("repo", "")
        tag = payload.get("tag", "")
        name = payload.get("name", tag)
        prerelease = payload.get("prerelease", False)
        body_preview = payload.get("body_preview", "")

        self.log.info(
            "bitcoin.new_release",
            repo=repo,
            tag=tag,
            prerelease=prerelease,
        )

        # Assess fee estimation impact
        affects_fees = repo in self._fee_relevant_repos
        fee_keywords = [
            "fee", "estimatesmartfee", "feerate", "mempool",
            "rbf", "cpfp", "priority", "dust", "relay",
        ]
        body_lower = body_preview.lower()
        fee_mentions = [kw for kw in fee_keywords if kw in body_lower]

        # Assess Charms / cross-chain routing impact
        affects_charms = repo in self._charms_relevant_repos
        charms_keywords = [
            "spell", "charm", "op_return", "taproot", "groth16",
            "proof", "cbor", "bridge", "grail",
        ]
        charms_mentions = [kw for kw in charms_keywords if kw in body_lower]

        impact = {
            "repo": repo,
            "tag": tag,
            "name": name,
            "prerelease": prerelease,
            "affects_fee_estimation": affects_fees,
            "fee_relevant_mentions": fee_mentions,
            "affects_charms_routing": affects_charms,
            "charms_relevant_mentions": charms_mentions,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        self._upstream_updates.append(impact)
        self.memory.remember("tech_updates", {
            "type": "upstream_release",
            **impact,
        })

        # Store knowledge node for fee-affecting or charms-affecting releases
        if (affects_fees or affects_charms) and self._store:
            from autono.knowledge.types import KnowledgeNode, VolatilityTier

            node = KnowledgeNode(
                content=(
                    f"Upstream release: {repo} {name} (tag {tag}). "
                    f"Pre-release: {prerelease}. "
                    f"Fee mentions: {', '.join(fee_mentions) or 'none'}. "
                    f"Charms mentions: {', '.join(charms_mentions) or 'none'}. "
                    f"Preview: {body_preview[:300]}"
                ),
                domain="bitcoin",
                subdomain="upstream_updates",
                volatility=VolatilityTier.VOLATILE,
                tags=["release", "upstream", repo.split("/")[-1]],
            )
            self._store.save_node(node)

        # If Charms-related, notify CharmsAgent so it can reassess routing
        if affects_charms:
            await self.send("CharmsAgent", "alert", {
                "type": "upstream_charms_release",
                "repo": repo,
                "tag": tag,
                "charms_mentions": charms_mentions,
            })

    async def _handle_breaking_change(self, payload: dict[str, Any]) -> None:
        """Handle a ``repo_breaking_change`` alert from RepoWatcherAgent.

        Assesses impact on fee estimation APIs and cross-chain routing.
        """
        repo = payload.get("repo", "")
        issue = payload.get("issue", "")
        title = payload.get("title", "")
        url = payload.get("url", "")

        self.log.warning(
            "bitcoin.breaking_change",
            repo=repo,
            issue=issue,
            title=title,
        )

        # Classify affected subsystems
        affected_subsystems: list[str] = []
        title_lower = title.lower()
        if any(kw in title_lower for kw in ("fee", "estimatesmartfee", "feerate")):
            affected_subsystems.append("fee_estimation")
        if any(kw in title_lower for kw in ("rpc", "api", "endpoint", "json")):
            affected_subsystems.append("rpc_api")
        if any(kw in title_lower for kw in ("utxo", "input", "output", "psbt")):
            affected_subsystems.append("utxo_psbt")
        if any(kw in title_lower for kw in ("taproot", "schnorr", "witness")):
            affected_subsystems.append("taproot_schnorr")
        if any(kw in title_lower for kw in ("op_return", "spell", "charm")):
            affected_subsystems.append("charms_integration")
        if not affected_subsystems:
            affected_subsystems.append("general")

        update_record = {
            "repo": repo,
            "issue": issue,
            "title": title,
            "url": url,
            "affected_subsystems": affected_subsystems,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        self._upstream_updates.append(update_record)
        self.memory.remember("tech_updates", {
            "type": "breaking_change",
            **update_record,
        })

        # Create action-plan knowledge node
        if self._store:
            from autono.knowledge.types import KnowledgeNode, VolatilityTier

            action_items = [
                f"- Review breaking change: {title}",
                f"- Affected subsystems: {', '.join(affected_subsystems)}",
            ]
            if "fee_estimation" in affected_subsystems:
                action_items.append(
                    "- Verify estimatesmartfee RPC still returns expected format"
                )
            if "rpc_api" in affected_subsystems:
                action_items.append(
                    "- Test Bitcoin RPC endpoint compatibility"
                )
            if "charms_integration" in affected_subsystems:
                action_items.append(
                    "- Coordinate with CharmsAgent on OP_RETURN / spell impact"
                )
            action_items.append(f"- Source: {url}")

            node = KnowledgeNode(
                content=(
                    f"ACTION PLAN — Breaking change in {repo} (#{issue}):\n"
                    f"{title}\n\n"
                    + "\n".join(action_items)
                ),
                domain="bitcoin",
                subdomain="action_plans",
                volatility=VolatilityTier.VOLATILE,
                priority_score=90,
                tags=["breaking-change", "action-plan", repo.split("/")[-1]],
            )
            self._store.save_node(node)

    async def _handle_security_advisory(self, payload: dict[str, Any]) -> None:
        """Handle a ``security_advisory`` broadcast from RepoWatcherAgent.

        Security advisories are critical.  Only act on Bitcoin-domain
        advisories — log at warning, store immediately.
        """
        repo = payload.get("repo", "")
        issue = payload.get("issue", "")
        title = payload.get("title", "")
        domain = payload.get("domain", "")
        url = payload.get("url", "")

        self.log.warning(
            "bitcoin.security_advisory",
            repo=repo,
            issue=issue,
            title=title,
            domain=domain,
        )

        if domain and domain not in ("bitcoin", "bitcoinos", "charms"):
            return

        update_record = {
            "repo": repo,
            "issue": issue,
            "title": title,
            "url": url,
            "severity": "critical",
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        self._upstream_updates.append(update_record)
        self.memory.remember("tech_updates", {
            "type": "security_advisory",
            **update_record,
        })

        if self._store:
            from autono.knowledge.types import KnowledgeNode, VolatilityTier

            node = KnowledgeNode(
                content=(
                    f"SECURITY ADVISORY — {repo} (#{issue}): {title}\n"
                    f"URL: {url}\n"
                    f"Priority: CRITICAL — assess impact on PSBT construction, "
                    f"fee estimation, and Charms cross-chain routing."
                ),
                domain="bitcoin",
                subdomain="security",
                volatility=VolatilityTier.VOLATILE,
                priority_score=99,
                tags=["security", "advisory", repo.split("/")[-1]],
            )
            self._store.save_node(node)

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "protocol_facts": len(self._protocol_facts),
            "cross_chain_routes": list(self._cross_chain_routes.keys()),
            "upstream_updates": len(self._upstream_updates),
        })
        return base
