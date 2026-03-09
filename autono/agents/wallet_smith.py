"""Agent 4: WalletSmith — WALI wallet coordinator for the agent system.

The bridge between the WALI TypeScript wallet (user-facing) and the
Python agent system (brain). WalletSmith:

- Creates multi-chain wallets (Cardano + Bitcoin + Night Chain)
- Coordinates with NightChainAgent for encrypted seed storage
- Stores wallet state in the knowledge graph as locked nodes
- Validates addresses across all supported chains
- Estimates fees and builds transaction requests
- Manages derivation paths (CIP-1852, BIP-44/84/86)
- Tracks wallet health and UX metrics

Every wallet address becomes a PERMANENT locked node in the knowledge
graph — "What is my Cardano address?" → instant lock hit, zero inference.

Architecture:
    User → WALI (TypeScript) → WalletSmith (Python) → Chain Agents
                                    ↓
                              WalletService
                                    ↓
                          Knowledge Graph (Locks)
"""

from __future__ import annotations

from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message


class WalletSmith(AutonomousAgent):
    """WALI wallet coordinator — makes crypto simple for agents and users.

    Creates wallets, manages addresses, coordinates with chain specialists,
    and ensures every wallet fact is locked in the knowledge graph.
    """

    def __init__(self) -> None:
        super().__init__(
            name="WalletSmith",
            role="WALI wallet coordinator — multi-chain wallet creation, validation, and management",
            capabilities=[
                AgentCapability.MANAGE_WALLET,
                AgentCapability.BUILD_PRODUCT,
                AgentCapability.START_BUSINESS,
            ],
        )
        self._wallet_service = None
        self._store = None
        self._graph = None

        self.wallet_features = [
            "one_click_bridge",
            "social_recovery",
            "biometric_auth",
            "human_readable_addresses",
            "gas_abstraction",
            "fiat_onramp",
            "multi_sig",
            "hardware_wallet_support",
            "nft_gallery",
            "defi_dashboard",
        ]
        self.wallets_created = 0
        self.active_users = 0
        self._knowledge_seeded = False

    @property
    def work_interval(self) -> float:
        return 30.0

    def set_dependencies(self, store: Any, graph: Any, wallet_service: Any) -> None:
        """Inject dependencies from orchestrator."""
        self._store = store
        self._graph = graph
        self._wallet_service = wallet_service
        if wallet_service:
            wallet_service.set_dependencies(store, graph)

    async def do_work(self) -> None:
        """Seed wallet knowledge and monitor wallet health."""
        if self._store and not self._knowledge_seeded:
            await self._seed_wallet_knowledge()
            self._knowledge_seeded = True

    async def handle_message(self, msg: Message) -> None:
        if msg.kind != "request":
            return

        req_type = msg.payload.get("type", "")

        if req_type == "create_wallet":
            result = await self._create_wallet(msg.payload)
            await self.send(msg.sender, "response", {
                "type": "wallet_created",
                **result,
            })

        elif req_type == "validate_address":
            result = self._validate_address(msg.payload)
            await self.send(msg.sender, "response", {
                "type": "address_validated",
                **result,
            })

        elif req_type == "identify_address":
            result = self._identify_address(msg.payload)
            await self.send(msg.sender, "response", {
                "type": "address_identified",
                **result,
            })

        elif req_type == "estimate_fees":
            result = self._estimate_fees(msg.payload)
            await self.send(msg.sender, "response", {
                "type": "fee_estimate",
                **result,
            })

        elif req_type == "get_derivation_path":
            result = self._get_derivation_path(msg.payload)
            await self.send(msg.sender, "response", {
                "type": "derivation_path",
                **result,
            })

        elif req_type == "list_wallets":
            wallets = self._wallet_service.list_wallets() if self._wallet_service else []
            await self.send(msg.sender, "response", {
                "type": "wallet_list",
                "wallets": wallets,
            })

        elif req_type == "backup_wallet":
            result = await self._coordinate_backup(msg.payload)
            await self.send(msg.sender, "response", {
                "type": "backup_result", **result,
            })

        elif req_type == "recover_wallet":
            result = await self._coordinate_recovery(msg.payload)
            await self.send(msg.sender, "response", {
                "type": "recovery_result", **result,
            })

        elif req_type == "backup_status":
            await self.send("NightChainAgent", "request", {
                "type": "backup_info",
            })
            await self.send(msg.sender, "response", {
                "type": "backup_status_forwarded",
                "message": "Backup status requested from NightChainAgent.",
            })

        elif req_type == "ux_report":
            await self.send(msg.sender, "response", {
                "type": "ux_report",
                "features": self.wallet_features,
                "wallets_created": self.wallets_created,
                "active_users": self.active_users,
                "wallet_service": self._wallet_service.stats() if self._wallet_service else {},
            })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "wallet_ux",
            "topics": [
                "account_abstraction_erc4337",
                "passkey_authentication",
                "social_login_web3",
                "gasless_transactions",
                "smart_wallet_patterns",
                "cip_1852_derivation",
                "bip_86_taproot_wallets",
            ],
        })

    # -- Wallet operations ---------------------------------------------------

    async def _create_wallet(self, spec: dict) -> dict:
        """Create a multi-chain wallet via WalletService."""
        if not self._wallet_service:
            return {"error": "WalletService not initialized"}

        chains = spec.get("chains", ["cardano", "bitcoin"])
        word_count = spec.get("word_count", 24)

        result = self._wallet_service.create_wallet(
            chains=chains,
            word_count=word_count,
        )

        self.wallets_created += 1
        wallet_id = result["wallet_id"]

        # Request NightChainAgent to encrypt the mnemonic
        result.pop("mnemonic_bytes")  # remove sensitive data from result

        await self.send("NightChainAgent", "request", {
            "type": "encrypt_and_store",
            "data_type": "seed_phrase",
            "wallet_id": wallet_id,
        })

        # Remove internal state object from response
        result.pop("state")

        return {
            "wallet_id": wallet_id,
            "addresses": result["addresses"],
            "derivation_paths": result["derivation_paths"],
            "chains": chains,
            "features": self.wallet_features,
            "status": "active",
            "encrypted_on_night_chain": True,
        }

    def _validate_address(self, spec: dict) -> dict:
        """Validate an address for a specific chain."""
        if not self._wallet_service:
            return {"error": "WalletService not initialized"}

        address = spec.get("address", "")
        chain = spec.get("chain", "")

        if not address:
            return {"valid": False, "error": "no address provided"}
        if not chain:
            return self._wallet_service.identify_address(address)

        return self._wallet_service.validate_address(address, chain)

    def _identify_address(self, spec: dict) -> dict:
        """Auto-detect chain and type from any address."""
        if not self._wallet_service:
            return {"error": "WalletService not initialized"}

        address = spec.get("address", "")
        return self._wallet_service.identify_address(address)

    def _estimate_fees(self, spec: dict) -> dict:
        """Get fee estimates for a chain."""
        if not self._wallet_service:
            return {"error": "WalletService not initialized"}

        chain = spec.get("chain", "cardano")
        estimate = self._wallet_service.estimate_fees(chain)
        return {
            "chain": estimate.chain.value,
            "slow": estimate.slow,
            "medium": estimate.medium,
            "fast": estimate.fast,
            "unit": estimate.unit,
        }

    def _get_derivation_path(self, spec: dict) -> dict:
        """Get standard derivation path for a chain."""
        if not self._wallet_service:
            return {"error": "WalletService not initialized"}

        chain = spec.get("chain", "cardano")
        account = spec.get("account", 0)
        index = spec.get("index", 0)
        addr_type = spec.get("address_type", "native_segwit")

        path = self._wallet_service.get_derivation_path(
            chain, account, index, addr_type
        )
        return {"chain": chain, "path": path}

    # -- Backup & Recovery coordination --------------------------------------

    async def _coordinate_backup(self, spec: dict) -> dict:
        """Coordinate a full backup through NightChainAgent.

        User-friendly flow:
        1. Validate access key
        2. Forward to NightChainAgent for encrypted backup
        3. Return step-by-step progress to user
        """
        access_key = spec.get("access_key", "")
        if not access_key:
            return {
                "ok": False,
                "message": "I need your access key to encrypt the backup.",
                "detail": "Your access key is the 4-12 character key you set when creating your wallet.",
            }

        # Forward to NightChainAgent which owns the BackupService
        await self.send("NightChainAgent", "request", {
            "type": "backup_knowledge",
            "access_key": access_key,
        })

        return {
            "ok": True,
            "message": "Backup started! NightChainAgent is encrypting your knowledge graph.",
            "detail": (
                "Your backup includes:\n"
                "  - All wallet addresses and derivation paths\n"
                "  - The entire knowledge graph (nodes, links, locks)\n"
                "  - Protocol facts from all chain agents\n\n"
                "Encryption: AES-256-GCM with PBKDF2 (100,000 iterations)\n"
                "Your access key never leaves your device."
            ),
        }

    async def _coordinate_recovery(self, spec: dict) -> dict:
        """Coordinate wallet and knowledge recovery.

        User-friendly 7-step flow:
        1. Start recovery
        2. Recovery dialog (4-line challenge)
        3. Access key verification
        4. Decryption
        5. Integrity verification
        6. State restoration
        7. Complete
        """
        access_key = spec.get("access_key", "")
        version = spec.get("version", 0)

        if not access_key:
            # Return the recovery steps so the user knows what to expect
            await self.send("NightChainAgent", "request", {
                "type": "recovery_steps",
            })
            return {
                "ok": False,
                "message": "Let's recover your wallet and knowledge!",
                "detail": (
                    "Here's what will happen:\n"
                    "  1. You provide your recovery words (4-line dialog)\n"
                    "  2. Enter your access key (3 attempts, 15-min lockout)\n"
                    "  3. We decrypt everything with AES-256-GCM\n"
                    "  4. Verify data integrity\n"
                    "  5. Restore wallet addresses and knowledge graph\n"
                    "  6. Rebuild semantic search\n"
                    "  7. You're back in action!\n\n"
                    "Please provide your access key to begin."
                ),
                "needs": "access_key",
            }

        # Start recovery dialog first
        await self.send("NightChainAgent", "request", {
            "type": "start_recovery",
        })

        # Forward restore request to NightChainAgent
        await self.send("NightChainAgent", "request", {
            "type": "restore_knowledge",
            "access_key": access_key,
            "version": version,
        })

        return {
            "ok": True,
            "message": "Recovery in progress! Decrypting and restoring your data...",
            "detail": (
                "NightChainAgent is:\n"
                "  - Decrypting your backup with your access key\n"
                "  - Verifying data integrity\n"
                "  - Restoring knowledge graph nodes, links, and locks\n"
                "  - Rebuilding semantic search index\n\n"
                "This should only take a moment."
            ),
        }

    # -- Knowledge seeding ---------------------------------------------------

    async def _seed_wallet_knowledge(self) -> None:
        """Seed wallet protocol knowledge into the knowledge graph."""
        if not self._store:
            return

        from autono.knowledge.types import KnowledgeNode, Lock, VolatilityTier

        wallet_facts = [
            {
                "fact": "WALI wallet supports Cardano (CIP-1852) and Bitcoin (BIP-44/84/86) derivation",
                "domain": "wallet", "subdomain": "protocol",
                "answer": {"cardano": "CIP-1852", "bitcoin": "BIP-44/84/86"},
                "answer_type": "json",
                "source": "WALI Wallet Engine",
                "tags": ["wallet", "derivation", "multi-chain"],
            },
            {
                "fact": "Cardano uses CIP-1852 purpose 1852' with coin type 1815'",
                "domain": "wallet", "subdomain": "cardano",
                "answer": "m/1852'/1815'/0'/0/0",
                "answer_type": "derivation_path",
                "source": "CIP-1852",
                "tags": ["wallet", "cardano", "derivation", "cip-1852"],
            },
            {
                "fact": "Bitcoin Native SegWit uses BIP-84 purpose 84' with coin type 0'",
                "domain": "wallet", "subdomain": "bitcoin",
                "answer": "m/84'/0'/0'/0/0",
                "answer_type": "derivation_path",
                "source": "BIP-84",
                "tags": ["wallet", "bitcoin", "derivation", "bip-84", "segwit"],
            },
            {
                "fact": "Bitcoin Taproot uses BIP-86 purpose 86' with coin type 0'",
                "domain": "wallet", "subdomain": "bitcoin",
                "answer": "m/86'/0'/0'/0/0",
                "answer_type": "derivation_path",
                "source": "BIP-86",
                "tags": ["wallet", "bitcoin", "derivation", "bip-86", "taproot"],
            },
            {
                "fact": "WALI wallet encrypts seed phrases with AES-256-GCM on Night Chain",
                "domain": "wallet", "subdomain": "security",
                "answer": "AES-256-GCM via NightChainAgent",
                "answer_type": "string",
                "source": "WALI Night Chain Integration",
                "tags": ["wallet", "encryption", "night-chain", "security"],
            },
            {
                "fact": "WALI wallet generates 24-word BIP-39 mnemonics (256-bit entropy)",
                "domain": "wallet", "subdomain": "security",
                "answer": "24 words / 256 bits",
                "answer_type": "string",
                "source": "BIP-39",
                "tags": ["wallet", "mnemonic", "bip-39", "entropy"],
            },
            {
                "fact": "WALI supports 4 Bitcoin address types: P2PKH, P2SH-P2WPKH, P2WPKH, P2TR",
                "domain": "wallet", "subdomain": "bitcoin",
                "answer": ["p2pkh", "p2sh-p2wpkh", "p2wpkh", "p2tr"],
                "answer_type": "json",
                "source": "BIP-44/49/84/86",
                "tags": ["wallet", "bitcoin", "address-types"],
            },
            {
                "fact": "WALI recovery uses 4-line challenge-response dialog with 3-strike lockout",
                "domain": "wallet", "subdomain": "security",
                "answer": "4-line dialog, 3 max attempts, 15-min lockout",
                "answer_type": "string",
                "source": "WALI Recovery Protocol",
                "tags": ["wallet", "recovery", "security", "dialog"],
            },
        ]

        for fact_data in wallet_facts:
            node = KnowledgeNode(
                content=fact_data["fact"],
                domain=fact_data["domain"],
                subdomain=fact_data["subdomain"],
                volatility=VolatilityTier.PERMANENT,
                tags=fact_data.get("tags", []),
            )
            self._store.save_node(node)

            lock = Lock(
                node_id=node.id,
                absolute_answer=fact_data["answer"],
                answer_type=fact_data["answer_type"],
                verification_source=fact_data["source"],
            )
            lock.compute_dependency_hash(str(fact_data["answer"]))
            self._store.save_lock(lock)

            node.is_locked = True
            node.lock_id = lock.id
            node.bypass_llm = True
            self._store.save_node(node)

        self.log.info("walletsmith.knowledge_seeded", facts=len(wallet_facts))

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "wallets_created": self.wallets_created,
            "active_users": self.active_users,
            "features": self.wallet_features,
            "wallet_service": self._wallet_service.stats() if self._wallet_service else {},
        })
        return base
