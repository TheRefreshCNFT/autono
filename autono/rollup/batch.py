"""Batch builder for Wali rollup.

Collects transactions from the pool, applies them to rollup state,
and packages the result into a settlement batch. Each batch contains:
- Pre/post state roots
- List of applied transactions
- Withdrawal requests (for L1 unlock)
- Batch number for ordering

One batch = one Cardano L1 transaction during settlement.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

from autono.rollup.state import PendingWithdrawal, RollupState
from autono.rollup.transaction import RollupTx, TxType
from autono.rollup.tx_pool import TxPool

log = structlog.get_logger()


class BatchStatus(str, Enum):
    READY = "ready"          # built, awaiting settlement
    SETTLING = "settling"    # submitted to L1
    SETTLED = "settled"      # confirmed on L1
    FAILED = "failed"


@dataclass
class Batch:
    """A settlement batch ready to be posted to Cardano L1."""
    batch_number: int
    pre_state_root: str
    post_state_root: str
    transactions: list[RollupTx] = field(default_factory=list)
    failed_txs: list[tuple[RollupTx, str]] = field(default_factory=list)
    withdrawals: list[PendingWithdrawal] = field(default_factory=list)
    status: BatchStatus = BatchStatus.READY
    created_at: float = field(default_factory=time.time)
    settled_at: float | None = None
    l1_tx_hash: str = ""

    @property
    def tx_count(self) -> int:
        return len(self.transactions)

    def settlement_payload(self) -> dict[str, Any]:
        """Data to include in the Cardano L1 settlement transaction."""
        return {
            "batch_number": self.batch_number,
            "pre_state_root": self.pre_state_root,
            "post_state_root": self.post_state_root,
            "tx_count": self.tx_count,
            "withdrawals": [
                {"address": w.address, "asset": w.asset, "amount": w.amount}
                for w in self.withdrawals
            ],
        }


class BatchBuilder:
    """Builds settlement batches from the transaction pool.

    Flow:
    1. Drain transactions from pool
    2. Apply each to rollup state
    3. Skip failed transactions (log them)
    4. Record pre/post state roots
    5. Package as a Batch ready for L1 settlement
    """

    def __init__(self, state: RollupState, pool: TxPool) -> None:
        self._state = state
        self._pool = pool
        self._batch_counter = 0
        self._log = log.bind(component="batch_builder")

    def build(self, max_txs: int = 1000) -> Batch | None:
        """Build a batch from pending transactions.

        Returns None if no valid transactions to include.
        """
        txs = self._pool.drain(max_count=max_txs)
        if not txs:
            return None

        pre_root = self._state.state_root
        applied: list[RollupTx] = []
        failed: list[tuple[RollupTx, str]] = []

        for tx in txs:
            success, error = self._apply_tx(tx)
            if success:
                applied.append(tx)
            else:
                failed.append((tx, error))

        if not applied:
            return None

        post_root = self._state.state_root
        withdrawals = self._state.drain_pending_withdrawals()

        self._batch_counter += 1
        batch = Batch(
            batch_number=self._batch_counter,
            pre_state_root=pre_root,
            post_state_root=post_root,
            transactions=applied,
            failed_txs=failed,
            withdrawals=withdrawals,
        )

        self._log.info("batch.built",
                       batch=self._batch_counter,
                       applied=len(applied),
                       failed=len(failed),
                       withdrawals=len(withdrawals))

        return batch

    def _apply_tx(self, tx: RollupTx) -> tuple[bool, str]:
        """Apply a single transaction to rollup state.

        Returns (success, error_message).
        """
        if tx.tx_type == TxType.DEPOSIT:
            self._state.deposit(tx.recipient, tx.asset, tx.amount)
            return True, ""

        elif tx.tx_type == TxType.TRANSFER:
            result = self._state.transfer(
                tx.sender, tx.recipient, tx.asset, tx.amount,
            )
            return result.success, result.error

        elif tx.tx_type == TxType.WITHDRAWAL:
            result = self._state.withdraw(tx.sender, tx.asset, tx.amount)
            return result.success, result.error

        return False, f"Unknown tx type: {tx.tx_type}"
