"""JSON-based persistent store for the knowledge graph.

Storage is cheap. JSON files are lightweight. This beats training an LLM
on billions of parameters — just store the facts and let agents navigate.

Directory structure:
    ~/.autono/knowledge/
    ├── nodes/           # Individual node JSON files
    ├── links/           # Link definitions
    ├── locks/           # Lock and mLock definitions
    ├── embeds/          # Embedding vectors (numpy or raw floats)
    ├── research/        # .md files from ResearchManager
    └── index.json       # Master index for fast lookup
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from autono.knowledge.types import (
    KnowledgeNode,
    Link,
    Lock,
    MLock,
    NodeStatus,
)

log = structlog.get_logger()


class KnowledgeStore:
    """Persistent JSON store for the Links & Locks knowledge system.

    All data is stored as flat JSON files — no database required.
    The ExpansionManager watches for changes and triggers updates.
    """

    def __init__(self, base_path: str | None = None) -> None:
        self.base_path = Path(base_path or os.path.expanduser("~/.autono/knowledge"))
        self._ensure_dirs()
        self._index: dict[str, Any] = self._load_index()

    def _ensure_dirs(self) -> None:
        for subdir in ["nodes", "links", "locks", "embeds", "research"]:
            (self.base_path / subdir).mkdir(parents=True, exist_ok=True)

    def _load_index(self) -> dict[str, Any]:
        index_path = self.base_path / "index.json"
        if index_path.exists():
            with open(index_path) as f:
                return json.load(f)
        return {
            "nodes": {},
            "links": {},
            "locks": {},
            "mlocks": {},
            "domain_index": {},
            "tag_index": {},
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }

    def _save_index(self) -> None:
        self._index["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(self.base_path / "index.json", "w") as f:
            json.dump(self._index, f, indent=2)

    # -- Node operations --------------------------------------------------

    def save_node(self, node: KnowledgeNode) -> None:
        """Persist a knowledge node to disk."""
        data = _dataclass_to_dict(node)
        path = self.base_path / "nodes" / f"{node.id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        # Update indexes
        self._index["nodes"][node.id] = {
            "domain": node.domain,
            "subdomain": node.subdomain,
            "status": node.status.value if isinstance(node.status, NodeStatus) else node.status,
            "is_locked": node.is_locked,
            "is_mlocked": node.is_mlocked,
            "volatility": node.volatility.value if hasattr(node.volatility, "value") else node.volatility,
        }

        # Domain index
        domain_key = f"{node.domain}:{node.subdomain}" if node.subdomain else node.domain
        if domain_key not in self._index["domain_index"]:
            self._index["domain_index"][domain_key] = []
        if node.id not in self._index["domain_index"][domain_key]:
            self._index["domain_index"][domain_key].append(node.id)

        # Tag index
        for tag in node.tags:
            if tag not in self._index["tag_index"]:
                self._index["tag_index"][tag] = []
            if node.id not in self._index["tag_index"][tag]:
                self._index["tag_index"][tag].append(node.id)

        self._save_index()
        log.debug("store.node_saved", node_id=node.id, domain=node.domain)

    def load_node(self, node_id: str) -> KnowledgeNode | None:
        """Load a node from disk."""
        path = self.base_path / "nodes" / f"{node_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return _dict_to_node(data)

    def delete_node(self, node_id: str) -> None:
        """Remove a node from disk and all indexes."""
        path = self.base_path / "nodes" / f"{node_id}.json"
        if path.exists():
            path.unlink()

        # Clean indexes
        self._index["nodes"].pop(node_id, None)
        for domain_nodes in self._index["domain_index"].values():
            if node_id in domain_nodes:
                domain_nodes.remove(node_id)
        for tag_nodes in self._index["tag_index"].values():
            if node_id in tag_nodes:
                tag_nodes.remove(node_id)

        self._save_index()
        log.info("store.node_deleted", node_id=node_id)

    def find_nodes_by_domain(self, domain: str, subdomain: str = "") -> list[str]:
        """Find node IDs by domain."""
        key = f"{domain}:{subdomain}" if subdomain else domain
        return self._index["domain_index"].get(key, [])

    def find_nodes_by_tag(self, tag: str) -> list[str]:
        """Find node IDs by tag."""
        return self._index["tag_index"].get(tag, [])

    def find_nodes_by_status(self, status: str) -> list[str]:
        """Find all nodes with a given status."""
        return [
            nid for nid, meta in self._index["nodes"].items()
            if meta.get("status") == status
        ]

    def find_locked_nodes(self) -> list[str]:
        """Find all nodes that have locks or mlocks."""
        return [
            nid for nid, meta in self._index["nodes"].items()
            if meta.get("is_locked") or meta.get("is_mlocked")
        ]

    # -- Link operations --------------------------------------------------

    def save_link(self, link: Link) -> None:
        data = _dataclass_to_dict(link)
        path = self.base_path / "links" / f"{link.id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._index["links"][link.id] = {
            "source": link.source_node_id,
            "target": link.target_node_id,
            "relationship": link.relationship.value if hasattr(link.relationship, "value") else link.relationship,
            "weight": link.shortcut_weight,
        }
        self._save_index()

    def load_link(self, link_id: str) -> Link | None:
        path = self.base_path / "links" / f"{link_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return _dict_to_link(data)

    def delete_link(self, link_id: str) -> None:
        path = self.base_path / "links" / f"{link_id}.json"
        if path.exists():
            path.unlink()
        self._index["links"].pop(link_id, None)
        self._save_index()
        log.info("store.link_deleted", link_id=link_id)

    def find_links_for_node(self, node_id: str) -> list[str]:
        """Find all links that touch a given node."""
        return [
            lid for lid, meta in self._index["links"].items()
            if meta.get("source") == node_id or meta.get("target") == node_id
        ]

    # -- Lock operations --------------------------------------------------

    def save_lock(self, lock: Lock) -> None:
        data = _dataclass_to_dict(lock)
        path = self.base_path / "locks" / f"{lock.id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._index["locks"][lock.id] = {
            "node_id": lock.node_id,
            "status": lock.status.value if hasattr(lock.status, "value") else lock.status,
            "answer_type": lock.answer_type,
        }
        self._save_index()

    def save_mlock(self, mlock: MLock) -> None:
        data = _dataclass_to_dict(mlock)
        path = self.base_path / "locks" / f"{mlock.id}.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        self._index["mlocks"][mlock.id] = {
            "status": mlock.status.value if hasattr(mlock.status, "value") else mlock.status,
            "payload_type": mlock.payload_type,
            "path_count": len(mlock.incoming_links),
        }
        self._save_index()

    def load_lock(self, lock_id: str) -> Lock | None:
        path = self.base_path / "locks" / f"{lock_id}.json"
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        return _dict_to_lock(data)

    def find_locks_by_status(self, status: str) -> list[str]:
        """Find locks by their status (active, shattered, etc.)."""
        results = []
        for lid, meta in self._index["locks"].items():
            if meta.get("status") == status:
                results.append(lid)
        for mid, meta in self._index["mlocks"].items():
            if meta.get("status") == status:
                results.append(mid)
        return results

    # -- Research file tracking -------------------------------------------

    def save_research(self, filename: str, content: str) -> str:
        """Save a research .md file and return its content hash."""
        path = self.base_path / "research" / filename
        with open(path, "w") as f:
            f.write(content)
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        log.info("store.research_saved", file=filename, hash=content_hash)
        return content_hash

    def list_research_files(self) -> list[str]:
        """List all research .md files."""
        research_dir = self.base_path / "research"
        return [f.name for f in research_dir.iterdir() if f.suffix == ".md"]

    def load_research(self, filename: str) -> str | None:
        path = self.base_path / "research" / filename
        if not path.exists():
            return None
        with open(path) as f:
            return f.read()

    # -- Stats ------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return store statistics."""
        return {
            "total_nodes": len(self._index["nodes"]),
            "total_links": len(self._index["links"]),
            "total_locks": len(self._index["locks"]),
            "total_mlocks": len(self._index["mlocks"]),
            "domains": list(self._index["domain_index"].keys()),
            "tags": list(self._index["tag_index"].keys()),
            "locked_nodes": len(self.find_locked_nodes()),
            "stale_nodes": len(self.find_nodes_by_status("stale")),
        }


# -- Serialization helpers ------------------------------------------------

def _dataclass_to_dict(obj: Any) -> dict[str, Any]:
    """Convert a dataclass to a JSON-serializable dict."""
    result = {}
    for key, value in obj.__dict__.items():
        if hasattr(value, "value"):  # Enum
            result[key] = value.value
        elif isinstance(value, list):
            result[key] = [
                _dataclass_to_dict(v) if hasattr(v, "__dict__") and not isinstance(v, str) else v
                for v in value
            ]
        else:
            result[key] = value
    return result


def _dict_to_node(data: dict) -> KnowledgeNode:
    node = KnowledgeNode()
    for key, value in data.items():
        if key == "status":
            value = NodeStatus(value)
        elif key == "volatility":
            from autono.knowledge.types import VolatilityTier
            value = VolatilityTier(value)
        if hasattr(node, key):
            setattr(node, key, value)
    return node


def _dict_to_link(data: dict) -> Link:
    from autono.knowledge.types import LinkRelationship
    link = Link()
    for key, value in data.items():
        if key == "relationship":
            value = LinkRelationship(value)
        if hasattr(link, key):
            setattr(link, key, value)
    return link


def _dict_to_lock(data: dict) -> Lock:
    lock = Lock()
    for key, value in data.items():
        if key == "status":
            value = NodeStatus(value)
        if hasattr(lock, key):
            setattr(lock, key, value)
    return lock
