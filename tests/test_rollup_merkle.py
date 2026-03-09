"""Tests for sparse merkle tree used in rollup state proofs."""

from autono.rollup.merkle import SparseMerkleTree


class TestSparseMerkleTree:
    def test_empty_tree_has_root(self):
        tree = SparseMerkleTree()
        assert tree.root is not None
        assert isinstance(tree.root, str)
        assert len(tree.root) == 64  # sha256 hex

    def test_insert_changes_root(self):
        tree = SparseMerkleTree()
        old_root = tree.root
        tree.put(b"alice", b"1000")
        assert tree.root != old_root

    def test_get_returns_inserted_value(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        assert tree.get(b"alice") == b"1000"

    def test_get_missing_key_returns_none(self):
        tree = SparseMerkleTree()
        assert tree.get(b"nonexistent") is None

    def test_update_existing_key(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        tree.put(b"alice", b"2000")
        assert tree.get(b"alice") == b"2000"

    def test_multiple_keys_independent(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        tree.put(b"bob", b"500")
        assert tree.get(b"alice") == b"1000"
        assert tree.get(b"bob") == b"500"

    def test_deterministic_root(self):
        """Same inserts in same order produce identical root."""
        t1 = SparseMerkleTree()
        t2 = SparseMerkleTree()
        t1.put(b"alice", b"1000")
        t1.put(b"bob", b"500")
        t2.put(b"alice", b"1000")
        t2.put(b"bob", b"500")
        assert t1.root == t2.root

    def test_order_independent_root(self):
        """Same key-value pairs inserted in different order produce same root."""
        t1 = SparseMerkleTree()
        t2 = SparseMerkleTree()
        t1.put(b"alice", b"1000")
        t1.put(b"bob", b"500")
        t2.put(b"bob", b"500")
        t2.put(b"alice", b"1000")
        assert t1.root == t2.root

    def test_generate_proof(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        tree.put(b"bob", b"500")
        proof = tree.prove(b"alice")
        assert proof is not None
        assert "key" in proof
        assert "value" in proof
        assert "siblings" in proof
        assert "root" in proof

    def test_verify_valid_proof(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        tree.put(b"bob", b"500")
        proof = tree.prove(b"alice")
        assert SparseMerkleTree.verify(proof)

    def test_verify_tampered_proof_fails(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        proof = tree.prove(b"alice")
        proof["value"] = b"9999"  # tamper
        assert not SparseMerkleTree.verify(proof)

    def test_verify_wrong_root_fails(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        proof = tree.prove(b"alice")
        proof["root"] = "0" * 64  # wrong root
        assert not SparseMerkleTree.verify(proof)

    def test_proof_for_missing_key_returns_none(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        proof = tree.prove(b"nonexistent")
        assert proof is None

    def test_delete_key(self):
        tree = SparseMerkleTree()
        tree.put(b"alice", b"1000")
        tree.delete(b"alice")
        assert tree.get(b"alice") is None

    def test_delete_restores_root(self):
        tree = SparseMerkleTree()
        empty_root = tree.root
        tree.put(b"alice", b"1000")
        tree.delete(b"alice")
        assert tree.root == empty_root

    def test_large_tree_performance(self):
        """1000 inserts should complete in under 1 second."""
        import time
        tree = SparseMerkleTree()
        start = time.time()
        for i in range(1000):
            tree.put(f"addr_{i}".encode(), f"{i * 100}".encode())
        elapsed = time.time() - start
        assert elapsed < 1.0, f"1000 inserts took {elapsed:.2f}s"
        # Verify random sample
        assert tree.get(b"addr_500") == b"50000"
