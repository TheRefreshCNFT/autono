"""Tests for rollup settlement manager."""

import time

from autono.rollup.batch import BatchBuilder
from autono.rollup.settlement import SettlementConfig, SettlementManager
from autono.rollup.state import RollupState
from autono.rollup.transaction import RollupTx
from autono.rollup.tx_pool import TxPool


class TestSettlementManager:
    def _setup(self, **config_overrides):
        state = RollupState()
        pool = TxPool()
        builder = BatchBuilder(state=state, pool=pool)
        config = SettlementConfig(**config_overrides)
        manager = SettlementManager(builder=builder, pool=pool, config=config)
        return state, pool, manager

    def test_no_settlement_when_empty(self):
        _, _, manager = self._setup()
        assert not manager.should_settle()

    def test_settle_on_count_trigger(self):
        state, pool, manager = self._setup(count_trigger=5)
        state.deposit("alice", "ADA", 1_000_000)
        for i in range(5):
            pool.add(RollupTx.transfer("alice", "bob", "ADA", 1, nonce=i))
        assert manager.should_settle()

    def test_no_settle_below_count(self):
        state, pool, manager = self._setup(count_trigger=5)
        state.deposit("alice", "ADA", 1_000_000)
        for i in range(4):
            pool.add(RollupTx.transfer("alice", "bob", "ADA", 1, nonce=i))
        assert not manager.should_settle()

    def test_settle_on_time_trigger(self):
        _, pool, manager = self._setup(time_trigger_seconds=0.1)
        pool.add(RollupTx.deposit("alice", "ADA", 1000, l1_tx_hash="a"))
        # Simulate time passing
        manager._last_settlement_time = time.time() - 1
        assert manager.should_settle()

    def test_no_settle_before_time_trigger(self):
        _, pool, manager = self._setup(time_trigger_seconds=9999)
        pool.add(RollupTx.deposit("alice", "ADA", 1000, l1_tx_hash="a"))
        # Time just started, shouldn't trigger
        assert not manager.should_settle()

    def test_force_settle(self):
        state, pool, manager = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        batch = manager.force_settle()
        assert batch is not None
        assert batch.tx_count == 1

    def test_force_settle_empty_returns_none(self):
        _, _, manager = self._setup()
        batch = manager.force_settle()
        assert batch is None

    def test_settle_returns_batch(self):
        state, pool, manager = self._setup(count_trigger=1)
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        batch = manager.try_settle()
        assert batch is not None

    def test_try_settle_when_not_triggered(self):
        state, pool, manager = self._setup(count_trigger=999)
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        batch = manager.try_settle()
        assert batch is None  # count not reached, time not elapsed

    def test_settle_resets_timer(self):
        state, pool, manager = self._setup(count_trigger=1)
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        manager.try_settle()
        assert not manager.should_settle()  # just settled, timer reset

    def test_settlement_history(self):
        state, pool, manager = self._setup(count_trigger=1)
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        manager.try_settle()
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=1))
        manager.try_settle()
        assert len(manager.history) == 2

    def test_stats(self):
        state, pool, manager = self._setup(count_trigger=1)
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        manager.try_settle()
        stats = manager.stats()
        assert stats["total_settlements"] == 1
        assert stats["total_txs_settled"] == 1
        assert "pool_size" in stats
        assert "time_trigger_seconds" in stats
        assert "count_trigger" in stats
