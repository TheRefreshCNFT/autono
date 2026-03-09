"""Tests for the unified rollup engine."""

import time

from autono.rollup.batch import BatchStatus
from autono.rollup.engine import RollupEngine, EngineConfig
from autono.rollup.transaction import RollupTx, TxType


class TestRollupEngine:
    """Test the engine as a unified entry point."""

    def _engine(self, **overrides) -> RollupEngine:
        config = EngineConfig(**overrides)
        return RollupEngine(config=config)

    # ── Deposits ──

    def test_deposit(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="abc123")
        engine.settle()  # deposit goes pool -> batch -> state
        assert engine.get_balance("alice", "ADA") == 1_000_000

    def test_deposit_adds_to_pool(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 500, l1_tx_hash="tx1")
        assert engine.pool_size == 1

    # ── Transfers ──

    def test_transfer(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="tx1")
        engine.settle()  # settle deposit into state
        engine.submit_transfer("alice", "bob", "ADA", 300_000, nonce=0)
        assert engine.pool_size == 1

    def test_transfer_included_in_settlement(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="tx1")
        engine.settle()  # apply deposit
        engine.submit_transfer("alice", "bob", "ADA", 300_000, nonce=0)
        batch = engine.settle()
        assert batch is not None
        assert batch.tx_count == 1
        assert engine.get_balance("alice", "ADA") == 700_000
        assert engine.get_balance("bob", "ADA") == 300_000

    # ── Withdrawals ──

    def test_withdrawal(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="tx1")
        engine.settle()
        engine.submit_withdrawal("alice", "ADA", 500_000, nonce=0)
        batch = engine.settle()
        assert batch is not None
        assert len(batch.withdrawals) == 1
        assert batch.withdrawals[0].amount == 500_000
        assert engine.get_balance("alice", "ADA") == 500_000

    # ── Settlement triggers ──

    def test_tick_no_settle_below_threshold(self):
        engine = self._engine(count_trigger=10, time_trigger_seconds=9999)
        engine.deposit("alice", "ADA", 1000, l1_tx_hash="tx1")
        batch = engine.tick()
        assert batch is None  # only 1 tx, count trigger is 10

    def test_tick_settles_on_count_trigger(self):
        engine = self._engine(count_trigger=3)
        for i in range(3):
            engine.deposit(f"user{i}", "ADA", 1000, l1_tx_hash=f"tx{i}")
        batch = engine.tick()
        assert batch is not None
        assert batch.tx_count == 3

    def test_tick_settles_on_time_trigger(self):
        engine = self._engine(time_trigger_seconds=0.1)
        engine.deposit("alice", "ADA", 1000, l1_tx_hash="tx1")
        # Simulate time passing
        engine._settlement._last_settlement_time = time.time() - 1
        batch = engine.tick()
        assert batch is not None

    def test_force_settle(self):
        engine = self._engine(count_trigger=999, time_trigger_seconds=9999)
        engine.deposit("alice", "ADA", 1000, l1_tx_hash="tx1")
        batch = engine.settle()  # force regardless of triggers
        assert batch is not None

    def test_settle_empty_returns_none(self):
        engine = self._engine()
        batch = engine.settle()
        assert batch is None

    # ── Balance proofs ──

    def test_balance_proof(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="tx1")
        engine.settle()
        proof = engine.get_balance_proof("alice")
        assert proof is not None
        assert "root" in proof
        assert "key" in proof
        assert "value" in proof

    def test_verify_balance_proof(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="tx1")
        engine.settle()
        proof = engine.get_balance_proof("alice")
        assert engine.verify_balance_proof(proof)

    # ── State root ──

    def test_state_root_changes_after_settlement(self):
        engine = self._engine()
        root_before = engine.state_root
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="tx1")
        engine.settle()
        root_after = engine.state_root
        assert root_before != root_after

    # ── History + stats ──

    def test_settlement_history(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1000, l1_tx_hash="tx1")
        engine.settle()
        engine.deposit("bob", "ADA", 2000, l1_tx_hash="tx2")
        engine.settle()
        assert len(engine.settlement_history) == 2

    def test_stats(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1000, l1_tx_hash="tx1")
        engine.settle()
        stats = engine.stats()
        assert "state_root" in stats
        assert "pool" in stats
        assert "settlement" in stats
        assert stats["settlement"]["total_settlements"] == 1

    # ── Multi-asset ──

    def test_multi_asset_deposits(self):
        engine = self._engine()
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="tx1")
        engine.deposit("alice", "AUTO", 500, l1_tx_hash="tx2")
        engine.settle()
        assert engine.get_balance("alice", "ADA") == 1_000_000
        assert engine.get_balance("alice", "AUTO") == 500

    # ── End-to-end ──

    def test_full_lifecycle(self):
        """Deposit -> transfer -> withdraw -> settle -> verify."""
        engine = self._engine()

        # 1. Deposit
        engine.deposit("alice", "ADA", 1_000_000, l1_tx_hash="deposit1")
        b1 = engine.settle()
        assert b1 is not None
        assert engine.get_balance("alice", "ADA") == 1_000_000

        # 2. Transfer
        engine.submit_transfer("alice", "bob", "ADA", 400_000, nonce=0)
        b2 = engine.settle()
        assert b2 is not None
        assert engine.get_balance("alice", "ADA") == 600_000
        assert engine.get_balance("bob", "ADA") == 400_000

        # 3. Withdraw
        engine.submit_withdrawal("bob", "ADA", 200_000, nonce=0)
        b3 = engine.settle()
        assert b3 is not None
        assert len(b3.withdrawals) == 1
        assert engine.get_balance("bob", "ADA") == 200_000

        # 4. Verify final state
        proof = engine.get_balance_proof("bob")
        assert proof is not None
        assert engine.verify_balance_proof(proof)

        # 5. History
        assert len(engine.settlement_history) == 3
