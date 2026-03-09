"""Unified rollup engine for Wali.

Composes all rollup components into a single entry point:
- RollupState: account balances + merkle proofs
- TxPool: transaction validation + ordering
- BatchBuilder: state application + batch packaging
- SettlementManager: settlement timing + history

Downstream code (orchestrator, API) talks ONLY to the engine.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import structlog

from autono.rollup.batch import Batch, BatchBuilder
from autono.rollup.settlement import SettlementConfig, SettlementManager
from autono.rollup.state import RollupState
from autono.rollup.transaction import RollupTx
from autono.rollup.tx_pool import TxPool

log = structlog.get_logger()


@dataclass
class EngineConfig:
    """Rollup engine configuration."""
    time_trigger_seconds: float = 600.0
    count_trigger: int = 100
    max_batch_size: int = 1000


class RollupEngine:
    """Wali rollup engine — single entry point for all rollup operations.

    Usage:
        engine = RollupEngine()
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="abc")
        engine.settle()  # force settlement
        engine.submit_transfer("alice", "bob", "ADA", 500_000, nonce=0)
        batch = engine.tick()  # settle only if triggers met
    """

    def __init__(self, config: EngineConfig | None = None) -> None:
        cfg = config or EngineConfig()
        self._state = RollupState()
        self._pool = TxPool()
        self._builder = BatchBuilder(state=self._state, pool=self._pool)
        self._settlement = SettlementManager(
            builder=self._builder,
            pool=self._pool,
            config=SettlementConfig(
                time_trigger_seconds=cfg.time_trigger_seconds,
                count_trigger=cfg.count_trigger,
                max_batch_size=cfg.max_batch_size,
            ),
        )
        self._log = log.bind(component="rollup_engine")

    # ── Public API: submit transactions ──

    def deposit(self, address: str, asset: str, amount: int,
                *, l1_tx_hash: str) -> None:
        """Record a deposit from Cardano L1."""
        tx = RollupTx.deposit(address, asset, amount, l1_tx_hash=l1_tx_hash)
        self._pool.add(tx)
        self._log.debug("engine.deposit", address=address,
                        asset=asset, amount=amount)

    def submit_transfer(self, sender: str, recipient: str,
                        asset: str, amount: int, *, nonce: int) -> None:
        """Submit a transfer between rollup accounts."""
        tx = RollupTx.transfer(sender, recipient, asset, amount, nonce=nonce)
        self._pool.add(tx)
        self._log.debug("engine.transfer", sender=sender,
                        recipient=recipient, asset=asset, amount=amount)

    def submit_withdrawal(self, address: str, asset: str, amount: int,
                          *, nonce: int) -> None:
        """Submit a withdrawal request (rollup -> L1)."""
        tx = RollupTx.withdrawal(address, asset, amount, nonce=nonce)
        self._pool.add(tx)
        self._log.debug("engine.withdrawal", address=address,
                        asset=asset, amount=amount)

    # ── Settlement ──

    def tick(self) -> Batch | None:
        """Check settlement triggers and settle if conditions met.

        Call this periodically (e.g., every second) from the main loop.
        Returns batch if settled, None otherwise.
        """
        return self._settlement.try_settle()

    def settle(self) -> Batch | None:
        """Force immediate settlement regardless of triggers.

        Returns the batch, or None if pool is empty.
        """
        return self._settlement.force_settle()

    # ── Queries ──

    def get_balance(self, address: str, asset: str) -> int:
        """Get current balance for an address."""
        return self._state.get_balance(address, asset)

    def get_balance_proof(self, address: str) -> dict[str, Any] | None:
        """Get a merkle proof for an account (for force exit)."""
        return self._state.get_balance_proof(address)

    def verify_balance_proof(self, proof: dict[str, Any]) -> bool:
        """Verify a balance proof against current state root."""
        return self._state.verify_balance_proof(proof)

    @property
    def state_root(self) -> str:
        """Current merkle state root."""
        return self._state.state_root

    @property
    def pool_size(self) -> int:
        """Number of pending transactions."""
        return self._pool.size

    @property
    def settlement_history(self) -> list[Batch]:
        """All settled batches."""
        return self._settlement.history

    def stats(self) -> dict[str, Any]:
        """Comprehensive engine statistics."""
        return {
            "state_root": self._state.state_root,
            "pool": self._pool.stats(),
            "settlement": self._settlement.stats(),
        }
