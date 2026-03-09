"""Rollup transaction types.

Three transaction types flow through the rollup:
- TRANSFER: Wali -> Wali (instant, near-zero cost)
- DEPOSIT: L1 detection -> rollup credit
- WITHDRAWAL: Rollup debit -> included in next L1 settlement
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum


class TxType(str, Enum):
    TRANSFER = "transfer"
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"


@dataclass
class RollupTx:
    """A single rollup transaction."""
    tx_type: TxType
    sender: str
    recipient: str
    asset: str
    amount: int
    nonce: int = 0
    timestamp: float = field(default_factory=time.time)
    l1_tx_hash: str = ""  # for deposits — the L1 tx that locked funds
    tx_hash: str = ""

    def __post_init__(self) -> None:
        if not self.tx_hash:
            self.tx_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        content = (
            f"{self.tx_type.value}{self.sender}{self.recipient}"
            f"{self.asset}{self.amount}{self.nonce}"
        )
        return hashlib.sha256(content.encode()).hexdigest()

    @classmethod
    def transfer(cls, sender: str, recipient: str,
                 asset: str, amount: int, nonce: int = 0) -> RollupTx:
        """Create a Wali-to-Wali transfer."""
        return cls(
            tx_type=TxType.TRANSFER,
            sender=sender,
            recipient=recipient,
            asset=asset,
            amount=amount,
            nonce=nonce,
        )

    @classmethod
    def deposit(cls, recipient: str, asset: str, amount: int,
                l1_tx_hash: str = "") -> RollupTx:
        """Create a deposit (L1 -> rollup)."""
        return cls(
            tx_type=TxType.DEPOSIT,
            sender="L1_BRIDGE",
            recipient=recipient,
            asset=asset,
            amount=amount,
            l1_tx_hash=l1_tx_hash,
        )

    @classmethod
    def withdrawal(cls, sender: str, asset: str, amount: int,
                   nonce: int = 0) -> RollupTx:
        """Create a withdrawal request (rollup -> L1)."""
        return cls(
            tx_type=TxType.WITHDRAWAL,
            sender=sender,
            recipient="L1_BRIDGE",
            asset=asset,
            amount=amount,
            nonce=nonce,
        )
