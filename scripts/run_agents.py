#!/usr/bin/env python3
"""Run all agents — full autonomous loop with message bus.

Boots the entire system: knowledge layer, Blockfrost, all chain specialists,
all managers, message bus routing. Agents run their work/message/learn loops
autonomously until interrupted.

Usage:
    python scripts/run_agents.py              # run for 60s (default)
    python scripts/run_agents.py --duration 30  # run for 30s
    python scripts/run_agents.py --forever     # run until Ctrl+C
"""

import argparse
import asyncio
import os
import sys
import time

from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import structlog
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
)
log = structlog.get_logger()


async def run_system(duration: float | None = 60.0):
    """Boot and run the full agent system."""
    from autono.core.message_bus import MessageBus
    from autono.knowledge.store import KnowledgeStore
    from autono.knowledge.graph import KnowledgeGraph
    from autono.knowledge.expansion import KnowledgeExpansionEngine
    from autono.services.blockfrost import BlockfrostClient
    from autono.services.scraper import Scraper
    from autono.agents.chain_specialists import ALL_CHAIN_SPECIALISTS
    from autono.agents.managers import ALL_MANAGERS

    start = time.monotonic()

    # ── Knowledge layer ──────────────────────────────────────────────────
    print("Initializing knowledge layer...")
    store = KnowledgeStore()
    graph = KnowledgeGraph(store=store)

    # Seed brain
    scraper = Scraper()
    expansion = KnowledgeExpansionEngine(store=store, scraper=scraper, graph=graph)
    seed_result = expansion.seed_all_facts()
    print(f"Brain seeded: {seed_result['seeded']} facts, "
          f"{seed_result['skipped']} skipped, {seed_result['errors']} errors")

    # ── Blockfrost ───────────────────────────────────────────────────────
    bf = BlockfrostClient()
    if bf.is_configured:
        try:
            health = await bf.health()
            tip = await bf.tip()
            print(f"Blockfrost: {bf.network} | healthy={health.get('is_healthy')} | "
                  f"block={tip.get('block')} epoch={tip.get('epoch')}")
        except Exception as e:
            print(f"Blockfrost check failed: {e}")
    else:
        print("Blockfrost: not configured (no API key)")

    # ── Message bus ──────────────────────────────────────────────────────
    bus = MessageBus()

    # ── Boot managers ────────────────────────────────────────────────────
    managers = {}
    for mgr_cls in ALL_MANAGERS:
        mgr = mgr_cls()
        managers[mgr.name] = mgr
        bus.register(mgr)

    # Inject manager dependencies
    if "EmbedManager" in managers:
        managers["EmbedManager"].set_store(store)
        managers["EmbedManager"].set_graph(graph)
    if "ExpansionManager" in managers:
        managers["ExpansionManager"].set_dependencies(store, graph)
    if "ResearchManager" in managers:
        managers["ResearchManager"].set_store(store)
    if "LinkManager" in managers:
        managers["LinkManager"].set_dependencies(store, graph)
    if "LockManager" in managers:
        managers["LockManager"].set_dependencies(store, graph)

    print(f"Managers registered: {list(managers.keys())}")

    # ── Boot chain specialists ───────────────────────────────────────────
    agents = {}
    for agent_cls in ALL_CHAIN_SPECIALISTS:
        agent = agent_cls()
        agents[agent.name] = agent
        bus.register(agent)
        if hasattr(agent, "set_dependencies"):
            agent.set_dependencies(store, graph)

    print(f"Chain agents registered: {list(agents.keys())}")

    # ── Launch everything ────────────────────────────────────────────────
    all_entities = {**managers, **agents}
    total = len(all_entities)
    elapsed_boot = time.monotonic() - start

    print()
    print("=" * 70)
    print(f"  LAUNCHING {total} AGENTS  (boot: {elapsed_boot:.2f}s)")
    if duration:
        print(f"  Running for {duration}s — press Ctrl+C to stop early")
    else:
        print("  Running forever — press Ctrl+C to stop")
    print("=" * 70)
    print()

    # Create tasks
    tasks = []

    # Message bus (routes messages between agents)
    bus_task = asyncio.create_task(bus.start())
    tasks.append(bus_task)

    # All agent loops
    for entity in all_entities.values():
        tasks.append(asyncio.create_task(entity.start()))

    # Status reporter — prints system status every 15 seconds
    async def status_reporter():
        cycle = 0
        while True:
            await asyncio.sleep(15)
            cycle += 1
            elapsed = time.monotonic() - start
            print()
            print(f"--- STATUS REPORT #{cycle} ({elapsed:.0f}s elapsed) ---")

            # Message bus stats
            total_inbox = sum(a.inbox.qsize() for a in all_entities.values())
            total_outbox = sum(a.outbox.qsize() for a in all_entities.values())
            print(f"  Messages: inbox={total_inbox}, outbox={total_outbox}")

            # Agent statuses
            for name, entity in all_entities.items():
                status = entity.status.value
                inbox_sz = entity.inbox.qsize()
                learnings = len(entity.memory.learnings)
                extra = ""
                if name == "CardanoChainAgent":
                    extra = f" | chain_synced={getattr(entity, '_chain_synced', False)}"
                    if hasattr(entity, '_blockfrost'):
                        extra += f" | bf_calls={entity._blockfrost.stats()['total_calls']}"
                elif name == "SpellCasterAgent":
                    active = len(getattr(entity, '_active_spells', {}))
                    extra = f" | active_spells={active}"
                elif name == "RepoWatcherAgent":
                    checked = getattr(entity, '_repos_checked', 0)
                    extra = f" | repos_checked={checked}"

                print(f"  {name}: {status} | inbox={inbox_sz} | learnings={learnings}{extra}")

            # Knowledge stats
            stats = store.stats()
            print(f"  Knowledge: nodes={stats.get('total_nodes', 0)}, "
                  f"locks={stats.get('total_locks', 0)}, "
                  f"links={stats.get('total_links', 0)}")

            if bf.is_configured:
                bf_stats = bf.stats()
                print(f"  Blockfrost: calls={bf_stats['total_calls']}, "
                      f"errors={bf_stats['errors']}, "
                      f"remaining={bf_stats['requests_remaining']}")
            print()

    tasks.append(asyncio.create_task(status_reporter()))

    # Timeout or run forever
    try:
        if duration:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True),
                timeout=duration,
            )
        else:
            await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.TimeoutError:
        print(f"\n{'=' * 70}")
        print(f"  DURATION REACHED ({duration}s)")
        print(f"{'=' * 70}")
    except KeyboardInterrupt:
        print(f"\n{'=' * 70}")
        print("  INTERRUPTED BY USER")
        print(f"{'=' * 70}")
    finally:
        # Graceful shutdown
        print("\nShutting down agents...")
        await bus.stop()
        for entity in all_entities.values():
            await entity.stop()
        await bf.close()

        # Cancel remaining tasks
        for task in tasks:
            if not task.done():
                task.cancel()

        # Final report
        elapsed = time.monotonic() - start
        print()
        print("=" * 70)
        print("  FINAL STATUS REPORT")
        print("=" * 70)
        for name, entity in all_entities.items():
            report = entity.report()
            print(f"  {name}:")
            print(f"    status={report['status']}")
            print(f"    learnings={len(report.get('recent_learnings', []))}")
            if 'blockfrost' in report:
                print(f"    blockfrost={report['blockfrost']}")

        stats = store.stats()
        print(f"\n  Final knowledge: nodes={stats.get('total_nodes', 0)}, "
              f"locks={stats.get('total_locks', 0)}, "
              f"links={stats.get('total_links', 0)}")
        print(f"  Total runtime: {elapsed:.2f}s")
        print("=" * 70)


def main():
    parser = argparse.ArgumentParser(description="Run autono agent system")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="Run duration in seconds (default: 60)")
    parser.add_argument("--forever", action="store_true",
                        help="Run until Ctrl+C")
    args = parser.parse_args()

    duration = None if args.forever else args.duration
    asyncio.run(run_system(duration))


if __name__ == "__main__":
    main()
