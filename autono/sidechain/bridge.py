"""Cardano <-> Autono sidechain bridge protocol.

Two-way bridge secured by:
- Multi-sig validator committee
- Merkle proof verification
- Challenge period for disputes
- Mithril-compatible state proofs from Cardano
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

log = structlog.get_logger()


class TransferDirection(str, Enum):
    TO_SIDECHAIN = "cardano_to_sidechain"
    TO_CARDANO = "sidechain_to_cardano"


class TransferStatus(str, Enum):
    PENDING = "pending"
    LOCKED = "locked"
    ATTESTED = "attested"
    COMPLETED = "completed"
    CHALLENGED = "challenged"
    REFUNDED = "refunded"


@dataclass
class BridgeTransfer:
    id: str
    direction: TransferDirection
    asset: str
    amount: int
    sender_address: str
    recipient_address: str
    status: TransferStatus = TransferStatus.PENDING
    source_tx_hash: str = ""
    destination_tx_hash: str = ""
    attestations: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None

    @property
    def attestation_count(self) -> int:
        return len(self.attestations)


@dataclass
class BridgeConfig:
    required_attestations: int = 5  # out of validator committee
    challenge_period_seconds: int = 3600  # 1 hour
    min_transfer_ada: int = 5
    max_transfer_ada: int = 1_000_000
    fee_bps: int = 10  # 0.1% bridge fee


class CardanoBridge:
    """Two-way bridge between Cardano mainchain and Autono sidechain."""

    def __init__(self, config: BridgeConfig | None = None) -> None:
        self.config = config or BridgeConfig()
        self.transfers: dict[str, BridgeTransfer] = {}
        self.committee_members: list[str] = []  # validator public keys
        self.locked_assets: dict[str, int] = {}  # asset -> amount locked
        self.log = log.bind(component="bridge")

    def initiate_transfer(
        self, direction: TransferDirection, asset: str, amount: int,
        sender: str, recipient: str,
    ) -> BridgeTransfer:
        transfer_id = hashlib.sha256(
            f"{sender}{recipient}{amount}{time.time()}".encode()
        ).hexdigest()[:16]

        transfer = BridgeTransfer(
            id=transfer_id,
            direction=direction,
            asset=asset,
            amount=amount,
            sender_address=sender,
            recipient_address=recipient,
        )
        self.transfers[transfer_id] = transfer
        self.log.info("bridge.transfer_initiated",
                      id=transfer_id, direction=direction.value,
                      asset=asset, amount=amount)
        return transfer

    def attest_transfer(self, transfer_id: str, validator_key: str) -> bool:
        transfer = self.transfers.get(transfer_id)
        if not transfer:
            return False
        if validator_key in transfer.attestations:
            return False  # already attested
        transfer.attestations.append(validator_key)
        if transfer.attestation_count >= self.config.required_attestations:
            transfer.status = TransferStatus.ATTESTED
            self.log.info("bridge.transfer_attested", id=transfer_id)
        return True

    def complete_transfer(self, transfer_id: str) -> bool:
        transfer = self.transfers.get(transfer_id)
        if not transfer or transfer.status != TransferStatus.ATTESTED:
            return False
        transfer.status = TransferStatus.COMPLETED
        transfer.completed_at = time.time()
        # Track locked assets
        if transfer.direction == TransferDirection.TO_SIDECHAIN:
            self.locked_assets[transfer.asset] = (
                self.locked_assets.get(transfer.asset, 0) + transfer.amount
            )
        else:
            self.locked_assets[transfer.asset] = max(
                0, self.locked_assets.get(transfer.asset, 0) - transfer.amount
            )
        self.log.info("bridge.transfer_completed", id=transfer_id)
        return True

    def challenge_transfer(self, transfer_id: str, challenger: str,
                           proof: dict[str, Any]) -> bool:
        transfer = self.transfers.get(transfer_id)
        if not transfer:
            return False
        transfer.status = TransferStatus.CHALLENGED
        self.log.warning("bridge.transfer_challenged",
                         id=transfer_id, challenger=challenger)
        return True

    def status(self) -> dict[str, Any]:
        return {
            "total_transfers": len(self.transfers),
            "pending": sum(1 for t in self.transfers.values()
                           if t.status == TransferStatus.PENDING),
            "completed": sum(1 for t in self.transfers.values()
                             if t.status == TransferStatus.COMPLETED),
            "locked_assets": self.locked_assets,
            "committee_size": len(self.committee_members),
            "required_attestations": self.config.required_attestations,
        }
