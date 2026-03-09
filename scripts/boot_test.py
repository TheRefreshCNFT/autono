#!/usr/bin/env python3
"""Boot test — spin up the full system and verify everything connects.

Loads .env, initializes all agents, seeds the brain, queries Blockfrost,
and reports system status.

Usage:
    python scripts/boot_test.py
"""

import asyncio
import os
import sys
import time

# Load .env before any imports that read env vars
from dotenv import load_dotenv
load_dotenv()

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(colors=True),
    ],
)
log = structlog.get_logger()


async def main():
    start = time.monotonic()

    print("=" * 70)
    print("  AUTONO BOOT TEST")
    print("=" * 70)
    print()

    # ── Step 1: Check environment ────────────────────────────────────────
    print("[1/7] Checking environment...")
    api_key = os.environ.get("BLOCKFROST_API_KEY", "")
    if api_key:
        # Show only first 7 chars (network prefix) — never the full key
        print(f"  Blockfrost API key: {api_key[:7]}... (configured)")
    else:
        print("  WARNING: No BLOCKFROST_API_KEY set in .env")
    print()

    # ── Step 2: Initialize knowledge layer ───────────────────────────────
    print("[2/7] Initializing knowledge layer...")
    from autono.knowledge.store import KnowledgeStore
    from autono.knowledge.graph import KnowledgeGraph

    store = KnowledgeStore()
    graph = KnowledgeGraph(store=store)
    stats = store.stats()
    print(f"  Knowledge store: {stats}")
    print()

    # ── Step 3: Seed the brain ───────────────────────────────────────────
    print("[3/7] Seeding brain with protocol facts...")
    from autono.knowledge.expansion import KnowledgeExpansionEngine
    from autono.services.scraper import Scraper

    scraper = Scraper()
    expansion = KnowledgeExpansionEngine(
        store=store, scraper=scraper, graph=graph
    )
    seed_result = expansion.seed_all_facts()
    print(f"  Seeded: {seed_result}")
    print(f"  Store after seeding: {store.stats()}")
    print()

    # ── Step 4: Test Blockfrost connection ────────────────────────────────
    print("[4/7] Testing Blockfrost connection...")
    from autono.services.blockfrost import BlockfrostClient, BlockfrostError

    bf = BlockfrostClient()
    print(f"  Network: {bf.network}")
    print(f"  Configured: {bf.is_configured}")

    if bf.is_configured:
        try:
            health = await bf.health()
            print(f"  Health: {health}")

            tip = await bf.tip()
            print(f"  Chain tip: block {tip.get('block')}, "
                  f"slot {tip.get('slot')}, epoch {tip.get('epoch')}")

            params = await bf.protocol_params()
            if params:
                print(f"  Protocol params loaded: "
                      f"min_fee_a={params.get('min_fee_a')}, "
                      f"min_fee_b={params.get('min_fee_b')}, "
                      f"max_tx_size={params.get('max_tx_size')}")

            epoch = await bf.latest_epoch()
            if epoch:
                print(f"  Current epoch: {epoch.get('epoch')}, "
                      f"start: {epoch.get('start_time')}, "
                      f"end: {epoch.get('end_time')}")

        except BlockfrostError as e:
            print(f"  ERROR: {e}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")
    print()

    # ── Step 5: Boot agents ──────────────────────────────────────────────
    print("[5/7] Booting chain specialist agents...")
    from autono.core.message_bus import MessageBus
    from autono.agents.chain_specialists import ALL_CHAIN_SPECIALISTS

    bus = MessageBus()
    agents = {}
    for agent_cls in ALL_CHAIN_SPECIALISTS:
        agent = agent_cls()
        agents[agent.name] = agent
        bus.register(agent)
        print(f"  Registered: {agent.name} ({agent.role})")

    # Inject dependencies
    for agent in agents.values():
        if hasattr(agent, "set_dependencies"):
            agent.set_dependencies(store, graph)
    print()

    # ── Step 6: Boot managers ────────────────────────────────────────────
    print("[6/7] Booting managers...")
    from autono.agents.managers import ALL_MANAGERS

    managers = {}
    for mgr_cls in ALL_MANAGERS:
        mgr = mgr_cls()
        managers[mgr.name] = mgr
        bus.register(mgr)
        print(f"  Registered: {mgr.name}")
    print()

    # ── Step 7: System status report ─────────────────────────────────────
    elapsed = time.monotonic() - start
    print("[7/7] System status report")
    print("-" * 50)

    brain_status = expansion.get_brain_status()
    print(f"  Brain coverage: {brain_status.get('coverage_pct', 0):.1f}%")
    print(f"  Total facts seeded: {brain_status.get('total_facts', 0)}")
    print(f"  Nodes in store: {store.stats().get('total_nodes', 0)}")
    print(f"  Locks active: {store.stats().get('total_locks', 0)}")

    print(f"\n  Chain agents: {len(agents)}")
    for name, agent in agents.items():
        report = agent.report()
        print(f"    {name}: {report.get('status', 'ready')}")

    print(f"\n  Managers: {len(managers)}")
    for name, mgr in managers.items():
        print(f"    {name}: ready")

    if bf.is_configured:
        print(f"\n  Blockfrost: {bf.stats()}")

    print(f"\n  Boot time: {elapsed:.2f}s")
    print()
    print("=" * 70)
    print("  AUTONO SYSTEM READY")
    print("=" * 70)

    # Clean up
    await bf.close()


if __name__ == "__main__":
    asyncio.run(main())
