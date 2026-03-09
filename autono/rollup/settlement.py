"""Settlement manager for the Wali rollup.

Decides WHEN to settle batches to Cardano L1. Three triggers:
- Time: Every N seconds (default 600 = 10 minutes)
- Count: Every N transactions in the pool
- Force: Any user can force immediate settlement (pays full L1 fee)

The settlement manager does NOT submit to L1 directly — it builds
the batch and returns it. The chain connector (Blockfrost) handles
actual L1 submission.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import structlog

from autono.rollup.batch import Batch, BatchBuilder
from autono.rollup.tx_pool import TxPool

log = structlog.get_logger()


@dataclass
class SettlementConfig:
    """Settlement trigger configuration."""
    time_trigger_seconds: float = 600.0  # 10 minutes
    count_trigger: int = 100             # transactions
    max_batch_size: int = 1000           # txs per batch


class SettlementManager:
    """Manages settlement timing and history."""

    def __init__(
        self,
        builder: BatchBuilder,
        pool: TxPool,
        config: SettlementConfig | None = None,
    ) -> None:
        self._builder = builder
        self._pool = pool
        self._config = config or SettlementConfig()
        self._last_settlement_time = time.time()
        self._history: list[Batch] = []
        self._log = log.bind(component="settlement")

    @property
    def history(self) -> list[Batch]:
        return list(self._history)

    def should_settle(self) -> bool:
        """Check if settlement conditions are met."""
        if self._pool.size == 0:
            return False

        # Count trigger
        if self._pool.size >= self._config.count_trigger:
            return True

        # Time trigger
        elapsed = time.time() - self._last_settlement_time
        if elapsed >= self._config.time_trigger_seconds:
            return True

        return False

    def try_settle(self) -> Batch | None:
        """Settle if conditions are met. Returns batch or None."""
        if not self.should_settle():
            return None
        return self._do_settle()

    def force_settle(self) -> Batch | None:
        """Force immediate settlement regardless of triggers."""
        return self._do_settle()

    def _do_settle(self) -> Batch | None:
        """Execute settlement."""
        batch = self._builder.build(max_txs=self._config.max_batch_size)
        if batch is None:
            return None

        self._history.append(batch)
        self._last_settlement_time = time.time()

        self._log.info("settlement.completed",
                       batch=batch.batch_number,
                       txs=batch.tx_count,
                       withdrawals=len(batch.withdrawals))

        return batch

    def stats(self) -> dict[str, Any]:
        """Settlement statistics."""
        total_txs = sum(b.tx_count for b in self._history)
        return {
            "total_settlements": len(self._history),
            "total_txs_settled": total_txs,
            "pool_size": self._pool.size,
            "time_trigger_seconds": self._config.time_trigger_seconds,
            "count_trigger": self._config.count_trigger,
        }
