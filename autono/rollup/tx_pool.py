"""Transaction pool for the Wali rollup.

Validates incoming transactions, deduplicates, and orders them FIFO
for inclusion in the next batch.
"""

from __future__ import annotations

from collections import deque
from typing import Any

import structlog

from autono.rollup.transaction import RollupTx, TxType

log = structlog.get_logger()


class TxValidationError(Exception):
    """Raised when a transaction fails pool validation."""


class TxPool:
    """Collects and validates rollup transactions before batching."""

    def __init__(self) -> None:
        self._queue: deque[RollupTx] = deque()
        self._seen: set[str] = set()  # tx hashes for dedup
        self._log = log.bind(component="tx_pool")

    @property
    def size(self) -> int:
        return len(self._queue)

    def add(self, tx: RollupTx) -> None:
        """Add a validated transaction to the pool."""
        self._validate(tx)
        self._queue.append(tx)
        self._seen.add(tx.tx_hash)
        self._log.debug("tx_pool.added", tx_hash=tx.tx_hash[:12],
                        tx_type=tx.tx_type.value)

    def drain(self, max_count: int | None = None) -> list[RollupTx]:
        """Remove and return transactions from the pool.

        Args:
            max_count: Maximum number to return. None = all.

        Returns:
            List of transactions in FIFO order.
        """
        if max_count is None:
            max_count = len(self._queue)

        result: list[RollupTx] = []
        for _ in range(min(max_count, len(self._queue))):
            tx = self._queue.popleft()
            self._seen.discard(tx.tx_hash)
            result.append(tx)

        return result

    def stats(self) -> dict[str, Any]:
        """Pool statistics by transaction type."""
        type_counts: dict[str, int] = {}
        for tx in self._queue:
            key = tx.tx_type.value + "s"
            type_counts[key] = type_counts.get(key, 0) + 1
        return {"size": self.size, **type_counts}

    def _validate(self, tx: RollupTx) -> None:
        """Validate a transaction before pool admission."""
        if tx.tx_hash in self._seen:
            raise TxValidationError(f"duplicate transaction: {tx.tx_hash[:12]}")

        if tx.amount <= 0:
            raise TxValidationError(f"invalid amount: {tx.amount}")

        if tx.tx_type == TxType.TRANSFER and tx.sender == tx.recipient:
            raise TxValidationError("self-transfer not allowed")
