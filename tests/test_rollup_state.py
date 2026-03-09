"""Tests for rollup state manager."""

from autono.rollup.state import RollupState


class TestRollupState:
    def test_empty_state_has_root(self):
        state = RollupState()
        assert state.state_root is not None
        assert len(state.state_root) == 64

    def test_deposit_creates_account(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        assert state.get_balance("alice", "ADA") == 1_000_000

    def test_deposit_increments_balance(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        state.deposit("alice", "ADA", 500_000)
        assert state.get_balance("alice", "ADA") == 1_500_000

    def test_transfer_moves_funds(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        result = state.transfer("alice", "bob", "ADA", 300_000)
        assert result.success
        assert state.get_balance("alice", "ADA") == 700_000
        assert state.get_balance("bob", "ADA") == 300_000

    def test_transfer_insufficient_funds(self):
        state = RollupState()
        state.deposit("alice", "ADA", 100)
        result = state.transfer("alice", "bob", "ADA", 200)
        assert not result.success
        assert "insufficient" in result.error.lower()

    def test_transfer_increments_nonce(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        state.transfer("alice", "bob", "ADA", 100)
        assert state.get_nonce("alice") == 1
        state.transfer("alice", "bob", "ADA", 100)
        assert state.get_nonce("alice") == 2

    def test_failed_transfer_does_not_increment_nonce(self):
        state = RollupState()
        state.deposit("alice", "ADA", 100)
        state.transfer("alice", "bob", "ADA", 200)  # fails
        assert state.get_nonce("alice") == 0

    def test_withdraw_marks_pending(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        result = state.withdraw("alice", "ADA", 500_000)
        assert result.success
        assert state.get_balance("alice", "ADA") == 500_000
        assert len(state.pending_withdrawals) == 1

    def test_withdraw_insufficient_funds(self):
        state = RollupState()
        state.deposit("alice", "ADA", 100)
        result = state.withdraw("alice", "ADA", 200)
        assert not result.success

    def test_state_root_changes_on_mutation(self):
        state = RollupState()
        root1 = state.state_root
        state.deposit("alice", "ADA", 1_000_000)
        root2 = state.state_root
        assert root1 != root2
        state.transfer("alice", "bob", "ADA", 100)
        root3 = state.state_root
        assert root2 != root3

    def test_deterministic_state_root(self):
        """Same operations produce same root."""
        s1 = RollupState()
        s2 = RollupState()
        s1.deposit("alice", "ADA", 1000)
        s1.deposit("bob", "ADA", 500)
        s2.deposit("alice", "ADA", 1000)
        s2.deposit("bob", "ADA", 500)
        assert s1.state_root == s2.state_root

    def test_multi_asset_balances(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        state.deposit("alice", "AUTO", 500)
        assert state.get_balance("alice", "ADA") == 1_000_000
        assert state.get_balance("alice", "AUTO") == 500

    def test_balance_proof_generation(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        proof = state.get_balance_proof("alice")
        assert proof is not None
        assert proof["root"] == state.state_root

    def test_balance_proof_verification(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        proof = state.get_balance_proof("alice")
        assert RollupState.verify_balance_proof(proof)

    def test_balance_proof_invalid_after_mutation(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        proof = state.get_balance_proof("alice")
        state.deposit("alice", "ADA", 500)  # mutate state
        # Proof was for old root, should not match new root
        assert proof["root"] != state.state_root

    def test_account_count(self):
        state = RollupState()
        assert state.account_count == 0
        state.deposit("alice", "ADA", 100)
        state.deposit("bob", "ADA", 100)
        assert state.account_count == 2

    def test_snapshot(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        snap = state.snapshot()
        assert snap["state_root"] == state.state_root
        assert snap["account_count"] == 1
        assert snap["pending_withdrawals"] == 0

    def test_drain_pending_withdrawals(self):
        state = RollupState()
        state.deposit("alice", "ADA", 1_000_000)
        state.withdraw("alice", "ADA", 100_000)
        state.withdraw("alice", "ADA", 200_000)
        assert len(state.pending_withdrawals) == 2
        drained = state.drain_pending_withdrawals()
        assert len(drained) == 2
        assert len(state.pending_withdrawals) == 0

    def test_get_balance_nonexistent_account(self):
        state = RollupState()
        assert state.get_balance("nobody", "ADA") == 0

    def test_get_nonce_nonexistent_account(self):
        state = RollupState()
        assert state.get_nonce("nobody") == 0

    def test_transfer_from_nonexistent_account(self):
        state = RollupState()
        result = state.transfer("nobody", "bob", "ADA", 100)
        assert not result.success
