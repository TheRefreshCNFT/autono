"""Bootstrap — seeds the knowledge graph and proves the Links & Locks flow.

This script:
1. Creates the CrossChainOrchestrator (store + graph + all agents)
2. Seeds all protocol facts from chain specialist agents
3. Creates Locks for deterministic facts
4. Generates embeddings for all nodes
5. Runs semantic queries to prove the system works
6. Demonstrates lock hits (instant answers, zero inference)
7. Shows cross-chain bridge routing

Run: python -m autono.bootstrap
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

    # Step 3: Generate embeddings
    section("Step 3: Generating Embeddings")
    print("  Loading embedding model (first run downloads ~80MB)...")
    t0 = time.time()
    embedded = orch.graph.embed_all_nodes()
    elapsed = time.time() - t0
    if elapsed > 0:
        print(f"  Embedded {embedded} nodes in {elapsed:.1f}s "
              f"({embedded / elapsed:.0f} nodes/sec)")

    # Step 4: Knowledge stats
    section("Step 4: Knowledge Graph Status")
    stats = orch.knowledge_stats()
    show("Store", stats["store"])
    show("Graph", {k: v for k, v in stats["graph"].items() if k != "embeddings"})
    show("Embeddings", stats["graph"]["embeddings"])

    # Step 5: Semantic queries
    section("Step 5: Semantic Query Tests")
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

    # Step 6: Summary
    section("Step 6: Results Summary")
    print(f"  Total queries:  {len(query_results)}")
    print(f"  Lock hits:      {lock_hits}/{len(query_results)} "
          f"({lock_hits / len(query_results) * 100:.0f}% zero-inference)")
    print(f"  Avg query time: {total_time / len(query_results):.1f}ms")
    print(f"  Total time:     {total_time:.0f}ms")

    # Step 7: Bridge routes
    section("Step 7: Cross-Chain Bridge Routes")
    for from_c, to_c in [("cardano", "bitcoin"), ("bitcoin", "cardano")]:
        route = orch.get_bridge_route(from_c, to_c)
        print(f"\n  {from_c} -> {to_c}:")
        print(f"    Method: {route.get('method', 'N/A')}")
        for i, step in enumerate(route.get("steps", []), 1):
            print(f"    {i}. {step}")
        print(f"    Time: {route.get('estimated_time', 'N/A')}")

    # Step 8: Backward chaining
    section("Step 8: Backward Chaining Demo")
    print("  Query: 'I need 100000000 — what is that?'")
    back_result = orch.backward_chain(100_000_000)
    show("Result", back_result)

    banner("BOOTSTRAP COMPLETE")
    print(f"\n  {count} protocol facts seeded")
    print(f"  {embedded} embeddings generated")
    print(f"  {lock_hits}/{len(query_results)} queries answered WITHOUT inference")
    print(f"  System is ALIVE.\n")


if __name__ == "__main__":
    asyncio.run(main())
