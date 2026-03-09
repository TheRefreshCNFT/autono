"""Rollup state manager.

Manages all account balances inside the Wali rollup. Uses a merkle tree
for state root computation and proof generation. The state root is what
gets posted to Cardano L1 during batch settlement.

Key differences from sidechain/state.py:
- Merkle-backed state root (not simple hash)
- Balance proofs for force exit
- Pending withdrawal tracking
- Nonce per account for replay protection
- Multi-asset support (ADA, AUTO, CNTs)
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import structlog

from autono.rollup.merkle import SparseMerkleTree

log = structlog.get_logger()


@dataclass
class TransferResult:
    """Result of a state mutation (transfer, withdrawal)."""
    success: bool
    error: str = ""
    tx_id: str = ""


@dataclass
class RollupAccount:
    """A single account in the rollup state."""
    address: str
    balances: dict[str, int] = field(default_factory=dict)
    nonce: int = 0


@dataclass
class PendingWithdrawal:
    """A withdrawal request waiting for the next batch settlement."""
    address: str
    asset: str
    amount: int
    l1_destination: str = ""
    created_at: float = field(default_factory=time.time)


class RollupState:
    """Manages the rollup world state with merkle proofs.

    All balances live here. The state root is posted to Cardano L1
    during each batch settlement. Any user can generate a balance proof
    and force-exit to L1 without node cooperation.
    """

    def __init__(self) -> None:
        self._accounts: dict[str, RollupAccount] = {}
        self._tree = SparseMerkleTree()
        self._pending_withdrawals: list[PendingWithdrawal] = []
        self._tx_counter = 0
        self._log = log.bind(component="rollup_state")

    @property
    def state_root(self) -> str:
        """Current merkle state root."""
        return self._tree.root

    @property
    def account_count(self) -> int:
        return len(self._accounts)

    @property
    def pending_withdrawals(self) -> list[PendingWithdrawal]:
        return list(self._pending_withdrawals)

    def _get_or_create(self, address: str) -> RollupAccount:
        if address not in self._accounts:
            self._accounts[address] = RollupAccount(address=address)
        return self._accounts[address]

    def _sync_to_tree(self, address: str) -> None:
        """Sync an account's state into the merkle tree."""
        account = self._accounts.get(address)
        if account:
            value = json.dumps({
                "balances": account.balances,
                "nonce": account.nonce,
            }, sort_keys=True)
            self._tree.put(address.encode(), value.encode())
        else:
            self._tree.delete(address.encode())

    def deposit(self, address: str, asset: str, amount: int) -> None:
        """Credit funds from L1 deposit into rollup account."""
        account = self._get_or_create(address)
        account.balances[asset] = account.balances.get(asset, 0) + amount
        self._sync_to_tree(address)
        self._log.info("rollup.deposit", address=address,
                       asset=asset, amount=amount)

    def get_balance(self, address: str, asset: str = "ADA") -> int:
        """Get balance for an address. Returns 0 if not found."""
        account = self._accounts.get(address)
        if not account:
            return 0
        return account.balances.get(asset, 0)

    def get_nonce(self, address: str) -> int:
        """Get nonce for an address. Returns 0 if not found."""
        account = self._accounts.get(address)
        return account.nonce if account else 0

    def transfer(self, sender: str, recipient: str,
                 asset: str, amount: int) -> TransferResult:
        """Transfer within the rollup. Instant, near-zero cost."""
        sender_account = self._accounts.get(sender)
        if not sender_account:
            return TransferResult(
                success=False, error="Sender account not found",
            )

        balance = sender_account.balances.get(asset, 0)
        if balance < amount:
            return TransferResult(
                success=False,
                error=f"Insufficient {asset} balance: have {balance}, need {amount}",
            )

        # Debit sender
        sender_account.balances[asset] = balance - amount
        sender_account.nonce += 1

        # Credit recipient
        recipient_account = self._get_or_create(recipient)
        recipient_account.balances[asset] = (
            recipient_account.balances.get(asset, 0) + amount
        )

        # Update merkle tree
        self._sync_to_tree(sender)
        self._sync_to_tree(recipient)

        self._tx_counter += 1
        tx_id = f"rtx_{self._tx_counter}"

        self._log.info("rollup.transfer", tx_id=tx_id,
                       sender=sender, recipient=recipient,
                       asset=asset, amount=amount)

        return TransferResult(success=True, tx_id=tx_id)

    def withdraw(self, address: str, asset: str, amount: int,
                 l1_destination: str = "") -> TransferResult:
        """Request withdrawal from rollup to Cardano L1.

        Deducts balance immediately. Withdrawal is included in next batch
        settlement. User gets funds on L1 after settlement confirms.
        """
        account = self._accounts.get(address)
        if not account:
            return TransferResult(success=False, error="Account not found")

        balance = account.balances.get(asset, 0)
        if balance < amount:
            return TransferResult(
                success=False,
                error=f"Insufficient {asset} balance: have {balance}, need {amount}",
            )

        account.balances[asset] = balance - amount
        account.nonce += 1
        self._sync_to_tree(address)

        self._pending_withdrawals.append(PendingWithdrawal(
            address=address,
            asset=asset,
            amount=amount,
            l1_destination=l1_destination or address,
        ))

        self._tx_counter += 1
        tx_id = f"rtx_{self._tx_counter}"

        self._log.info("rollup.withdraw_requested", tx_id=tx_id,
                       address=address, asset=asset, amount=amount)

        return TransferResult(success=True, tx_id=tx_id)

    def get_balance_proof(self, address: str) -> dict[str, Any] | None:
        """Generate a merkle proof of account balance.

        This proof can be submitted to the bridge contract on Cardano L1
        for force exit — no node cooperation required.
        """
        if address not in self._accounts:
            return None
        return self._tree.prove(address.encode())

    @staticmethod
    def verify_balance_proof(proof: dict[str, Any]) -> bool:
        """Verify a balance proof. Used by bridge contract on L1."""
        return SparseMerkleTree.verify(proof)

    def drain_pending_withdrawals(self) -> list[PendingWithdrawal]:
        """Return and clear pending withdrawals for batch settlement."""
        withdrawals = self._pending_withdrawals
        self._pending_withdrawals = []
        return withdrawals

    def snapshot(self) -> dict[str, Any]:
        """Current state summary."""
        return {
            "state_root": self.state_root,
            "account_count": self.account_count,
            "pending_withdrawals": len(self._pending_withdrawals),
            "total_transactions": self._tx_counter,
        }
