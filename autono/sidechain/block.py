"""Block structure for the Autono sidechain.

Blocks are lightweight and optimized for high throughput.
Compatible with Cardano's UTXO model but extended with
account-based state for smart contract efficiency.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Transaction:
    tx_hash: str
    sender: str
    recipient: str
    amount: int
    asset: str = "AUTO"
    fee: int = 0
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    status: str = "pending"

    def compute_hash(self) -> str:
        content = f"{self.sender}{self.recipient}{self.amount}{self.asset}{self.timestamp}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class Block:
    slot: int
    epoch: int
    producer: str  # validator id
    parent_hash: str
    transactions: list[Transaction] = field(default_factory=list)
    state_root: str = ""
    timestamp: float = field(default_factory=time.time)
    block_hash: str = ""

    def __post_init__(self) -> None:
        if not self.block_hash:
            self.block_hash = self.compute_hash()

    def compute_hash(self) -> str:
        tx_hashes = "".join(tx.tx_hash for tx in self.transactions)
        content = (
            f"{self.slot}{self.epoch}{self.producer}"
            f"{self.parent_hash}{tx_hashes}{self.timestamp}"
        )
        return hashlib.sha256(content.encode()).hexdigest()

    @property
    def tx_count(self) -> int:
        return len(self.transactions)

    @property
    def total_fees(self) -> int:
        return sum(tx.fee for tx in self.transactions)


class BlockChain:
    """In-memory blockchain for the sidechain.

    Production would use persistent storage — this is the protocol logic.
    """

    def __init__(self) -> None:
        self.blocks: list[Block] = []
        self.pending_txs: list[Transaction] = []
        self.tx_index: dict[str, Transaction] = {}
        self._genesis()

    def _genesis(self) -> None:
        genesis = Block(
            slot=0, epoch=0, producer="genesis",
            parent_hash="0" * 64,
            state_root="genesis_state",
        )
        self.blocks.append(genesis)

    @property
    def height(self) -> int:
        return len(self.blocks) - 1  # exclude genesis

    @property
    def tip(self) -> Block:
        return self.blocks[-1]

    def add_transaction(self, tx: Transaction) -> None:
        tx.tx_hash = tx.compute_hash()
        self.pending_txs.append(tx)
        self.tx_index[tx.tx_hash] = tx

    def produce_block(self, slot: int, epoch: int, producer: str) -> Block:
        """Create a new block from pending transactions."""
        # Take up to 1000 txs per block for throughput
        batch = self.pending_txs[:1000]
        self.pending_txs = self.pending_txs[1000:]

        for tx in batch:
            tx.status = "confirmed"

        block = Block(
            slot=slot,
            epoch=epoch,
            producer=producer,
            parent_hash=self.tip.block_hash,
            transactions=batch,
        )
        self.blocks.append(block)
        return block

    def get_block(self, slot: int) -> Block | None:
        for b in self.blocks:
            if b.slot == slot:
                return b
        return None

    def get_transaction(self, tx_hash: str) -> Transaction | None:
        return self.tx_index.get(tx_hash)

    def stats(self) -> dict[str, Any]:
        total_txs = sum(b.tx_count for b in self.blocks)
        return {
            "height": self.height,
            "total_transactions": total_txs,
            "pending_transactions": len(self.pending_txs),
            "tip_hash": self.tip.block_hash[:16],
        }
