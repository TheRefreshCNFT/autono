"""Sparse Merkle Tree for rollup state proofs.

Used for:
- Computing state root (posted to Cardano L1 during settlement)
- Generating balance proofs (for force exit)
- Verifying proofs (bridge contract logic)

Implementation: sorted-leaf hash tree. Keys are SHA-256 hashed.
Leaves store (key, value). Root = hash of all leaf hashes in sorted
key order. Proofs contain sibling leaf hashes — verifier recomputes
root from target leaf + siblings.

This is practical for <1M accounts. For production scale, upgrade to
a full 256-level sparse merkle tree with level-cached hashes.
"""

from __future__ import annotations

import hashlib
from typing import Any


def _sha256(data: bytes) -> str:
    """SHA-256 hash returning hex string."""
    return hashlib.sha256(data).hexdigest()


def _sha256_bytes(data: bytes) -> bytes:
    """SHA-256 hash returning raw bytes."""
    return hashlib.sha256(data).digest()


# Empty tree root — hash of empty string
_EMPTY_ROOT = _sha256(b"")


class SparseMerkleTree:
    """Sparse merkle tree backed by sorted-leaf hashing.

    Properties:
    - Deterministic: same key-value set always produces same root
    - Order-independent: insert order doesn't matter
    - Provable: any leaf can generate a proof verifiable against root
    - Compact: only stores non-empty leaves
    """

    def __init__(self) -> None:
        self._leaves: dict[str, tuple[bytes, bytes]] = {}  # key_hash -> (key, value)
        self._root: str | None = None  # invalidated on mutation

    @property
    def root(self) -> str:
        """Current state root hash."""
        if self._root is None:
            self._root = self._compute_root()
        return self._root

    def put(self, key: bytes, value: bytes) -> None:
        """Insert or update a key-value pair."""
        key_hash = _sha256(key)
        self._leaves[key_hash] = (key, value)
        self._root = None  # invalidate

    def get(self, key: bytes) -> bytes | None:
        """Retrieve value by key, or None if not present."""
        key_hash = _sha256(key)
        entry = self._leaves.get(key_hash)
        return entry[1] if entry else None

    def delete(self, key: bytes) -> None:
        """Remove a key from the tree."""
        key_hash = _sha256(key)
        if key_hash in self._leaves:
            del self._leaves[key_hash]
            self._root = None  # invalidate

    def prove(self, key: bytes) -> dict[str, Any] | None:
        """Generate a merkle inclusion proof for a key.

        Returns None if the key doesn't exist.
        Returns dict with: key, value, key_hash, siblings, root.

        The proof allows anyone to recompute the root from:
        - The target leaf hash
        - All sibling leaf hashes (sorted)
        """
        key_hash = _sha256(key)
        if key_hash not in self._leaves:
            return None

        _, value = self._leaves[key_hash]

        # Siblings = all OTHER leaf hashes in sorted order
        target_leaf_hash = self._leaf_hash(key_hash, value)
        siblings: list[str] = []
        for kh in sorted(self._leaves.keys()):
            if kh != key_hash:
                _, v = self._leaves[kh]
                siblings.append(self._leaf_hash(kh, v))

        return {
            "key": key,
            "value": value,
            "key_hash": key_hash,
            "siblings": siblings,
            "root": self.root,
        }

    @staticmethod
    def verify(proof: dict[str, Any]) -> bool:
        """Verify a merkle proof against its claimed root.

        Recomputes root from target leaf + siblings and checks
        against the claimed root.
        """
        key = proof["key"]
        value = proof["value"]
        siblings = proof["siblings"]
        claimed_root = proof["root"]

        key_hash = _sha256(key)
        target_leaf_hash = _leaf_hash_static(key_hash, value)

        # Reconstruct: sort all leaf hashes (target + siblings), hash together
        all_hashes = sorted([target_leaf_hash] + list(siblings))
        combined = "".join(all_hashes)
        computed_root = _sha256(combined.encode())

        return computed_root == claimed_root

    def _compute_root(self) -> str:
        """Compute root from all leaves.

        Sorts by leaf hash value (not key hash) so verify() can
        reconstruct the same root from target + siblings.
        """
        if not self._leaves:
            return _EMPTY_ROOT

        # Collect all leaf hashes, sort by hash value
        leaf_hashes: list[str] = []
        for key_hash, (_, value) in self._leaves.items():
            leaf_hashes.append(self._leaf_hash(key_hash, value))
        leaf_hashes.sort()

        # Root = hash of concatenated sorted leaf hashes
        combined = "".join(leaf_hashes)
        return _sha256(combined.encode())

    @staticmethod
    def _leaf_hash(key_hash: str, value: bytes) -> str:
        """Hash a single leaf: H(key_hash || value)."""
        return _sha256(key_hash.encode() + value)


def _leaf_hash_static(key_hash: str, value: bytes) -> str:
    """Module-level leaf hash for use in static verify method."""
    return _sha256(key_hash.encode() + value)
