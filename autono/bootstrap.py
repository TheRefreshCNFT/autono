"""Bootstrap — seeds the knowledge graph and proves the Links & Locks flow.

This script:
1. Creates the CrossChainOrchestrator (store + graph + all agents)
2. Seeds all protocol facts from chain specialist agents
3. Creates Locks for deterministic facts
4. Generates embeddings for all nodes
5. Runs semantic queries to prove the system works
6. Demonstrates lock hits (instant answers, zero inference)
7. Shows cross-chain bridge routing
8. [NEW] Live research scraping — each agent scrapes its expert domains

Run: python -m autono.bootstrap
Options:
  --persist     Save to ~/.autono/knowledge (default: temp dir)
  --scrape      Run live research scraping from all domain sources
"""

from __future__ import annotations

import asyncio
import sys
import tempfile
import time
from typing import Any

import structlog

log = structlog.get_logger()


def banner(text: str) -> None:
    width = max(len(text) + 4, 60)
    print(f"\n{'=' * width}")
    print(f"  {text}")
    print(f"{'=' * width}")


def section(text: str) -> None:
    print(f"\n--- {text} ---")


def show(label: str, value: Any) -> None:
    if isinstance(value, dict):
        print(f"  {label}:")
        for k, v in value.items():
            print(f"    {k}: {v}")
    else:
        print(f"  {label}: {value}")


async def seed_protocol_facts(orch: Any) -> int:
    """Create nodes and locks from all chain agents' protocol facts."""
    from autono.knowledge.types import KnowledgeNode, Lock, VolatilityTier

    store = orch.store
    all_facts = []
    for agent_name, agent in orch.chain_agents.items():
        if hasattr(agent, "_protocol_facts"):
            for fact in agent._protocol_facts:
                fact["_agent"] = agent_name
                all_facts.append(fact)

    print(f"  Seeding {len(all_facts)} protocol facts from "
          f"{len(orch.chain_agents)} chain agents...")

    for fact_data in all_facts:
        node = KnowledgeNode(
            content=fact_data["fact"],
            domain=fact_data["domain"],
            subdomain=fact_data["subdomain"],
            volatility=VolatilityTier.STABLE,
            tags=fact_data.get("tags", []),
        )
        store.save_node(node)

        lock = Lock(
            node_id=node.id,
            absolute_answer=fact_data["answer"],
            answer_type=fact_data["answer_type"],
            verification_source=fact_data["source"],
        )
        lock.compute_dependency_hash(str(fact_data["answer"]))
        store.save_lock(lock)

        node.is_locked = True
        node.lock_id = lock.id
        node.bypass_llm = True
        store.save_node(node)

    return len(all_facts)


def run_live_scraping(orch: Any) -> dict[str, Any]:
    """Run live research scraping across all domains.

    Each chain agent's domain gets scraped using its expert research profile.
    Returns scraping summary.
    """
    research_mgr = orch.managers.get("ResearchManager")
    if not research_mgr:
        return {"error": "ResearchManager not found"}

    results = research_mgr.scrape_all_domains()
    return results


def run_semantic_queries(orch: Any) -> list[dict]:
    """Run natural language queries against the knowledge graph."""
    questions = [
        "What is the CIP-25 metadata key for NFTs on Cardano?",
        "How many satoshis are in one Bitcoin?",
        "What address prefix does Cardano mainnet use?",
        "What encryption does Night Chain use?",
        "How do Charms spells get stored on Bitcoin?",
        "How do I transfer tokens from Cardano to Bitcoin?",
        "What is the Grail Bridge security model?",
        "What smart contract languages work on Cardano?",
        "What is Taproot used for in Bitcoin?",
        "How does BitSNARK verify ZK proofs?",
        # Wallet queries (new — from WalletSmith knowledge seeding)
        "What derivation path does WALI use for Cardano?",
        "How does WALI encrypt seed phrases?",
    ]

    results = []
    for q in questions:
        t0 = time.time()
        answer = orch.ask(q)
        elapsed_ms = (time.time() - t0) * 1000

        results.append({
            "question": q,
            "hit_lock": answer["hit_lock"],
            "hit_mlock": answer["hit_mlock"],
            "bypass_llm": answer["bypass_llm"],
            "locked_answer": answer.get("locked_answer"),
            "semantic_matches": answer.get("semantic_matches", 0),
            "context_count": answer.get("context_count", 0),
            "elapsed_ms": round(elapsed_ms, 1),
        })

    return results


async def main() -> None:
    from autono.agents.chain_specialists.cross_chain_orchestrator import CrossChainOrchestrator

    banner("AUTONO KNOWLEDGE SYSTEM BOOTSTRAP")
    print("Initializing the Links & Locks brain...")

    persist = "--persist" in sys.argv
    do_scrape = "--scrape" in sys.argv

    if persist:
        knowledge_path = None
        print("  Mode: PERSISTENT (data saved to ~/.autono/knowledge)")
    else:
        _tmpdir = tempfile.mkdtemp(prefix="autono_knowledge_")
        knowledge_path = _tmpdir
        print(f"  Mode: TEMP (data in {_tmpdir})")

    # Step 1: Create orchestrator
    section("Step 1: Initializing CrossChainOrchestrator")
    t0 = time.time()
    orch = CrossChainOrchestrator(knowledge_path=knowledge_path)
    print(f"  Initialized in {(time.time() - t0) * 1000:.0f}ms")
    print(f"  Managers: {list(orch.managers.keys())}")
    print(f"  Chain Agents: {list(orch.chain_agents.keys())}")

    # Step 2: Seed protocol facts
    section("Step 2: Seeding Protocol Facts")
    t0 = time.time()
    count = await seed_protocol_facts(orch)
    print(f"  Seeded {count} facts with Locks in {(time.time() - t0) * 1000:.0f}ms")

    # Step 3: Live research scraping (optional)
    scrape_results = {}
    if do_scrape:
        section("Step 3: Live Research Scraping")
        print("  Scraping all domain sources with expert profiles...")
        print("  (This hits live websites — may take 30-60s)\n")
        t0 = time.time()
        scrape_results = run_live_scraping(orch)
        elapsed = time.time() - t0

        total_pages = sum(r.get("pages_scraped", 0) for r in scrape_results.values())
        total_facts = sum(r.get("facts_extracted", 0) for r in scrape_results.values())

        for domain, result in scrape_results.items():
            print(f"  {domain}:")
            print(f"    Sources: {result.get('sources', 0)}")
            print(f"    Pages:   {result.get('pages_scraped', 0)}")
            print(f"    Facts:   {result.get('facts_extracted', 0)}")

        print(f"\n  Total: {total_pages} pages, {total_facts} facts in {elapsed:.1f}s")

        # Re-embed after scraping (ExpansionManager creates new nodes)
        research_files = orch.store.list_research_files()
        print(f"  Research files created: {len(research_files)}")
    else:
        section("Step 3: Research Scraping (skipped)")
        print("  Use --scrape to enable live web scraping")

    # Step 3.5: WALI Wallet Creation
    section("Step 3.5: WALI Wallet Demo")
    print("  Creating multi-chain wallet (Cardano + Bitcoin + Night Chain)...")
    t0 = time.time()
    wallet_result = orch.wallet.create_wallet(
        chains=["cardano", "bitcoin", "night_chain"]
    )
    elapsed_ms = (time.time() - t0) * 1000

    print(f"  Wallet created in {elapsed_ms:.0f}ms")
    print(f"  Wallet ID: {wallet_result['wallet_id']}")
    for chain, addr in wallet_result["addresses"].items():
        print(f"  {chain}: {addr}")
    for chain, path in wallet_result["derivation_paths"].items():
        print(f"  {chain} path: {path}")

    # Validate the generated addresses
    print("\n  Address validation:")
    for chain, addr in wallet_result["addresses"].items():
        validation = orch.wallet.validate_address(addr, chain)
        status = "VALID" if validation.get("valid") else "INVALID"
        addr_type = validation.get("type", "?")
        print(f"    {chain} [{status}] type={addr_type}")

    # Auto-detect addresses
    print("\n  Auto-detection:")
    for chain, addr in wallet_result["addresses"].items():
        detected = orch.wallet.identify_address(addr)
        print(f"    {addr[:20]}... → {detected.get('chain', '?')} ({detected.get('type', '?')})")

    # Generate all Bitcoin address types
    import hashlib as hl
    seed = hl.pbkdf2_hmac("sha512", b"test_mnemonic", b"mnemonic", 2048, dklen=64)
    all_btc_types = orch.wallet.generate_all_bitcoin_types(seed)
    print("\n  All Bitcoin address types from same key:")
    for addr_type, wallet_addr in all_btc_types.items():
        print(f"    {addr_type}: {wallet_addr.address[:30]}... ({wallet_addr.derivation_path})")

    # Fee estimates
    print("\n  Fee estimates:")
    for chain in ["cardano", "bitcoin"]:
        fee = orch.wallet.estimate_fees(chain)
        print(f"    {chain}: slow={fee.slow} med={fee.medium} fast={fee.fast} {fee.unit}")

    print(f"\n  Wallet service: {orch.wallet.stats()}")

    # Step 4: Generate embeddings
    section("Step 4: Generating Embeddings")
    print("  Loading embedding model (first run downloads ~80MB)...")
    t0 = time.time()
    embedded = orch.graph.embed_all_nodes()
    elapsed = time.time() - t0
    if elapsed > 0:
        print(f"  Embedded {embedded} nodes in {elapsed:.1f}s "
              f"({embedded / elapsed:.0f} nodes/sec)")

    # Step 5: Knowledge stats
    section("Step 5: Knowledge Graph Status")
    stats = orch.knowledge_stats()
    show("Store", stats["store"])
    show("Graph", {k: v for k, v in stats["graph"].items() if k != "embeddings"})
    show("Embeddings", stats["graph"]["embeddings"])

    # Step 6: Semantic queries
    section("Step 6: Semantic Query Tests")
    print("  Running 10 natural language queries...\n")

    query_results = run_semantic_queries(orch)
    lock_hits = 0
    total_time = 0

    for qr in query_results:
        if qr["bypass_llm"]:
            status = "LOCK HIT — bypass LLM"
            lock_hits += 1
        elif qr["context_count"] > 0:
            status = f"CONTEXT ({qr['context_count']} nodes gathered)"
        else:
            status = "NO MATCH"

        total_time += qr["elapsed_ms"]

        print(f"  Q: {qr['question']}")
        print(f"     [{status}] {qr['elapsed_ms']:.1f}ms"
              f" | matches: {qr['semantic_matches']}")
        if qr["locked_answer"]:
            answer_str = str(qr["locked_answer"])
            if len(answer_str) > 80:
                answer_str = answer_str[:77] + "..."
            print(f"     ANSWER: {answer_str}")
        print()

    # Step 7: Results Summary
    section("Step 7: Results Summary")
    print(f"  Total queries:  {len(query_results)}")
    print(f"  Lock hits:      {lock_hits}/{len(query_results)} "
          f"({lock_hits / len(query_results) * 100:.0f}% zero-inference)")
    print(f"  Avg query time: {total_time / len(query_results):.1f}ms")
    print(f"  Total time:     {total_time:.0f}ms")

    # Step 8: Bridge routes
    section("Step 8: Cross-Chain Bridge Routes")
    for from_c, to_c in [("cardano", "bitcoin"), ("bitcoin", "cardano")]:
        route = orch.get_bridge_route(from_c, to_c)
        print(f"\n  {from_c} -> {to_c}:")
        print(f"    Method: {route.get('method', 'N/A')}")
        for i, step in enumerate(route.get("steps", []), 1):
            print(f"    {i}. {step}")
        print(f"    Time: {route.get('estimated_time', 'N/A')}")

    # Step 9: Backward chaining
    section("Step 9: Backward Chaining Demo")
    print("  Query: 'I need 100000000 — what is that?'")
    back_result = orch.backward_chain(100_000_000)
    show("Result", back_result)

    # Step 10: Research Manager report (if scraping was done)
    if do_scrape:
        section("Step 10: Research Manager Report")
        rm_report = orch.managers["ResearchManager"].report()
        show("Scraper Stats", {
            "pages_scraped": rm_report.get("pages_scraped", 0),
            "facts_extracted": rm_report.get("facts_extracted", 0),
            "completed_research": rm_report.get("completed_research", 0),
            "scrape_errors": rm_report.get("scrape_errors", 0),
        })

    banner("BOOTSTRAP COMPLETE")
    wallet_stats = orch.wallet.stats()
    print(f"\n  {count} protocol facts seeded")
    print(f"  {embedded} embeddings generated")
    print(f"  {wallet_stats['wallets_created']} wallet(s) created ({', '.join(wallet_stats['supported_chains'])})")
    print(f"  {lock_hits}/{len(query_results)} queries answered WITHOUT inference")
    if do_scrape:
        total_pages = sum(r.get("pages_scraped", 0) for r in scrape_results.values())
        total_facts = sum(r.get("facts_extracted", 0) for r in scrape_results.values())
        print(f"  {total_pages} pages scraped, {total_facts} live facts extracted")
    print(f"  System is ALIVE.\n")


if __name__ == "__main__":
    asyncio.run(main())
