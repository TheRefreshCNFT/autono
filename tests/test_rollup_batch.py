"""Tests for rollup batch builder."""

from autono.rollup.batch import BatchBuilder, BatchStatus
from autono.rollup.state import RollupState
from autono.rollup.transaction import RollupTx
from autono.rollup.tx_pool import TxPool


class TestBatchBuilder:
    def _setup(self):
        state = RollupState()
        pool = TxPool()
        builder = BatchBuilder(state=state, pool=pool)
        return state, pool, builder

    def test_build_empty_batch(self):
        _, _, builder = self._setup()
        batch = builder.build()
        assert batch is None  # nothing to settle

    def test_build_batch_with_transfers(self):
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100_000, nonce=0))
        batch = builder.build()
        assert batch is not None
        assert batch.tx_count == 1
        assert batch.status == BatchStatus.READY

    def test_batch_applies_state_changes(self):
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 300_000, nonce=0))
        builder.build()
        assert state.get_balance("alice", "ADA") == 700_000
        assert state.get_balance("bob", "ADA") == 300_000

    def test_batch_records_state_roots(self):
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pre_root = state.state_root
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100_000, nonce=0))
        batch = builder.build()
        assert batch.pre_state_root == pre_root
        assert batch.post_state_root == state.state_root
        assert batch.pre_state_root != batch.post_state_root

    def test_batch_includes_deposits(self):
        state, pool, builder = self._setup()
        pool.add(RollupTx.deposit("alice", "ADA", 1_000_000, l1_tx_hash="abc"))
        batch = builder.build()
        assert batch is not None
        assert batch.tx_count == 1
        assert state.get_balance("alice", "ADA") == 1_000_000

    def test_batch_includes_withdrawals(self):
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.withdrawal("alice", "ADA", 500_000, nonce=0))
        batch = builder.build()
        assert batch is not None
        assert len(batch.withdrawals) == 1
        assert batch.withdrawals[0].amount == 500_000

    def test_failed_tx_skipped_in_batch(self):
        state, pool, builder = self._setup()
        # alice has no balance — transfer should fail
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 1000, nonce=0))
        batch = builder.build()
        # Batch is None because the only tx failed
        assert batch is None

    def test_mixed_success_and_failure(self):
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        pool.add(RollupTx.transfer("nobody", "bob", "ADA", 999, nonce=0))  # fails
        batch = builder.build()
        assert batch is not None
        assert batch.tx_count == 1  # only successful tx
        assert len(batch.failed_txs) == 1

    def test_batch_number_increments(self):
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        b1 = builder.build()
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=1))
        b2 = builder.build()
        assert b2.batch_number == b1.batch_number + 1

    def test_batch_max_size(self):
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 10_000_000)
        for i in range(200):
            pool.add(RollupTx.transfer("alice", "bob", "ADA", 1, nonce=i))
        batch = builder.build(max_txs=100)
        assert batch.tx_count == 100
        assert pool.size == 100  # remaining

    def test_settlement_payload(self):
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        batch = builder.build()
        payload = batch.settlement_payload()
        assert "batch_number" in payload
        assert "pre_state_root" in payload
        assert "post_state_root" in payload
        assert "tx_count" in payload
        assert "withdrawals" in payload

    def test_withdrawal_drained_after_batch(self):
        """Pending withdrawals are drained into the batch, not left in state."""
        state, pool, builder = self._setup()
        state.deposit("alice", "ADA", 1_000_000)
        pool.add(RollupTx.withdrawal("alice", "ADA", 100_000, nonce=0))
        batch = builder.build()
        assert len(batch.withdrawals) == 1
        assert len(state.pending_withdrawals) == 0
