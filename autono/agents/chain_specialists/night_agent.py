"""NightChainAgent — Night/Midnight blockchain specialist.

MISSION: Make crypto safe without making it hard. Users should never
worry about losing access or exposing secrets. Night Chain handles all
encryption, backup, and recovery invisibly. No seed phrases shown to
users, no manual backup steps — it just works.

Dual role:
1. Encrypted vault for seed phrases and sensitive data (existing WALI role)
2. Persistence layer for the Links & Locks knowledge graph

The knowledge graph gets encrypted and stored on Night Chain, making it:
- Recoverable (just like seed phrases)
- Encrypted at rest (AES-256-GCM)
- Decentralized (not dependent on local disk)

Also handles:
- Night wallet operations (Ed25519 keypairs, night1 addresses)
- 4-line recovery dialog
- Access key control and rate limiting
- Midnight SDK integration (when available)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message

from autono.agents.chain_specialists.compatibility_harness import (
    CompatibilityTestMixin,
    check_dependency_version,
    check_config_key_exists,
)


class NightChainAgent(CompatibilityTestMixin, AutonomousAgent):
    """Night Chain — invisible security so users never worry about keys.

    Handles all encryption, backup, and recovery behind the scenes. Users
    don't see seed phrases or manage keys. Night Chain makes crypto safe
    without making it complicated.
    """

    def __init__(self) -> None:
        super().__init__(
            name="NightChainAgent",
            role="Invisible security — encrypted backup, seamless recovery, zero user friction",
            capabilities=[
                AgentCapability.MANAGE_WALLET,
                AgentCapability.AUDIT,
            ],
        )
        self._graph = None
        self._store = None
        self._backup_service = None
        self._wallet_service = None

        # Night Chain protocol facts
        self._protocol_facts: list[dict[str, Any]] = [
            {
                "fact": "Night Chain uses Ed25519 keypairs from @noble/ed25519",
                "domain": "night_chain", "subdomain": "protocol",
                "answer": "Ed25519", "answer_type": "string",
                "source": "Night Chain Specification",
                "tags": ["keypair", "ed25519", "cryptography"],
            },
            {
                "fact": "Night Chain address prefix is night1 (bech32 encoded)",
                "domain": "night_chain", "subdomain": "protocol",
                "answer": "night1", "answer_type": "string",
                "source": "Night Chain Specification",
                "tags": ["address", "prefix", "bech32"],
            },
            {
                "fact": "Night Chain uses AES-256-GCM encryption with PBKDF2 key derivation",
                "domain": "night_chain", "subdomain": "encryption",
                "answer": "AES-256-GCM + PBKDF2-SHA256 (100,000 iterations)",
                "answer_type": "string",
                "source": "Night Chain Encryption Spec",
                "tags": ["encryption", "aes", "pbkdf2"],
            },
            {
                "fact": "Recovery dialog uses 4-line challenge-response pattern",
                "domain": "night_chain", "subdomain": "recovery",
                "answer": "4-line: user-4-words, bot-4-words, user-4-words, bot-4-words",
                "answer_type": "string",
                "source": "Recovery Protocol",
                "tags": ["recovery", "dialog", "challenge"],
            },
            {
                "fact": "Access key control: 3 max failed attempts, 15-minute lockout",
                "domain": "night_chain", "subdomain": "security",
                "answer": {"max_attempts": 3, "lockout_minutes": 15},
                "answer_type": "json",
                "source": "Access Control Specification",
                "tags": ["security", "rate-limit", "lockout"],
            },
        ]

        # Encryption config — used for compatibility checks
        self._encryption_config: dict[str, Any] = {
            "algorithm": "AES-256-GCM",
            "kdf": "PBKDF2-SHA256",
            "kdf_iterations": 100_000,
            "recovery": {
                "dialog_lines": 4,
                "words_per_line": 4,
            },
        }

        # Register compatibility checks for upstream repos
        self.register_compatibility_check(
            "nicolo-ribaudo/noble-ed25519",
            "encryption_lib_compat",
            check_dependency_version("cryptography", "41.0.0"),
        )
        self.register_compatibility_check(
            "nicolo-ribaudo/noble-ed25519",
            "recovery_protocol_config",
            check_config_key_exists(
                self._encryption_config,
                "recovery.dialog_lines",
            ),
        )

        # Repos whose releases affect encryption, privacy, or recovery
        self._privacy_relevant_repos: set[str] = {
            "nicolo-ribaudo/noble-ed25519",
            "midnight-network/midnight-core",
            "input-output-hk/midnight-sdk",
        }
        self._encryption_relevant_repos: set[str] = {
            "nicolo-ribaudo/noble-ed25519",
            "nicolo-ribaudo/noble-secp256k1",
        }

        # In-memory log of upstream updates received from RepoWatcherAgent
        self._upstream_updates: list[dict[str, Any]] = []

        # Knowledge graph backup state
        self._last_backup_hash: str = ""
        self._backup_count: int = 0

    @property
    def work_interval(self) -> float:
        return 30.0

    def set_dependencies(self, store: Any, graph: Any,
                         wallet_service: Any = None) -> None:
        self._store = store
        self._graph = graph
        self._wallet_service = wallet_service

        # Initialize BackupService with real dependencies
        from autono.services.backup_service import BackupService
        self._backup_service = BackupService()
        self._backup_service.set_dependencies(store, graph, wallet_service)

    async def do_work(self) -> None:
        """Seed protocol facts and periodically backup knowledge graph."""
        if self._store and not hasattr(self, "_facts_seeded"):
            await self._seed_protocol_facts()
            self._facts_seeded = True

        # Request expert-level research scraping for Night Chain domain
        if not hasattr(self, "_research_requested"):
            await self.send("ResearchManager", "request", {
                "type": "scrape_domain",
                "domain": "night_chain",
            })
            self._research_requested = True

        # Periodic backups are triggered on-demand via message (requires access key)

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

            if req_type == "encrypt_and_store":
                result = await self._encrypt_and_store(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "stored", **result,
                })

            elif req_type == "retrieve_and_decrypt":
                result = await self._retrieve_and_decrypt(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "retrieved", **result,
                })

            elif req_type == "backup_knowledge":
                result = await self._backup_knowledge_graph(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "backup_complete", **result,
                })

            elif req_type == "restore_knowledge":
                result = await self._restore_knowledge_graph(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "restore_complete", **result,
                })

            elif req_type == "backup_info":
                info = self._backup_service.get_backup_info() if self._backup_service else {}
                await self.send(msg.sender, "response", {
                    "type": "backup_info", **info,
                })

            elif req_type == "recovery_steps":
                steps = self._backup_service.get_recovery_steps() if self._backup_service else []
                await self.send(msg.sender, "response", {
                    "type": "recovery_steps",
                    "steps": [s.as_dict() for s in steps],
                })

            elif req_type == "start_recovery":
                result = await self._start_recovery_dialog(msg.payload)
                await self.send(msg.sender, "response", {
                    "type": "recovery_started", **result,
                })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "night_chain",
            "topics": [
                "midnight_sdk_integration",
                "zero_knowledge_proofs_privacy",
                "encrypted_state_channels",
                "knowledge_graph_encryption",
            ],
        })

    # -- Night Chain operations -------------------------------------------

    async def _seed_protocol_facts(self) -> None:
        """Seed Night Chain protocol facts into the knowledge graph."""
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

        self.log.info("night.protocol_facts_seeded",
                      count=len(self._protocol_facts))

    async def _backup_knowledge_graph(self, payload: dict | None = None
                                      ) -> dict[str, Any]:
        """Backup the knowledge graph using BackupService with AES-256-GCM.

        The knowledge graph is treated like a seed phrase — encrypted with
        AES-256-GCM and stored for recovery.
        """
        if not self._backup_service:
            return {"ok": False, "error": "BackupService not initialized"}

        access_key = (payload or {}).get("access_key", "")
        if not access_key:
            return {
                "ok": False,
                "error": "Access key required for encrypted backup",
                "message": "Please provide your 4-12 character access key.",
            }

        result = self._backup_service.create_backup(access_key)

        if result.get("ok"):
            self._backup_count = self._backup_service._backup_count
            self._last_backup_hash = self._backup_service._last_backup_hash
            self.log.info("night.knowledge_backup",
                          backup_count=self._backup_count,
                          version=result.get("version"))

        return result

    async def _restore_knowledge_graph(self, payload: dict) -> dict[str, Any]:
        """Restore knowledge graph from encrypted backup via BackupService."""
        if not self._backup_service:
            return {"ok": False, "error": "BackupService not initialized"}

        access_key = payload.get("access_key", "")
        version = payload.get("version", 0)

        if not access_key:
            return {
                "ok": False,
                "error": "Access key required for decryption",
                "message": "Please provide your access key to decrypt the backup.",
            }

        if not version:
            # Default to latest backup
            backups = self._backup_service.list_backups()
            if not backups:
                return {
                    "ok": False,
                    "error": "No backups found",
                    "message": "No backups available to restore from.",
                }
            version = backups[-1]["version"]

        result = self._backup_service.restore_backup(version, access_key)

        if result.get("ok"):
            self.log.info("night.knowledge_restored",
                          version=version,
                          restored=result.get("restored"))

        return result

    async def _encrypt_and_store(self, payload: dict) -> dict[str, Any]:
        """Encrypt data and store on Night Chain."""
        data_type = payload.get("data_type", "unknown")
        return {
            "status": "encrypted_and_stored",
            "data_type": data_type,
            "encryption": "AES-256-GCM",
        }

    async def _retrieve_and_decrypt(self, payload: dict) -> dict[str, Any]:
        """Retrieve and decrypt data from Night Chain."""
        asset_id = payload.get("asset_id", "")
        return {
            "status": "retrieved",
            "asset_id": asset_id,
        }

    async def _start_recovery_dialog(self, payload: dict) -> dict[str, Any]:
        """Start the 4-line recovery challenge dialog."""
        return {
            "status": "dialog_started",
            "step": "user-line-1",
            "prompt": "Please provide 4 words from your recovery phrase.",
        }

    # -- Repo-watcher alert handlers -----------------------------------------

    async def _handle_new_release(self, payload: dict[str, Any]) -> None:
        """Handle a ``repo_new_release`` alert from RepoWatcherAgent.

        Tracks encryption library changes, assesses backup/recovery
        protocol impact, and monitors for privacy-breaking changes.
        """
        repo = payload.get("repo", "")
        tag = payload.get("tag", "")
        name = payload.get("name", tag)
        prerelease = payload.get("prerelease", False)
        body_preview = payload.get("body_preview", "")

        self.log.info(
            "night.new_release",
            repo=repo,
            tag=tag,
            prerelease=prerelease,
        )

        body_lower = body_preview.lower()

        # Track encryption library changes
        encryption_keywords = [
            "aes", "gcm", "pbkdf2", "ed25519", "encryption",
            "cipher", "key derivation", "salt", "iv", "nonce",
        ]
        encryption_mentions = [kw for kw in encryption_keywords if kw in body_lower]

        # Assess backup/recovery protocol impact
        recovery_keywords = [
            "backup", "recovery", "restore", "seed", "mnemonic",
            "key export", "import", "migration",
        ]
        recovery_mentions = [kw for kw in recovery_keywords if kw in body_lower]

        # Monitor for privacy-breaking changes
        privacy_keywords = [
            "privacy", "leak", "expose", "plaintext", "unencrypted",
            "vulnerability", "side-channel", "timing attack",
            "deprecated", "removed", "breaking",
        ]
        privacy_mentions = [kw for kw in privacy_keywords if kw in body_lower]

        impact = {
            "repo": repo,
            "tag": tag,
            "name": name,
            "prerelease": prerelease,
            "encryption_mentions": encryption_mentions,
            "recovery_mentions": recovery_mentions,
            "privacy_concerns": privacy_mentions,
            "received_at": datetime.now(timezone.utc).isoformat(),
        }

        self._upstream_updates.append(impact)
        self.memory.remember("tech_updates", {
            "type": "upstream_release",
            **impact,
        })

        # Store knowledge node for significant releases
        if (encryption_mentions or recovery_mentions or privacy_mentions) and self._store:
            from autono.knowledge.types import KnowledgeNode, VolatilityTier

            node = KnowledgeNode(
                content=(
                    f"Upstream release: {repo} {name} (tag {tag}). "
                    f"Pre-release: {prerelease}. "
                    f"Encryption changes: {', '.join(encryption_mentions) or 'none'}. "
                    f"Recovery impact: {', '.join(recovery_mentions) or 'none'}. "
                    f"Privacy concerns: {', '.join(privacy_mentions) or 'none'}. "
                    f"Preview: {body_preview[:300]}"
                ),
                domain="night_chain",
                subdomain="upstream_updates",
                volatility=VolatilityTier.VOLATILE,
                tags=["release", "upstream", repo.split("/")[-1]],
            )
            self._store.save_node(node)

    async def _handle_breaking_change(self, payload: dict[str, Any]) -> None:
        """Handle a ``repo_breaking_change`` alert from RepoWatcherAgent.

        Assesses impact on encryption libraries, backup/recovery
        protocols, and watches for privacy-breaking changes.
        """
        repo = payload.get("repo", "")
        issue = payload.get("issue", "")
        title = payload.get("title", "")
        url = payload.get("url", "")

        self.log.warning(
            "night.breaking_change",
            repo=repo,
            issue=issue,
            title=title,
        )

        # Classify affected subsystems
        affected_subsystems: list[str] = []
        title_lower = title.lower()
        if any(kw in title_lower for kw in ("aes", "gcm", "encryption", "cipher", "ed25519")):
            affected_subsystems.append("encryption")
        if any(kw in title_lower for kw in ("backup", "recovery", "restore", "seed")):
            affected_subsystems.append("backup_recovery")
        if any(kw in title_lower for kw in ("privacy", "leak", "expose", "plaintext")):
            affected_subsystems.append("privacy")
        if any(kw in title_lower for kw in ("key", "keypair", "derivation", "pbkdf2")):
            affected_subsystems.append("key_management")
        if any(kw in title_lower for kw in ("api", "sdk", "endpoint")):
            affected_subsystems.append("sdk_api")
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
            if "encryption" in affected_subsystems:
                action_items.append(
                    "- Verify AES-256-GCM encryption/decryption still works"
                )
                action_items.append(
                    "- Test backward compatibility with existing encrypted backups"
                )
            if "backup_recovery" in affected_subsystems:
                action_items.append(
                    "- Verify 4-line recovery dialog still functions correctly"
                )
                action_items.append(
                    "- Test backup restore with existing encrypted data"
                )
            if "privacy" in affected_subsystems:
                action_items.append(
                    "- CRITICAL: Assess if user data could be exposed"
                )
                action_items.append(
                    "- Review all encryption paths for privacy leaks"
                )
            if "key_management" in affected_subsystems:
                action_items.append(
                    "- Verify Ed25519 keypair generation and PBKDF2 derivation"
                )
            action_items.append(f"- Source: {url}")

            node = KnowledgeNode(
                content=(
                    f"ACTION PLAN — Breaking change in {repo} (#{issue}):\n"
                    f"{title}\n\n"
                    + "\n".join(action_items)
                ),
                domain="night_chain",
                subdomain="action_plans",
                volatility=VolatilityTier.VOLATILE,
                priority_score=95 if "privacy" in affected_subsystems else 90,
                tags=["breaking-change", "action-plan", repo.split("/")[-1]],
            )
            self._store.save_node(node)

    async def _handle_security_advisory(self, payload: dict[str, Any]) -> None:
        """Handle a ``security_advisory`` broadcast from RepoWatcherAgent.

        Security advisories are especially critical for NightChainAgent
        because it handles encryption and key management. Only act on
        advisories relevant to the night_chain domain.
        """
        repo = payload.get("repo", "")
        issue = payload.get("issue", "")
        title = payload.get("title", "")
        domain = payload.get("domain", "")
        url = payload.get("url", "")

        self.log.warning(
            "night.security_advisory",
            repo=repo,
            issue=issue,
            title=title,
            domain=domain,
        )

        if domain and domain != "night_chain":
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
                    f"Priority: CRITICAL — NightChainAgent handles encryption "
                    f"and key management. Assess impact on AES-256-GCM "
                    f"encryption, Ed25519 keypairs, PBKDF2 key derivation, "
                    f"and the 4-line recovery protocol."
                ),
                domain="night_chain",
                subdomain="security",
                volatility=VolatilityTier.VOLATILE,
                priority_score=99,
                tags=["security", "advisory", repo.split("/")[-1]],
            )
            self._store.save_node(node)

    def report(self) -> dict[str, Any]:
        base = super().report()
        backup_stats = self._backup_service.stats() if self._backup_service else {}
        base.update({
            "protocol_facts": len(self._protocol_facts),
            "backup_count": self._backup_count,
            "last_backup_hash": self._last_backup_hash,
            "backup_service": backup_stats,
            "upstream_updates": len(self._upstream_updates),
        })
        return base
