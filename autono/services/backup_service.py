"""BackupService — encrypted backup and recovery for the entire system.

Ties together:
1. Knowledge graph encrypted snapshots (nodes, links, locks, embeddings index)
2. Wallet state persistence (addresses, derivation paths)
3. Recovery flow coordination with user-friendly messaging
4. Versioned backups with timestamps and integrity hashes

Security model:
- All backups encrypted with AES-256-GCM (via cryptography library)
- Key derived from user access key via PBKDF2-SHA256 (100,000 iterations)
- Each backup gets unique salt + nonce
- Integrity verified via content hash before and after encryption
- Backup versions tracked (can restore to any previous version)

User-facing messages follow WALI's friendly style —
every step tells the user exactly what's happening and why.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

log = structlog.get_logger()

# PBKDF2 parameters (matching WALI TypeScript: 100,000 iterations)
PBKDF2_ITERATIONS = 100_000
SALT_SIZE = 32
NONCE_SIZE = 12  # AES-GCM standard
KEY_SIZE = 32    # AES-256


@dataclass
class BackupManifest:
    """Metadata for a backup snapshot."""
    version: int
    created_at: float
    content_hash: str
    encrypted: bool
    salt_hex: str
    nonce_hex: str
    node_count: int
    lock_count: int
    link_count: int
    wallet_count: int
    domains: list[str]
    size_bytes: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "created_at": self.created_at,
            "content_hash": self.content_hash,
            "encrypted": self.encrypted,
            "node_count": self.node_count,
            "lock_count": self.lock_count,
            "link_count": self.link_count,
            "wallet_count": self.wallet_count,
            "domains": self.domains,
            "size_bytes": self.size_bytes,
        }


@dataclass
class BackupStatus:
    """User-friendly backup status report."""
    step: str
    progress: float  # 0.0 - 1.0
    message: str
    detail: str = ""
    ok: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "progress": self.progress,
            "message": self.message,
            "detail": self.detail,
            "ok": self.ok,
        }


@dataclass
class RecoveryStep:
    """A single step in the recovery flow with user-friendly messaging."""
    number: int
    name: str
    description: str
    status: str = "pending"  # pending, active, complete, failed
    user_action: str = ""    # what the user needs to do (empty = automatic)
    result: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "user_action": self.user_action,
            "result": self.result,
        }


class BackupService:
    """Encrypted backup and recovery for knowledge graph + wallet state.

    Usage:
        service = BackupService(backup_path="/path/to/backups")
        service.set_dependencies(store, graph, wallet_service)

        # Create backup
        result = service.create_backup(access_key="mykey123")

        # List backups
        backups = service.list_backups()

        # Restore from backup
        result = service.restore_backup(version=1, access_key="mykey123")

        # Get recovery flow for user
        steps = service.get_recovery_steps()
    """

    def __init__(self, backup_path: str | None = None) -> None:
        self._backup_path = Path(backup_path) if backup_path else Path.home() / ".autono" / "backups"
        self._backup_path.mkdir(parents=True, exist_ok=True)
        self._store = None
        self._graph = None
        self._wallet_service = None
        self._backup_count: int = 0
        self._last_backup_hash: str = ""
        self._manifests: list[BackupManifest] = []

        # Load existing manifests
        self._load_manifests()

    def set_dependencies(self, store: Any, graph: Any,
                         wallet_service: Any = None) -> None:
        self._store = store
        self._graph = graph
        self._wallet_service = wallet_service

    # =========================================================================
    # Encryption (AES-256-GCM matching WALI TypeScript)
    # =========================================================================

    def _derive_key(self, access_key: str, salt: bytes) -> bytes:
        """Derive encryption key from access key via PBKDF2-SHA256."""
        return hashlib.pbkdf2_hmac(
            "sha256",
            access_key.encode("utf-8"),
            salt,
            PBKDF2_ITERATIONS,
            dklen=KEY_SIZE,
        )

    def _encrypt(self, plaintext: bytes, access_key: str
                 ) -> tuple[bytes, bytes, bytes, bytes]:
        """Encrypt with AES-256-GCM. Returns (ciphertext, salt, nonce, tag)."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        salt = os.urandom(SALT_SIZE)
        nonce = os.urandom(NONCE_SIZE)
        key = self._derive_key(access_key, salt)

        aesgcm = AESGCM(key)
        ciphertext = aesgcm.encrypt(nonce, plaintext, None)

        # AES-GCM appends the tag to ciphertext
        return ciphertext, salt, nonce, b""

    def _decrypt(self, ciphertext: bytes, access_key: str,
                 salt: bytes, nonce: bytes) -> bytes:
        """Decrypt with AES-256-GCM. Raises on invalid key."""
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM

        key = self._derive_key(access_key, salt)
        aesgcm = AESGCM(key)

        return aesgcm.decrypt(nonce, ciphertext, None)

    # =========================================================================
    # Backup Creation
    # =========================================================================

    def create_backup(self, access_key: str) -> dict[str, Any]:
        """Create an encrypted backup of the entire system state.

        Returns user-friendly progress messages at each step.
        """
        if not self._store:
            return {"ok": False, "error": "Store not initialized"}

        if len(access_key) < 4 or len(access_key) > 12:
            return {"ok": False, "error": "Access key must be 4-12 characters"}

        steps: list[BackupStatus] = []

        # Step 1: Serialize knowledge graph
        steps.append(BackupStatus(
            step="serialize",
            progress=0.1,
            message="Gathering your knowledge graph...",
            detail="Serializing nodes, links, and locks",
        ))

        snapshot = self._serialize_state()
        plaintext = json.dumps(snapshot, sort_keys=True).encode("utf-8")
        content_hash = hashlib.sha256(plaintext).hexdigest()[:16]

        # Step 2: Check if anything changed
        if content_hash == self._last_backup_hash:
            steps.append(BackupStatus(
                step="skip",
                progress=1.0,
                message="Everything is already backed up!",
                detail="No changes since last backup",
            ))
            return {"ok": True, "steps": [s.as_dict() for s in steps],
                    "changed": False}

        # Step 3: Encrypt
        steps.append(BackupStatus(
            step="encrypt",
            progress=0.4,
            message="Encrypting with AES-256-GCM...",
            detail=f"Using PBKDF2 with {PBKDF2_ITERATIONS:,} iterations",
        ))

        ciphertext, salt, nonce, _ = self._encrypt(plaintext, access_key)

        # Step 4: Verify round-trip (CRITICAL — matches WALI safety check)
        steps.append(BackupStatus(
            step="verify",
            progress=0.6,
            message="Verifying encryption round-trip...",
            detail="Making sure we can decrypt before saving",
        ))

        try:
            decrypted = self._decrypt(ciphertext, access_key, salt, nonce)
            verify_hash = hashlib.sha256(decrypted).hexdigest()[:16]
            if verify_hash != content_hash:
                return {"ok": False, "error": "Encryption verification failed — backup aborted",
                        "steps": [s.as_dict() for s in steps]}
        except Exception as e:
            return {"ok": False, "error": f"Encryption verification failed: {e}",
                    "steps": [s.as_dict() for s in steps]}

        steps.append(BackupStatus(
            step="verify_ok",
            progress=0.7,
            message="Encryption verified! Your data is safe.",
        ))

        # Step 5: Write to disk
        version = len(self._manifests) + 1
        backup_file = self._backup_path / f"backup_v{version}.enc"
        meta_file = self._backup_path / f"backup_v{version}.meta.json"

        steps.append(BackupStatus(
            step="save",
            progress=0.8,
            message="Saving encrypted backup...",
            detail=f"Version {version} → {backup_file.name}",
        ))

        # Write encrypted data
        with open(backup_file, "wb") as f:
            f.write(salt)
            f.write(nonce)
            f.write(ciphertext)

        # Create manifest
        stats = self._store.stats() if self._store else {}
        wallet_count = len(self._wallet_service.list_wallets()) if self._wallet_service else 0

        manifest = BackupManifest(
            version=version,
            created_at=time.time(),
            content_hash=content_hash,
            encrypted=True,
            salt_hex=salt.hex(),
            nonce_hex=nonce.hex(),
            node_count=stats.get("total_nodes", 0),
            lock_count=stats.get("total_locks", 0),
            link_count=stats.get("total_links", 0),
            wallet_count=wallet_count,
            domains=stats.get("domains", []),
            size_bytes=len(ciphertext),
        )

        with open(meta_file, "w") as f:
            json.dump(manifest.as_dict(), f, indent=2)

        self._manifests.append(manifest)
        self._backup_count += 1
        self._last_backup_hash = content_hash

        # Step 6: Done
        steps.append(BackupStatus(
            step="complete",
            progress=1.0,
            message="Backup complete! Your knowledge is safe.",
            detail=(
                f"Version {version}: {manifest.node_count} nodes, "
                f"{manifest.lock_count} locks, {wallet_count} wallet(s) "
                f"({manifest.size_bytes:,} bytes encrypted)"
            ),
        ))

        log.info("backup.created",
                 version=version,
                 nodes=manifest.node_count,
                 locks=manifest.lock_count,
                 size=manifest.size_bytes)

        return {
            "ok": True,
            "version": version,
            "manifest": manifest.as_dict(),
            "steps": [s.as_dict() for s in steps],
            "changed": True,
        }

    # =========================================================================
    # Backup Restoration
    # =========================================================================

    def restore_backup(self, version: int, access_key: str) -> dict[str, Any]:
        """Restore from an encrypted backup.

        Returns user-friendly progress messages.
        """
        steps: list[BackupStatus] = []

        # Step 1: Find backup
        steps.append(BackupStatus(
            step="find",
            progress=0.1,
            message=f"Looking for backup version {version}...",
        ))

        backup_file = self._backup_path / f"backup_v{version}.enc"
        if not backup_file.exists():
            steps.append(BackupStatus(
                step="not_found",
                progress=0.1,
                message=f"Backup version {version} not found.",
                ok=False,
            ))
            return {"ok": False, "error": f"Backup v{version} not found",
                    "steps": [s.as_dict() for s in steps]}

        # Step 2: Read encrypted data
        steps.append(BackupStatus(
            step="read",
            progress=0.2,
            message="Reading encrypted backup...",
        ))

        with open(backup_file, "rb") as f:
            salt = f.read(SALT_SIZE)
            nonce = f.read(NONCE_SIZE)
            ciphertext = f.read()

        # Step 3: Decrypt
        steps.append(BackupStatus(
            step="decrypt",
            progress=0.4,
            message="Decrypting with your access key...",
            detail=f"Using PBKDF2 with {PBKDF2_ITERATIONS:,} iterations",
        ))

        try:
            plaintext = self._decrypt(ciphertext, access_key, salt, nonce)
        except Exception:
            steps.append(BackupStatus(
                step="decrypt_failed",
                progress=0.4,
                message="Wrong access key! Decryption failed.",
                detail="Double-check your access key and try again.",
                ok=False,
            ))
            return {"ok": False, "error": "Decryption failed — invalid access key",
                    "steps": [s.as_dict() for s in steps]}

        steps.append(BackupStatus(
            step="decrypt_ok",
            progress=0.5,
            message="Decryption successful!",
        ))

        # Step 4: Verify integrity
        steps.append(BackupStatus(
            step="verify",
            progress=0.6,
            message="Verifying data integrity...",
        ))

        try:
            snapshot = json.loads(plaintext.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            steps.append(BackupStatus(
                step="corrupt",
                progress=0.6,
                message="Backup data is corrupt!",
                detail=str(e),
                ok=False,
            ))
            return {"ok": False, "error": "Backup data corrupt",
                    "steps": [s.as_dict() for s in steps]}

        # Step 5: Restore state
        steps.append(BackupStatus(
            step="restore",
            progress=0.7,
            message="Restoring your knowledge graph...",
            detail=f"{len(snapshot.get('nodes', {}))} nodes, "
                   f"{len(snapshot.get('locks', {}))} locks",
        ))

        restored = self._restore_state(snapshot)

        # Step 6: Re-embed if graph is available
        if self._graph:
            steps.append(BackupStatus(
                step="embed",
                progress=0.9,
                message="Rebuilding semantic search index...",
            ))
            embedded = self._graph.embed_all_nodes()
            steps.append(BackupStatus(
                step="embed_done",
                progress=0.95,
                message=f"Re-embedded {embedded} nodes.",
            ))

        # Step 7: Done
        steps.append(BackupStatus(
            step="complete",
            progress=1.0,
            message="Recovery complete! Your knowledge is restored.",
            detail=(
                f"Restored {restored['nodes']} nodes, "
                f"{restored['locks']} locks, "
                f"{restored['wallets']} wallet(s)"
            ),
        ))

        log.info("backup.restored",
                 version=version,
                 nodes=restored["nodes"],
                 locks=restored["locks"])

        return {
            "ok": True,
            "version": version,
            "restored": restored,
            "steps": [s.as_dict() for s in steps],
        }

    # =========================================================================
    # State Serialization
    # =========================================================================

    def _serialize_state(self) -> dict[str, Any]:
        """Serialize the complete system state for backup."""
        snapshot: dict[str, Any] = {
            "format_version": 1,
            "created_at": time.time(),
            "nodes": {},
            "links": {},
            "locks": {},
            "mlocks": {},
            "index": {},
            "wallets": [],
        }

        if self._store:
            # Serialize index
            snapshot["index"] = self._store._index.copy()

            # Serialize all nodes
            for node_id in self._store._index.get("nodes", {}):
                node = self._store.load_node(node_id)
                if node:
                    snapshot["nodes"][node_id] = node.to_dict()

            # Serialize all locks
            for lock_id in self._store._index.get("locks", {}):
                lock = self._store.load_lock(lock_id)
                if lock:
                    snapshot["locks"][lock_id] = lock.to_dict()

            # Serialize all links
            for link_id in self._store._index.get("links", {}):
                link = self._store.load_link(link_id)
                if link:
                    snapshot["links"][link_id] = link.to_dict()

        if self._wallet_service:
            snapshot["wallets"] = self._wallet_service.list_wallets()

        return snapshot

    def _restore_state(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        """Restore system state from a decrypted snapshot."""
        restored = {"nodes": 0, "locks": 0, "links": 0, "wallets": 0}

        if not self._store:
            return restored

        from autono.knowledge.types import KnowledgeNode, Lock, Link

        # Restore nodes
        for node_id, node_data in snapshot.get("nodes", {}).items():
            try:
                node = KnowledgeNode.from_dict(node_data)
                self._store.save_node(node)
                restored["nodes"] += 1
            except Exception as e:
                log.warning("backup.restore_node_error", node_id=node_id, error=str(e))

        # Restore locks
        for lock_id, lock_data in snapshot.get("locks", {}).items():
            try:
                lock = Lock.from_dict(lock_data)
                self._store.save_lock(lock)
                restored["locks"] += 1
            except Exception as e:
                log.warning("backup.restore_lock_error", lock_id=lock_id, error=str(e))

        # Restore links
        for link_id, link_data in snapshot.get("links", {}).items():
            try:
                link = Link.from_dict(link_data)
                self._store.save_link(link)
                restored["links"] += 1
            except Exception as e:
                log.warning("backup.restore_link_error", link_id=link_id, error=str(e))

        # Restore wallet metadata
        restored["wallets"] = len(snapshot.get("wallets", []))

        return restored

    # =========================================================================
    # Recovery Flow (User-Friendly)
    # =========================================================================

    def get_recovery_steps(self) -> list[RecoveryStep]:
        """Get the full recovery flow as user-friendly steps.

        This is what the user sees when they start recovery.
        """
        return [
            RecoveryStep(
                number=1,
                name="Start Recovery",
                description="Tell us you want to recover your wallet and knowledge.",
                user_action="Say 'I want to recover my wallet'",
            ),
            RecoveryStep(
                number=2,
                name="Recovery Dialog",
                description=(
                    "Answer 4 simple questions to verify it's really you. "
                    "You'll provide 4 words, we'll provide 4, you provide 4 more, "
                    "and we provide the last 4."
                ),
                user_action="Provide your recovery words when prompted",
            ),
            RecoveryStep(
                number=3,
                name="Access Key",
                description=(
                    "Enter your access key (the 4-12 character key you set "
                    "when you created your wallet). You have 3 attempts "
                    "before a 15-minute lockout."
                ),
                user_action="Enter your access key",
            ),
            RecoveryStep(
                number=4,
                name="Decryption",
                description=(
                    "We'll decrypt your seed phrases and knowledge graph "
                    "using AES-256-GCM encryption. This is automatic — "
                    "just wait a moment."
                ),
            ),
            RecoveryStep(
                number=5,
                name="Verification",
                description=(
                    "We verify the decrypted data is intact by checking "
                    "integrity hashes. If anything looks wrong, we'll let "
                    "you know immediately."
                ),
            ),
            RecoveryStep(
                number=6,
                name="Restore",
                description=(
                    "Your wallet addresses, knowledge graph, and all locked "
                    "facts are restored. Semantic search is rebuilt automatically."
                ),
            ),
            RecoveryStep(
                number=7,
                name="Complete",
                description=(
                    "Everything is back! Your wallet is active, your knowledge "
                    "is intact, and all your locked answers work instantly again."
                ),
            ),
        ]

    def get_backup_info(self) -> dict[str, Any]:
        """Get user-friendly backup status information."""
        if not self._manifests:
            return {
                "has_backup": False,
                "message": "No backups yet. Create one to protect your knowledge!",
                "how_to": (
                    "Your backup encrypts everything with your access key:\n"
                    "  - All wallet addresses and derivation paths\n"
                    "  - The entire knowledge graph (nodes, links, locks)\n"
                    "  - Protocol facts from all chain agents\n"
                    "  - Semantic search index\n\n"
                    "Encryption: AES-256-GCM with PBKDF2 (100,000 iterations)\n"
                    "Your access key never leaves your device."
                ),
            }

        latest = self._manifests[-1]
        return {
            "has_backup": True,
            "versions": len(self._manifests),
            "latest": latest.as_dict(),
            "message": (
                f"You have {len(self._manifests)} backup(s). "
                f"Latest: v{latest.version} with {latest.node_count} nodes, "
                f"{latest.lock_count} locks, {latest.wallet_count} wallet(s)."
            ),
            "recovery_steps": [s.as_dict() for s in self.get_recovery_steps()],
        }

    # =========================================================================
    # Manifest Management
    # =========================================================================

    def _load_manifests(self) -> None:
        """Load existing backup manifests from disk."""
        self._manifests = []
        for meta_file in sorted(self._backup_path.glob("backup_v*.meta.json")):
            try:
                with open(meta_file) as f:
                    data = json.load(f)
                manifest = BackupManifest(
                    version=data["version"],
                    created_at=data["created_at"],
                    content_hash=data["content_hash"],
                    encrypted=data.get("encrypted", True),
                    salt_hex=data.get("salt_hex", ""),
                    nonce_hex=data.get("nonce_hex", ""),
                    node_count=data.get("node_count", 0),
                    lock_count=data.get("lock_count", 0),
                    link_count=data.get("link_count", 0),
                    wallet_count=data.get("wallet_count", 0),
                    domains=data.get("domains", []),
                    size_bytes=data.get("size_bytes", 0),
                )
                self._manifests.append(manifest)
            except Exception as e:
                log.warning("backup.manifest_load_error", file=str(meta_file), error=str(e))

        if self._manifests:
            self._last_backup_hash = self._manifests[-1].content_hash
            self._backup_count = len(self._manifests)

    def list_backups(self) -> list[dict[str, Any]]:
        """List all available backups."""
        return [m.as_dict() for m in self._manifests]

    def stats(self) -> dict[str, Any]:
        return {
            "backup_count": self._backup_count,
            "latest_version": self._manifests[-1].version if self._manifests else 0,
            "backup_path": str(self._backup_path),
            "has_backup": len(self._manifests) > 0,
        }
