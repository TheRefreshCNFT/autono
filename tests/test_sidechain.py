"""Tests for sidechain protocol components."""

from __future__ import annotations

from autono.sidechain.block import BlockChain, Transaction
from autono.sidechain.bridge import (
    BridgeConfig,
    CardanoBridge,
    TransferDirection,
    TransferStatus,
)
from autono.sidechain.consensus import ConsensusParams, OuroborosTurbo
from autono.sidechain.state import StateManager


class TestConsensus:
    def test_register_validator(self):
        consensus = OuroborosTurbo()
        v = consensus.register_validator("v1", 50_000, "pk1")
        assert v.active
        assert v.stake == 50_000

    def test_reject_low_stake(self):
        consensus = OuroborosTurbo()
        try:
            consensus.register_validator("v1", 100, "pk1")
            assert False, "Should have raised"
        except ValueError:
            pass

    def test_select_leader(self):
        consensus = OuroborosTurbo()
        consensus.register_validator("v1", 50_000, "pk1")
        consensus.register_validator("v2", 50_000, "pk2")
        leader = consensus.select_leader(1)
        assert leader in ("v1", "v2")

    def test_advance_slot(self):
        consensus = OuroborosTurbo()
        consensus.register_validator("v1", 50_000, "pk1")
        slot = consensus.advance_slot()
        assert slot.number == 1
        assert slot.leader == "v1"

    def test_slash_validator(self):
        consensus = OuroborosTurbo()
        consensus.register_validator("v1", 50_000, "pk1")
        consensus.slash_validator("v1", "double_signing")
        assert consensus.validators["v1"].stake == 47_500  # 5% slash

    def test_status(self):
        consensus = OuroborosTurbo()
        s = consensus.status()
        assert "slot" in s
        assert "epoch" in s


class TestBlockChain:
    def test_genesis(self):
        chain = BlockChain()
        assert chain.height == 0
        assert chain.tip.producer == "genesis"

    def test_produce_block(self):
        chain = BlockChain()
        tx = Transaction(tx_hash="", sender="alice", recipient="bob", amount=100)
        chain.add_transaction(tx)
        block = chain.produce_block(1, 0, "validator1")
        assert block.tx_count == 1
        assert chain.height == 1

    def test_stats(self):
        chain = BlockChain()
        s = chain.stats()
        assert s["height"] == 0
        assert s["total_transactions"] == 0


class TestBridge:
    def test_initiate_transfer(self):
        bridge = CardanoBridge()
        transfer = bridge.initiate_transfer(
            TransferDirection.TO_SIDECHAIN, "ADA", 1000,
            "addr_cardano", "addr_sidechain",
        )
        assert transfer.status == TransferStatus.PENDING

    def test_attest_and_complete(self):
        bridge = CardanoBridge(BridgeConfig(required_attestations=2))
        transfer = bridge.initiate_transfer(
            TransferDirection.TO_SIDECHAIN, "ADA", 1000,
            "addr_cardano", "addr_sidechain",
        )
        bridge.attest_transfer(transfer.id, "validator1")
        bridge.attest_transfer(transfer.id, "validator2")
        assert transfer.status == TransferStatus.ATTESTED
        bridge.complete_transfer(transfer.id)
        assert transfer.status == TransferStatus.COMPLETED

    def test_duplicate_attestation(self):
        bridge = CardanoBridge(BridgeConfig(required_attestations=2))
        transfer = bridge.initiate_transfer(
            TransferDirection.TO_SIDECHAIN, "ADA", 1000,
            "addr_cardano", "addr_sidechain",
        )
        assert bridge.attest_transfer(transfer.id, "validator1")
        assert not bridge.attest_transfer(transfer.id, "validator1")  # duplicate


class TestState:
    def test_credit_debit(self):
        state = StateManager()
        state.credit("alice", "AUTO", 1000)
        assert state.get_balance("alice", "AUTO") == 1000
        assert state.debit("alice", "AUTO", 500)
        assert state.get_balance("alice", "AUTO") == 500

    def test_insufficient_balance(self):
        state = StateManager()
        state.credit("alice", "AUTO", 100)
        assert not state.debit("alice", "AUTO", 200)

    def test_transfer(self):
        state = StateManager()
        state.credit("alice", "AUTO", 1000)
        assert state.transfer("alice", "bob", "AUTO", 300)
        assert state.get_balance("alice", "AUTO") == 700
        assert state.get_balance("bob", "AUTO") == 300
