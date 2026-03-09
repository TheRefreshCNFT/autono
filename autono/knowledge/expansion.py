"""Knowledge Expansion Engine — fills the brain to capacity.

This engine:
1. INITIALIZES: Seeds ALL protocol facts from protocol_facts.py into the graph
2. VALIDATES: Checks existing locks against current sources
3. EXPANDS: Scrapes all configured research sources for new facts
4. LINKS: Creates connections between related facts across domains
5. SCHEDULES: Re-validates facts based on their volatility tier
6. REPORTS: Tracks brain coverage and identifies gaps

The expansion engine is designed to get the brain to 100% coverage.
It runs as a service, not as an agent (agents consume its output).
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any

import structlog

from autono.knowledge.graph import KnowledgeGraph
from autono.knowledge.store import KnowledgeStore
from autono.knowledge.types import (
    KnowledgeNode,
    Link,
    LinkRelationship,
    Lock,
    NodeStatus,
    VolatilityTier,
    VOLATILITY_INTERVALS,
)
from autono.services.scraper import Scraper

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Cross-domain linking rules
# ---------------------------------------------------------------------------

CROSS_DOMAIN_LINKS: list[dict[str, Any]] = [
    {
        "source_tags": ["utxo", "cardano"],
        "target_tags": ["utxo", "bitcoin"],
        "relationship": "commonly_paired",
        "description": "Both use UTXO model",
    },
    {
        "source_tags": ["charms", "spell"],
        "target_tags": ["op_return", "bitcoin"],
        "relationship": "requires",
        "description": "Charms spells require Bitcoin OP_RETURN",
    },
    {
        "source_tags": ["charms", "bridge"],
        "target_tags": ["bitcoinos", "bridge"],
        "relationship": "commonly_paired",
        "description": "Both bridges use ZK proof verification",
    },
    {
        "source_tags": ["night-chain", "midnight"],
        "target_tags": ["cardano", "protocol"],
        "relationship": "derives_from",
        "description": "Night chain is a Cardano sidechain",
    },
    {
        "source_tags": ["plutus", "smart-contract"],
        "target_tags": ["opshin", "smart-contract"],
        "relationship": "commonly_paired",
        "description": "OpShin compiles Python to Plutus Core",
    },
    {
        "source_tags": ["plutus", "smart-contract"],
        "target_tags": ["helios", "smart-contract"],
        "relationship": "commonly_paired",
        "description": "Helios compiles JS to Plutus Core",
    },
    {
        "source_tags": ["blockfrost", "api"],
        "target_tags": ["koios", "api"],
        "relationship": "alternative",
        "description": "Alternative Cardano API providers",
    },
    {
        "source_tags": ["taproot", "bitcoin"],
        "target_tags": ["charms", "protocol"],
        "relationship": "commonly_paired",
        "description": "Charms leverages Taproot witness space",
    },
    {
        "source_tags": ["zk", "privacy"],
        "target_tags": ["bitsnark", "zk"],
        "relationship": "commonly_paired",
        "description": "ZK proof systems used across chains",
    },
    {
        "source_tags": ["psbt", "transaction"],
        "target_tags": ["charms", "spell"],
        "relationship": "commonly_paired",
        "description": "Charms spells are constructed via PSBT flow",
    },
    {
        "source_tags": ["meshjs", "sdk"],
        "target_tags": ["blockfrost", "api"],
        "relationship": "requires",
        "description": "MeshJS uses Blockfrost as default provider",
    },
    {
        "source_tags": ["cip", "standard"],
        "target_tags": ["bip", "standard"],
        "relationship": "commonly_paired",
        "description": "CIPs and BIPs both define chain improvement proposals",
    },
    {
        "source_tags": ["grail", "bridge"],
        "target_tags": ["zkbtc"],
        "relationship": "results_in",
        "description": "Grail Bridge produces zkBTC wrapped tokens",
    },
    {
        "source_tags": ["compact", "language"],
        "target_tags": ["zk", "privacy"],
        "relationship": "requires",
        "description": "Compact language requires ZK circuit compilation",
    },
    {
        "source_tags": ["mempool", "api"],
        "target_tags": ["bitcoin", "fees"],
        "relationship": "results_in",
        "description": "Mempool API provides real-time fee estimates",
    },
]

# Expected knowledge domains and their subdomains for gap analysis
EXPECTED_COVERAGE: dict[str, list[str]] = {
    "cardano": [
        "protocol", "cip", "sdk", "api", "smart-contract",
        "wallet", "staking", "governance",
    ],
    "bitcoin": [
        "protocol", "bip", "api", "script", "taproot",
        "psbt", "lightning", "mining",
    ],
    "charms": [
        "protocol", "spell_format", "development", "bridge", "apps",
    ],
    "bitcoinos": [
        "protocol", "bridge", "development", "zkbtc",
    ],
    "night_chain": [
        "protocol", "sdk", "privacy", "compact",
    ],
}


class KnowledgeExpansionEngine:
    """Orchestrates knowledge graph population, validation, and maintenance.

    This is the workhorse that takes raw protocol facts, scraped web data,
    and cross-domain rules, then wires everything into the knowledge graph.
    Agents never call this directly — they navigate the finished graph.
    """

    def __init__(
        self,
        store: KnowledgeStore,
        scraper: Scraper,
        graph: KnowledgeGraph | None = None,
    ) -> None:
        self.store = store
        self.scraper = scraper
        self.graph = graph

        # Expansion state tracking
        self._last_expansion: str = ""
        self._facts_loaded: int = 0
        self._facts_validated: int = 0
        self._gaps_found: int = 0
        self._errors: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Seeding — load all protocol facts into the graph
    # ------------------------------------------------------------------

    def seed_all_facts(self) -> dict[str, Any]:
        """Import ALL_PROTOCOL_FACTS and seed them into the knowledge store.

        For each fact:
        - Creates a KnowledgeNode with proper domain, subdomain, volatility, tags
        - Saves to store
        - Creates a Lock with the deterministic answer
        - Links the lock to the node

        Skips facts that already exist (checked by content hash).

        Returns:
            Stats dict with seeded, skipped, and error counts.
        """
        stats: dict[str, Any] = {"seeded": 0, "skipped": 0, "errors": 0}

        try:
            from autono.knowledge.protocol_facts import ALL_PROTOCOL_FACTS
        except ImportError:
            log.warning(
                "expansion.seed.no_protocol_facts",
                msg="protocol_facts module not found — nothing to seed",
            )
            stats["errors"] = 1
            self._errors.append({
                "phase": "seed",
                "error": "protocol_facts module not found",
                "ts": _now_iso(),
            })
            return stats

        log.info("expansion.seed.start", total_facts=len(ALL_PROTOCOL_FACTS))

        for fact in ALL_PROTOCOL_FACTS:
            try:
                content = fact.get("fact", fact.get("content", ""))
                if not content:
                    stats["errors"] += 1
                    continue

                # Deterministic ID from content hash so we can skip duplicates
                content_hash = _content_hash(content)
                node_id = f"node_{content_hash}"

                # Check if already exists
                existing = self.store.load_node(node_id)
                if existing is not None:
                    stats["skipped"] += 1
                    continue

                # Map volatility string to enum
                volatility = _parse_volatility(
                    fact.get("volatility", "stable")
                )

                # Build node
                node = KnowledgeNode(
                    id=node_id,
                    content=content,
                    domain=fact.get("domain", ""),
                    subdomain=fact.get("subdomain", ""),
                    volatility=volatility,
                    tags=list(fact.get("tags", [])),
                    source_file="protocol_facts.py",
                    source_hash=content_hash,
                    bypass_llm=True,
                    priority_score=fact.get("priority", 80),
                )

                # Create lock with the deterministic answer
                answer = fact.get("answer", fact.get("absolute_answer", content))
                answer_type = fact.get("answer_type", "string")
                verification = fact.get("verification_source", fact.get("source", "protocol_facts"))

                lock = Lock(
                    node_id=node_id,
                    absolute_answer=answer,
                    answer_type=answer_type,
                    verification_source=verification,
                    status=NodeStatus.ACTIVE,
                )
                lock.compute_dependency_hash(content, str(answer))

                # Wire them together
                node.lock_id = lock.id
                node.is_locked = True

                # Persist
                self.store.save_node(node)
                self.store.save_lock(lock)
                stats["seeded"] += 1

            except Exception as exc:
                stats["errors"] += 1
                self._errors.append({
                    "phase": "seed",
                    "fact": str(fact)[:120],
                    "error": str(exc),
                    "ts": _now_iso(),
                })
                log.warning("expansion.seed.fact_error", error=str(exc))

        self._facts_loaded += stats["seeded"]
        log.info("expansion.seed.done", **stats)
        return stats

    # ------------------------------------------------------------------
    # Validation — check all locks for staleness
    # ------------------------------------------------------------------

    def validate_all_locks(self) -> dict[str, Any]:
        """Iterate all locked nodes and check for staleness.

        Compares each lock's last_validated timestamp against the volatility
        interval for its tier. Stale locks are marked for re-validation.

        Returns:
            Stats dict with valid, stale, shattered, and total counts.
        """
        stats: dict[str, Any] = {"valid": 0, "stale": 0, "shattered": 0, "total": 0}
        now_ts = time.time()

        locked_node_ids = self.store.find_locked_nodes()
        stats["total"] = len(locked_node_ids)

        log.info("expansion.validate.start", total_locked=stats["total"])

        for node_id in locked_node_ids:
            try:
                node = self.store.load_node(node_id)
                if not node or not node.lock_id:
                    continue

                lock = self.store.load_lock(node.lock_id)
                if not lock:
                    continue

                # Already shattered — count but skip
                if lock.status == NodeStatus.SHATTERED:
                    stats["shattered"] += 1
                    continue

                # Determine staleness window
                interval = VOLATILITY_INTERVALS.get(
                    node.volatility, VOLATILITY_INTERVALS[VolatilityTier.STABLE]
                )

                # PERMANENT nodes (interval=0) never go stale
                if interval == 0 and node.volatility == VolatilityTier.PERMANENT:
                    stats["valid"] += 1
                    continue

                # REALTIME nodes (interval=0) are always stale
                if interval == 0 and node.volatility == VolatilityTier.REALTIME:
                    node.mark_stale()
                    self.store.save_node(node)
                    stats["stale"] += 1
                    continue

                # Check timestamp
                last_validated_ts = _iso_to_timestamp(lock.last_validated)
                age = now_ts - last_validated_ts

                if age > interval:
                    node.mark_stale()
                    self.store.save_node(node)
                    stats["stale"] += 1
                else:
                    stats["valid"] += 1

            except Exception as exc:
                self._errors.append({
                    "phase": "validate",
                    "node_id": node_id,
                    "error": str(exc),
                    "ts": _now_iso(),
                })
                log.warning(
                    "expansion.validate.error",
                    node_id=node_id,
                    error=str(exc),
                )

        self._facts_validated += stats["valid"] + stats["stale"]
        log.info("expansion.validate.done", **stats)
        return stats

    # ------------------------------------------------------------------
    # Expansion — scrape sources and ingest new facts
    # ------------------------------------------------------------------

    def expand_from_sources(self) -> dict[str, Any]:
        """Scrape all configured research sources and ingest extracted facts.

        For each source from research_profiles:
        - Crawl using Scraper.crawl_source()
        - Extract facts from scraped content
        - Compare against existing knowledge:
            - New fact → create node + lock
            - Confirms existing → strengthen confidence (refresh timestamp)
            - Contradicts existing → shatter the old lock

        Returns:
            Stats dict with crawl and ingestion counts.
        """
        from autono.agents.chain_specialists.research_profiles import (
            get_all_sources,
        )

        stats: dict[str, Any] = {
            "sources_crawled": 0,
            "pages_scraped": 0,
            "new_facts": 0,
            "confirmations": 0,
            "contradictions": 0,
            "errors": 0,
        }

        all_sources = get_all_sources()
        log.info("expansion.expand.start", total_sources=len(all_sources))

        for source in all_sources:
            try:
                pages = self.scraper.crawl_source(source, max_pages=20)
                stats["sources_crawled"] += 1
                stats["pages_scraped"] += len(pages)

                for page in pages:
                    if not page.ok:
                        continue

                    facts = self.scraper.extract_facts(
                        page,
                        patterns=source.extract_patterns,
                        domain=source.domain,
                        subdomain=source.subdomain,
                    )

                    for fact in facts:
                        result = self._ingest_fact(fact, source.url)
                        if result == "new":
                            stats["new_facts"] += 1
                        elif result == "confirmed":
                            stats["confirmations"] += 1
                        elif result == "contradicted":
                            stats["contradictions"] += 1
                        elif result == "error":
                            stats["errors"] += 1

                # Save research markdown for the source
                if pages:
                    md = self.scraper.pages_to_research_md(pages, source)
                    filename = (
                        f"{source.domain}_{source.subdomain or 'general'}.md"
                    )
                    self.store.save_research(filename, md)

            except Exception as exc:
                stats["errors"] += 1
                self._errors.append({
                    "phase": "expand",
                    "source": source.url[:100],
                    "error": str(exc),
                    "ts": _now_iso(),
                })
                log.warning(
                    "expansion.expand.source_error",
                    source=source.url[:80],
                    error=str(exc),
                )

        self._facts_loaded += stats["new_facts"]
        log.info("expansion.expand.done", **stats)
        return stats

    def _ingest_fact(self, fact: dict[str, Any], source_url: str) -> str:
        """Ingest a single extracted fact into the store.

        Returns one of: 'new', 'confirmed', 'contradicted', 'skipped', 'error'.
        """
        try:
            content = fact.get("fact", "")
            answer = fact.get("answer", "")
            if not content or not answer:
                return "skipped"

            content_hash = _content_hash(content)
            node_id = f"node_{content_hash}"

            existing_node = self.store.load_node(node_id)

            if existing_node is not None:
                # Node exists — check if answer matches (confirmation vs contradiction)
                if existing_node.lock_id:
                    lock = self.store.load_lock(existing_node.lock_id)
                    if lock and lock.status == NodeStatus.ACTIVE:
                        if str(lock.absolute_answer) == str(answer):
                            # Confirmation — refresh validation timestamp
                            lock.last_validated = _now_iso()
                            self.store.save_lock(lock)
                            existing_node.status = NodeStatus.ACTIVE
                            existing_node.last_validated = _now_iso()
                            self.store.save_node(existing_node)
                            return "confirmed"
                        else:
                            # Contradiction — shatter the lock
                            lock.shatter(
                                f"contradicted_by:{source_url[:80]}"
                                f"|old={lock.absolute_answer}"
                                f"|new={answer}"
                            )
                            self.store.save_lock(lock)
                            existing_node.status = NodeStatus.SHATTERED
                            self.store.save_node(existing_node)
                            log.info(
                                "expansion.fact_contradicted",
                                node_id=node_id,
                                old_answer=str(lock.absolute_answer)[:60],
                                new_answer=str(answer)[:60],
                            )
                            return "contradicted"
                return "skipped"

            # Brand new fact — create node + lock
            domain = fact.get("domain", "")
            subdomain = fact.get("subdomain", "")
            tags = list(fact.get("tags", []))
            confidence = fact.get("confidence", 0.5)
            answer_type = fact.get("answer_type", "string")

            volatility = VolatilityTier.MODERATE
            if answer_type in ("constant", "integer"):
                volatility = VolatilityTier.STABLE
            elif answer_type in ("endpoint", "version"):
                volatility = VolatilityTier.VOLATILE

            node = KnowledgeNode(
                id=node_id,
                content=content,
                domain=domain,
                subdomain=subdomain,
                volatility=volatility,
                tags=tags,
                source_file=source_url,
                source_hash=content_hash,
                bypass_llm=confidence >= 0.7,
                priority_score=int(confidence * 100),
            )

            lock = Lock(
                node_id=node_id,
                absolute_answer=answer,
                answer_type=answer_type,
                verification_source=source_url,
                status=NodeStatus.ACTIVE,
            )
            lock.compute_dependency_hash(content, str(answer))

            node.lock_id = lock.id
            node.is_locked = True

            self.store.save_node(node)
            self.store.save_lock(lock)
            return "new"

        except Exception as exc:
            self._errors.append({
                "phase": "ingest",
                "fact": str(fact)[:120],
                "error": str(exc),
                "ts": _now_iso(),
            })
            log.warning("expansion.ingest.error", error=str(exc))
            return "error"

    # ------------------------------------------------------------------
    # Cross-domain linking
    # ------------------------------------------------------------------

    def build_cross_domain_links(self) -> dict[str, Any]:
        """Find facts that share tags across different domains and link them.

        Uses the CROSS_DOMAIN_LINKS rules to match source and target nodes
        based on tag overlap, then creates Link objects between them.

        Returns:
            Stats dict with links_created and domains_connected counts.
        """
        stats: dict[str, Any] = {"links_created": 0, "domains_connected": set()}

        log.info(
            "expansion.link.start",
            rules=len(CROSS_DOMAIN_LINKS),
        )

        for rule in CROSS_DOMAIN_LINKS:
            source_tags = rule["source_tags"]
            target_tags = rule["target_tags"]
            relationship_str = rule["relationship"]
            description = rule.get("description", "")

            try:
                relationship = LinkRelationship(relationship_str)
            except ValueError:
                relationship = LinkRelationship.COMMONLY_PAIRED

            # Find candidate nodes for each side
            source_nodes = self._find_nodes_matching_tags(source_tags)
            target_nodes = self._find_nodes_matching_tags(target_tags)

            if not source_nodes or not target_nodes:
                continue

            # Create links between the best matches (cap per rule to avoid
            # combinatorial explosion)
            links_for_rule = 0
            max_links_per_rule = 10

            for src_id in source_nodes:
                if links_for_rule >= max_links_per_rule:
                    break

                src_node = self.store.load_node(src_id)
                if not src_node or src_node.status == NodeStatus.PRUNED:
                    continue

                for tgt_id in target_nodes:
                    if links_for_rule >= max_links_per_rule:
                        break
                    if src_id == tgt_id:
                        continue

                    tgt_node = self.store.load_node(tgt_id)
                    if not tgt_node or tgt_node.status == NodeStatus.PRUNED:
                        continue

                    # Skip if these nodes are already linked
                    if self._nodes_already_linked(src_id, tgt_id):
                        continue

                    # Create the link
                    link = Link(
                        source_node_id=src_id,
                        target_node_id=tgt_id,
                        relationship=relationship,
                        shortcut_weight=0.6,
                        description=description,
                    )

                    self.store.save_link(link)

                    # Wire link IDs into both nodes
                    src_node.link_ids.append(link.id)
                    self.store.save_node(src_node)

                    tgt_node.link_ids.append(link.id)
                    self.store.save_node(tgt_node)

                    stats["links_created"] += 1
                    stats["domains_connected"].add(src_node.domain)
                    stats["domains_connected"].add(tgt_node.domain)
                    links_for_rule += 1

        stats["domains_connected"] = len(stats["domains_connected"])
        log.info("expansion.link.done", **stats)
        return stats

    def _find_nodes_matching_tags(self, tags: list[str]) -> list[str]:
        """Find node IDs that match ALL of the given tags."""
        if not tags:
            return []

        # Start with nodes matching the first tag, intersect with the rest
        candidate_ids: set[str] | None = None

        for tag in tags:
            tag_nodes = set(self.store.find_nodes_by_tag(tag))
            if candidate_ids is None:
                candidate_ids = tag_nodes
            else:
                candidate_ids &= tag_nodes

        if candidate_ids is None:
            return []

        # If strict intersection is empty, fall back to nodes matching ANY tag
        if not candidate_ids:
            all_ids: set[str] = set()
            for tag in tags:
                all_ids.update(self.store.find_nodes_by_tag(tag))
            return list(all_ids)[:20]

        return list(candidate_ids)[:20]

    def _nodes_already_linked(self, node_a: str, node_b: str) -> bool:
        """Check whether two nodes are already connected by a link."""
        links_a = self.store.find_links_for_node(node_a)
        links_b = set(self.store.find_links_for_node(node_b))
        return bool(set(links_a) & links_b)

    # ------------------------------------------------------------------
    # Gap analysis
    # ------------------------------------------------------------------

    def identify_gaps(self) -> dict[str, Any]:
        """Compare expected knowledge coverage against actual store contents.

        Checks each domain/subdomain defined in EXPECTED_COVERAGE against
        what is actually present in the store.

        Returns:
            Per-domain report with coverage percentages, missing topics,
            and counts of stale facts.
        """
        gaps: dict[str, Any] = {}
        total_missing = 0

        log.info("expansion.gaps.start", domains=len(EXPECTED_COVERAGE))

        for domain, expected_subdomains in EXPECTED_COVERAGE.items():
            domain_report: dict[str, Any] = {
                "coverage_pct": 0.0,
                "missing_topics": [],
                "stale_facts": 0,
                "total_nodes": 0,
                "locked_nodes": 0,
            }

            covered_subdomains = 0

            for subdomain in expected_subdomains:
                node_ids = self.store.find_nodes_by_domain(domain, subdomain)
                if node_ids:
                    covered_subdomains += 1
                    domain_report["total_nodes"] += len(node_ids)

                    # Count stale and locked
                    for nid in node_ids:
                        node = self.store.load_node(nid)
                        if node:
                            if node.status == NodeStatus.STALE:
                                domain_report["stale_facts"] += 1
                            if node.is_locked:
                                domain_report["locked_nodes"] += 1
                else:
                    domain_report["missing_topics"].append(subdomain)

            # Also count nodes filed under the bare domain (no subdomain)
            bare_nodes = self.store.find_nodes_by_domain(domain)
            domain_report["total_nodes"] += len(bare_nodes)

            if expected_subdomains:
                domain_report["coverage_pct"] = round(
                    (covered_subdomains / len(expected_subdomains)) * 100, 1
                )

            total_missing += len(domain_report["missing_topics"])
            gaps[domain] = domain_report

        self._gaps_found = total_missing
        log.info(
            "expansion.gaps.done",
            total_missing=total_missing,
            domains_analyzed=len(gaps),
        )
        return gaps

    # ------------------------------------------------------------------
    # Volatility scheduling
    # ------------------------------------------------------------------

    def get_stale_facts(self) -> list[str]:
        """Return node IDs that need re-validation based on volatility tier.

        Schedule:
        - PERMANENT: never
        - STABLE: weekly (604,800 s)
        - MODERATE: daily (86,400 s)
        - VOLATILE: hourly (3,600 s)
        - REALTIME: every access (always returned as stale)

        Returns:
            List of node IDs whose locks have exceeded their freshness window.
        """
        stale_ids: list[str] = []
        now_ts = time.time()

        for node_id, meta in self.store._index.get("nodes", {}).items():
            volatility_str = meta.get("volatility", "stable")
            try:
                volatility = VolatilityTier(volatility_str)
            except ValueError:
                volatility = VolatilityTier.STABLE

            # PERMANENT never expires
            if volatility == VolatilityTier.PERMANENT:
                continue

            # REALTIME is always stale
            if volatility == VolatilityTier.REALTIME:
                stale_ids.append(node_id)
                continue

            interval = VOLATILITY_INTERVALS.get(volatility, 604_800)
            if interval <= 0:
                continue

            # Load node to inspect timestamp
            node = self.store.load_node(node_id)
            if not node:
                continue

            last_ts = _iso_to_timestamp(node.last_validated)
            if (now_ts - last_ts) > interval:
                stale_ids.append(node_id)

        log.debug("expansion.stale_check", stale_count=len(stale_ids))
        return stale_ids

    # ------------------------------------------------------------------
    # Full expansion orchestration
    # ------------------------------------------------------------------

    def run_full_expansion(self) -> dict[str, Any]:
        """Orchestrate a complete expansion cycle.

        Steps executed in order:
        1. seed_all_facts()       — load protocol facts into the store
        2. expand_from_sources()  — scrape and ingest from research sources
        3. build_cross_domain_links() — wire related facts together
        4. validate_all_locks()   — check freshness of every lock
        5. identify_gaps()        — report coverage holes

        Returns:
            Comprehensive report combining all step outputs.
        """
        started = _now_iso()
        log.info("expansion.full.start")

        report: dict[str, Any] = {
            "started": started,
            "seed": {},
            "expand": {},
            "links": {},
            "validate": {},
            "gaps": {},
            "finished": "",
            "duration_s": 0.0,
        }

        t0 = time.monotonic()

        # 1. Seed deterministic protocol facts
        report["seed"] = self.seed_all_facts()

        # 2. Scrape and ingest from live sources
        report["expand"] = self.expand_from_sources()

        # 3. Wire cross-domain links
        report["links"] = self.build_cross_domain_links()

        # 4. Validate lock freshness
        report["validate"] = self.validate_all_locks()

        # 5. Identify gaps
        report["gaps"] = self.identify_gaps()

        elapsed = time.monotonic() - t0
        report["finished"] = _now_iso()
        report["duration_s"] = round(elapsed, 2)

        self._last_expansion = report["finished"]

        log.info(
            "expansion.full.done",
            duration_s=report["duration_s"],
            seeded=report["seed"].get("seeded", 0),
            new_facts=report["expand"].get("new_facts", 0),
            links_created=report["links"].get("links_created", 0),
        )

        return report

    # ------------------------------------------------------------------
    # Brain status
    # ------------------------------------------------------------------

    def get_brain_status(self) -> dict[str, Any]:
        """Return a comprehensive snapshot of the knowledge graph's health.

        Includes:
        - Total nodes, locks, links, mlocks
        - Coverage percentage per domain
        - Freshness (% of facts validated within their volatility window)
        - Gap count
        - Last expansion timestamp
        """
        store_stats = self.store.stats()
        stale_ids = self.get_stale_facts()
        total_nodes = store_stats.get("total_nodes", 0)

        # Freshness: proportion of non-stale nodes
        freshness_pct = 0.0
        if total_nodes > 0:
            freshness_pct = round(
                ((total_nodes - len(stale_ids)) / total_nodes) * 100, 1
            )

        # Per-domain coverage
        domain_coverage: dict[str, float] = {}
        for domain, expected_subs in EXPECTED_COVERAGE.items():
            covered = 0
            for sub in expected_subs:
                if self.store.find_nodes_by_domain(domain, sub):
                    covered += 1
            if expected_subs:
                domain_coverage[domain] = round(
                    (covered / len(expected_subs)) * 100, 1
                )

        return {
            "total_nodes": store_stats.get("total_nodes", 0),
            "total_locks": store_stats.get("total_locks", 0),
            "total_links": store_stats.get("total_links", 0),
            "total_mlocks": store_stats.get("total_mlocks", 0),
            "locked_nodes": store_stats.get("locked_nodes", 0),
            "stale_nodes": len(stale_ids),
            "freshness_pct": freshness_pct,
            "domain_coverage": domain_coverage,
            "gap_count": self._gaps_found,
            "errors_logged": len(self._errors),
            "last_expansion": self._last_expansion,
            "domains": store_stats.get("domains", []),
            "tags": store_stats.get("tags", []),
        }


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------

def _content_hash(text: str) -> str:
    """Deterministic short hash for deduplication."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    """Current UTC timestamp in ISO 8601."""
    return datetime.now(timezone.utc).isoformat()


def _iso_to_timestamp(iso_str: str) -> float:
    """Parse an ISO 8601 string into a Unix timestamp.

    Returns 0.0 on failure so stale checks default to 'needs re-validation'.
    """
    if not iso_str:
        return 0.0
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.timestamp()
    except (ValueError, TypeError):
        return 0.0


def _parse_volatility(value: str) -> VolatilityTier:
    """Safely convert a string to a VolatilityTier enum."""
    try:
        return VolatilityTier(value.lower())
    except ValueError:
        return VolatilityTier.STABLE
