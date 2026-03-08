"""Sidechain state management.

Hybrid UTXO + account model:
- UTXO for asset transfers (Cardano compatible)
- Account state for smart contracts and DeFi (performance)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Account:
    address: str
    balances: dict[str, int] = field(default_factory=lambda: {"AUTO": 0})
    nonce: int = 0
    contract_data: dict[str, Any] = field(default_factory=dict)
    is_contract: bool = False


@dataclass
class UTXO:
    tx_hash: str
    index: int
    address: str
    asset: str
    amount: int
    spent: bool = False


class StateManager:
    """Manages the sidechain's world state."""

    def __init__(self) -> None:
        self.accounts: dict[str, Account] = {}
        self.utxos: dict[str, UTXO] = {}

    def get_or_create_account(self, address: str) -> Account:
        if address not in self.accounts:
            self.accounts[address] = Account(address=address)
        return self.accounts[address]

    def credit(self, address: str, asset: str, amount: int) -> None:
        account = self.get_or_create_account(address)
        account.balances[asset] = account.balances.get(asset, 0) + amount

    def debit(self, address: str, asset: str, amount: int) -> bool:
        account = self.get_or_create_account(address)
        balance = account.balances.get(asset, 0)
        if balance < amount:
            return False
        account.balances[asset] = balance - amount
        return True

    def transfer(self, sender: str, recipient: str,
                 asset: str, amount: int) -> bool:
        if not self.debit(sender, asset, amount):
            return False
        self.credit(recipient, asset, amount)
        return True

    def get_balance(self, address: str, asset: str = "AUTO") -> int:
        account = self.accounts.get(address)
        if not account:
            return 0
        return account.balances.get(asset, 0)

    def add_utxo(self, utxo: UTXO) -> None:
        key = f"{utxo.tx_hash}:{utxo.index}"
        self.utxos[key] = utxo

    def spend_utxo(self, tx_hash: str, index: int) -> UTXO | None:
        key = f"{tx_hash}:{index}"
        utxo = self.utxos.get(key)
        if utxo and not utxo.spent:
            utxo.spent = True
            return utxo
        return None

    def state_root(self) -> str:
        """Compute a simple state root hash."""
        import hashlib
        content = ""
        for addr in sorted(self.accounts.keys()):
            acc = self.accounts[addr]
            content += f"{addr}:{acc.balances}:{acc.nonce}"
        return hashlib.sha256(content.encode()).hexdigest()

    def stats(self) -> dict[str, Any]:
        return {
            "total_accounts": len(self.accounts),
            "total_utxos": len(self.utxos),
            "unspent_utxos": sum(1 for u in self.utxos.values() if not u.spent),
        }
