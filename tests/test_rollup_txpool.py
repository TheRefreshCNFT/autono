"""Tests for rollup transaction types and pool."""

import pytest

from autono.rollup.transaction import RollupTx, TxType
from autono.rollup.tx_pool import TxPool, TxValidationError


class TestRollupTx:
    def test_create_transfer(self):
        tx = RollupTx.transfer("alice", "bob", "ADA", 1000, nonce=0)
        assert tx.tx_type == TxType.TRANSFER
        assert tx.sender == "alice"
        assert tx.recipient == "bob"
        assert tx.tx_hash  # auto-computed

    def test_create_deposit(self):
        tx = RollupTx.deposit("alice", "ADA", 1_000_000, l1_tx_hash="abc123")
        assert tx.tx_type == TxType.DEPOSIT
        assert tx.amount == 1_000_000

    def test_create_withdrawal(self):
        tx = RollupTx.withdrawal("alice", "ADA", 500_000, nonce=1)
        assert tx.tx_type == TxType.WITHDRAWAL

    def test_tx_hash_deterministic(self):
        tx1 = RollupTx.transfer("alice", "bob", "ADA", 1000, nonce=0)
        tx2 = RollupTx.transfer("alice", "bob", "ADA", 1000, nonce=0)
        assert tx1.tx_hash == tx2.tx_hash

    def test_different_nonce_different_hash(self):
        tx1 = RollupTx.transfer("alice", "bob", "ADA", 1000, nonce=0)
        tx2 = RollupTx.transfer("alice", "bob", "ADA", 1000, nonce=1)
        assert tx1.tx_hash != tx2.tx_hash

    def test_deposit_sender_is_bridge(self):
        tx = RollupTx.deposit("alice", "ADA", 1000, l1_tx_hash="x")
        assert tx.sender == "L1_BRIDGE"

    def test_withdrawal_recipient_is_bridge(self):
        tx = RollupTx.withdrawal("alice", "ADA", 1000, nonce=0)
        assert tx.recipient == "L1_BRIDGE"


class TestTxPool:
    def test_add_valid_tx(self):
        pool = TxPool()
        tx = RollupTx.transfer("alice", "bob", "ADA", 1000, nonce=0)
        pool.add(tx)
        assert pool.size == 1

    def test_reject_duplicate(self):
        pool = TxPool()
        tx = RollupTx.transfer("alice", "bob", "ADA", 1000, nonce=0)
        pool.add(tx)
        with pytest.raises(TxValidationError, match="duplicate"):
            pool.add(tx)

    def test_reject_zero_amount(self):
        pool = TxPool()
        tx = RollupTx.transfer("alice", "bob", "ADA", 0, nonce=0)
        with pytest.raises(TxValidationError, match="amount"):
            pool.add(tx)

    def test_reject_negative_amount(self):
        pool = TxPool()
        tx = RollupTx.transfer("alice", "bob", "ADA", -100, nonce=0)
        with pytest.raises(TxValidationError, match="amount"):
            pool.add(tx)

    def test_reject_self_transfer(self):
        pool = TxPool()
        tx = RollupTx.transfer("alice", "alice", "ADA", 1000, nonce=0)
        with pytest.raises(TxValidationError, match="self"):
            pool.add(tx)

    def test_drain_returns_all_and_empties(self):
        pool = TxPool()
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 200, nonce=1))
        txs = pool.drain()
        assert len(txs) == 2
        assert pool.size == 0

    def test_drain_max_count(self):
        pool = TxPool()
        for i in range(10):
            pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=i))
        txs = pool.drain(max_count=5)
        assert len(txs) == 5
        assert pool.size == 5  # remaining

    def test_ordering_fifo(self):
        pool = TxPool()
        tx1 = RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0)
        tx2 = RollupTx.transfer("carol", "dave", "ADA", 200, nonce=0)
        pool.add(tx1)
        pool.add(tx2)
        txs = pool.drain()
        assert txs[0].tx_hash == tx1.tx_hash
        assert txs[1].tx_hash == tx2.tx_hash

    def test_stats(self):
        pool = TxPool()
        pool.add(RollupTx.transfer("alice", "bob", "ADA", 100, nonce=0))
        pool.add(RollupTx.deposit("carol", "ADA", 5000, l1_tx_hash="xyz"))
        stats = pool.stats()
        assert stats["size"] == 2
        assert stats["transfers"] == 1
        assert stats["deposits"] == 1

    def test_drain_empty_pool(self):
        pool = TxPool()
        txs = pool.drain()
        assert txs == []

    def test_deposit_not_rejected_as_self_transfer(self):
        """Deposits have sender=L1_BRIDGE, should never be self-transfer."""
        pool = TxPool()
        tx = RollupTx.deposit("alice", "ADA", 1000, l1_tx_hash="abc")
        pool.add(tx)  # should not raise
        assert pool.size == 1
