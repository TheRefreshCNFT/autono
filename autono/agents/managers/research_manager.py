"""ResearchManager — god-level research scraping engine.

Each chain agent is a domain expert. ResearchManager is their research arm:
- Scrapes live web sources using domain-specific profiles
- Extracts structured facts from documentation
- Generates lockable knowledge for the Links & Locks system
- Creates .md research files that ExpansionManager ingests
- Handles dead link recovery by re-scraping from alternate sources

When things get busy, ResearchManager can spawn sub-agents to handle
parallel research tasks — always asking ThrottleManager first.

The pipeline:
1. Chain agent or scheduler requests research topic
2. ResearchManager loads the domain's research profile (expert sources)
3. Scraper crawls sources, extracts content and facts
4. Facts above confidence threshold get written as .md files
5. ExpansionManager watches → creates nodes → EmbedManager embeds
6. LockManager evaluates high-confidence facts → creates Locks
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

import structlog

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message

log = structlog.get_logger()


class ResearchManager(AutonomousAgent):
    """Knowledge researcher and scraper. The system's eyes on the web.

    Coordinates with chain agents via research profiles that define
    exactly where to look and what to extract for each domain.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ResearchManager",
            role="Knowledge researcher — scrapes live sources, extracts facts, creates .md files",
            capabilities=[AgentCapability.RESEARCH, AgentCapability.BUILD_PRODUCT],
        )
        self._store = None
        self._scraper = None  # lazy init
        self._research_queue: list[dict[str, Any]] = []
        self._completed_research: int = 0
        self._replacement_requests: list[dict[str, Any]] = []
        self._facts_extracted: int = 0
        self._pages_scraped: int = 0
        self._scrape_errors: int = 0

        # Track which domains have been initially scraped
        self._initial_scrape_done: set[str] = set()

        # Known research sources by domain (legacy fallback)
        self._sources: dict[str, list[str]] = {
            "cardano": [
                "https://docs.cardano.org",
                "https://cips.cardano.org",
                "https://developers.cardano.org",
            ],
            "bitcoin": [
                "https://developer.bitcoin.org",
                "https://github.com/bitcoin/bips",
            ],
            "charms": [
                "https://docs.charms.dev",
                "https://charms.dev",
            ],
            "bitcoinos": [
                "https://docs.bitcoinos.build",
                "https://bitcoinos.build",
            ],
        }

    @property
    def work_interval(self) -> float:
        return 120.0  # research cycle every 2 minutes

    def set_store(self, store: Any) -> None:
        """Inject the knowledge store."""
        self._store = store

    def _ensure_scraper(self) -> Any:
        """Lazy-init the scraper engine."""
        if self._scraper is None:
            from autono.services.scraper import Scraper
            self._scraper = Scraper(rate_limit=1.0)
        return self._scraper

    async def do_work(self) -> None:
        """Process research queue and handle replacement requests."""
        if not self._store:
            return

        # Process replacement requests from ExpansionManager
        await self._handle_replacement_requests()

        # Process queued research tasks
        await self._process_research_queue()

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request" and msg.payload.get("type") == "research_topic":
            self._research_queue.append({
                "topic": msg.payload.get("topic", ""),
                "domain": msg.payload.get("domain", ""),
                "subdomain": msg.payload.get("subdomain", ""),
                "requester": msg.sender,
                "priority": msg.payload.get("priority", 1),
                "sources": msg.payload.get("sources", []),
                "url": msg.payload.get("url", ""),
            })
            await self.send(msg.sender, "response", {
                "type": "research_queued",
                "topic": msg.payload.get("topic", ""),
                "queue_position": len(self._research_queue),
            })

        elif msg.kind == "request" and msg.payload.get("type") == "find_replacement":
            self._replacement_requests.append({
                "domain": msg.payload.get("original_domain", ""),
                "subdomain": msg.payload.get("original_subdomain", ""),
                "content_hint": msg.payload.get("original_content_summary", ""),
                "tags": msg.payload.get("tags", []),
                "requester": msg.sender,
            })

        elif msg.kind == "request" and msg.payload.get("type") == "scrape_domain":
            # Full domain scrape request — scrape all sources for a domain
            domain = msg.payload.get("domain", "")
            if domain:
                await self._scrape_domain(domain)
                await self.send(msg.sender, "response", {
                    "type": "domain_scraped",
                    "domain": domain,
                })

        elif msg.kind == "request" and msg.payload.get("type") == "scrape_url":
            # Single URL scrape request
            url = msg.payload.get("url", "")
            domain = msg.payload.get("domain", "general")
            subdomain = msg.payload.get("subdomain", "")
            if url:
                result = await self._scrape_single_url(url, domain, subdomain)
                await self.send(msg.sender, "response", {
                    "type": "url_scraped",
                    "url": url,
                    **result,
                })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "research_methodology",
            "topics": [
                "web_scraping_best_practices",
                "blockchain_documentation_indexing",
                "source_reliability_scoring",
                "fact_extraction_nlp",
                "content_change_detection",
            ],
        })

    # -- Core scraping operations -------------------------------------------

    async def _scrape_domain(self, domain: str) -> dict[str, Any]:
        """Scrape all sources for a domain using its research profile."""
        from autono.agents.chain_specialists.research_profiles import get_sources_for_domain

        sources = get_sources_for_domain(domain)
        if not sources:
            log.warning("research.no_profile", domain=domain)
            return {"error": f"No research profile for domain: {domain}"}

        scraper = self._ensure_scraper()
        total_pages = 0
        total_facts = 0

        for source in sources:
            try:
                pages = scraper.crawl_source(source, max_pages=10)
                total_pages += len(pages)

                if pages:
                    # Generate research .md file
                    md_content = scraper.pages_to_research_md(pages, source)
                    filename = self._generate_filename(
                        f"{source.subdomain or 'general'}",
                        source.domain,
                    )

                    if self._store:
                        self._store.save_research(filename, md_content)
                        self._completed_research += 1

                    # Count facts
                    for page in pages:
                        total_facts += len(page.extracted_facts)
                        self._pages_scraped += 1

                    # Notify ExpansionManager
                    await self.send("ExpansionManager", "request", {
                        "type": "ingest_research",
                        "filename": filename,
                    })

                    log.info("research.source_scraped",
                             source=source.url[:60],
                             pages=len(pages),
                             facts=sum(len(p.extracted_facts) for p in pages))

            except Exception as e:
                self._scrape_errors += 1
                log.warning("research.scrape_error",
                            source=source.url[:60], error=str(e))

        self._facts_extracted += total_facts
        self._initial_scrape_done.add(domain)

        log.info("research.domain_complete",
                 domain=domain, pages=total_pages, facts=total_facts)

        return {
            "domain": domain,
            "sources_scraped": len(sources),
            "pages": total_pages,
            "facts": total_facts,
        }

    async def _scrape_single_url(self, url: str, domain: str,
                                  subdomain: str) -> dict[str, Any]:
        """Scrape a single URL and extract facts."""
        scraper = self._ensure_scraper()

        page = scraper.fetch(url)
        if not page.ok:
            self._scrape_errors += 1
            return {"ok": False, "error": page.error}

        self._pages_scraped += 1

        # Extract facts
        from autono.agents.chain_specialists.research_profiles import get_sources_for_domain
        sources = get_sources_for_domain(domain)

        # Find matching source profile for patterns
        patterns = []
        for source in sources:
            if source.extract_patterns:
                patterns.extend(source.extract_patterns)

        facts = scraper.extract_facts(
            page, patterns=patterns, domain=domain, subdomain=subdomain
        )
        self._facts_extracted += len(facts)

        # Create research file
        from autono.services.scraper import ResearchSource
        source = ResearchSource(
            url=url, domain=domain, subdomain=subdomain,
            source_type="docs", tags=[domain],
        )
        md_content = scraper.pages_to_research_md([page], source)
        filename = self._generate_filename(
            subdomain or "scraped",
            domain,
        )

        if self._store:
            self._store.save_research(filename, md_content)
            self._completed_research += 1

            await self.send("ExpansionManager", "request", {
                "type": "ingest_research",
                "filename": filename,
            })

        return {
            "ok": True,
            "facts_extracted": len(facts),
            "content_length": len(page.markdown),
            "title": page.title,
        }

    # -- Research queue processing -------------------------------------------

    async def _process_research_queue(self) -> None:
        """Process queued research tasks with real scraping."""
        if not self._research_queue:
            return

        # Sort by priority
        self._research_queue.sort(key=lambda r: -r.get("priority", 1))

        task = self._research_queue.pop(0)
        topic = task.get("topic", "")
        domain = task.get("domain", "general")
        subdomain = task.get("subdomain", "")
        url = task.get("url", "")

        if url:
            # Direct URL scrape
            await self._scrape_single_url(url, domain, subdomain)
        elif domain and domain in self._sources:
            # Domain scrape
            await self._scrape_domain(domain)
        else:
            # Fallback: create research file from known info
            md_content = self._create_research_file(task)
            filename = self._generate_filename(topic, domain)

            if self._store:
                self._store.save_research(filename, md_content)
                self._completed_research += 1

                await self.send("ExpansionManager", "request", {
                    "type": "ingest_research",
                    "filename": filename,
                })

                log.info("research.file_created",
                         filename=filename, domain=domain, topic=topic)

    async def _handle_replacement_requests(self) -> None:
        """Find replacement sources for dead links.

        The topic didn't go away — the resource went away.
        Re-scrape from the domain's research profile to find current data.
        """
        if not self._replacement_requests:
            return

        request = self._replacement_requests.pop(0)
        domain = request.get("domain", "")

        if domain:
            # Re-scrape the domain to find replacement content
            await self._scrape_domain(domain)
        else:
            # Fallback: queue a research task
            self._research_queue.append({
                "topic": f"replacement:{request.get('content_hint', '')[:100]}",
                "domain": domain,
                "subdomain": request.get("subdomain", ""),
                "requester": request.get("requester", ""),
                "priority": 2,
                "sources": self._sources.get(domain, []),
                "is_replacement": True,
            })

        log.info("research.replacement_handled",
                 domain=domain, hint=request.get("content_hint", "")[:50])

    # -- Batch scraping (for bootstrap) -------------------------------------

    def scrape_all_domains(self) -> dict[str, Any]:
        """Scrape all domains synchronously. Used during bootstrap.

        Returns summary of all scraping results.
        """
        from autono.agents.chain_specialists.research_profiles import DOMAIN_SOURCES

        scraper = self._ensure_scraper()
        results = {}

        for domain, sources in DOMAIN_SOURCES.items():
            domain_pages = 0
            domain_facts = 0

            for source in sources:
                try:
                    pages = scraper.crawl_source(source, max_pages=5)
                    domain_pages += len(pages)

                    if pages:
                        md_content = scraper.pages_to_research_md(pages, source)
                        filename = self._generate_filename(
                            source.subdomain or "general",
                            source.domain,
                        )

                        if self._store:
                            self._store.save_research(filename, md_content)
                            self._completed_research += 1

                        for page in pages:
                            domain_facts += len(page.extracted_facts)
                            self._pages_scraped += 1

                except Exception as e:
                    self._scrape_errors += 1
                    log.warning("research.batch_error",
                                source=source.url[:60], error=str(e))

            self._facts_extracted += domain_facts
            results[domain] = {
                "pages_scraped": domain_pages,
                "facts_extracted": domain_facts,
                "sources": len(sources),
            }

            log.info("research.batch_domain_done",
                     domain=domain, pages=domain_pages, facts=domain_facts)

        return results

    # -- File generation helpers --------------------------------------------

    def _create_research_file(self, task: dict) -> str:
        """Create a structured .md research file (fallback when no scraping)."""
        topic = task.get("topic", "Unknown Topic")
        domain = task.get("domain", "general")
        subdomain = task.get("subdomain", "")
        sources = task.get("sources", [])
        is_replacement = task.get("is_replacement", False)

        now = datetime.now(timezone.utc).isoformat()

        lines = [
            f"# {topic}",
            "",
            f"**Domain**: {domain}",
        ]
        if subdomain:
            lines.append(f"**Subdomain**: {subdomain}")
        lines.extend([
            f"**Researched**: {now}",
            f"**Type**: {'replacement' if is_replacement else 'original'}",
            "",
            "## Summary",
            "",
            f"Research on: {topic}",
            "",
            "## Sources",
            "",
        ])

        for source in sources:
            lines.append(f"- {source}")

        if not sources:
            domain_sources = self._sources.get(domain, [])
            for source in domain_sources:
                lines.append(f"- {source}")

        lines.extend([
            "",
            "## Key Findings",
            "",
            "*(Pending live scraping)*",
            "",
            "## Related Topics",
            "",
            f"- {domain}",
        ])

        if subdomain:
            lines.append(f"- {subdomain}")

        for tag in task.get("tags", []):
            lines.append(f"- {tag}")

        return "\n".join(lines)

    def _generate_filename(self, topic: str, domain: str) -> str:
        """Generate a clean filename for research output."""
        clean = topic.lower()
        clean = clean.replace(":", "_").replace(" ", "_")
        clean = "".join(c for c in clean if c.isalnum() or c == "_")
        clean = clean[:60]

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        return f"{domain}_{clean}_{timestamp}.md"

    def report(self) -> dict[str, Any]:
        base = super().report()
        scraper_stats = self._scraper.stats() if self._scraper else {}
        base.update({
            "completed_research": self._completed_research,
            "queue_size": len(self._research_queue),
            "replacement_requests": len(self._replacement_requests),
            "facts_extracted": self._facts_extracted,
            "pages_scraped": self._pages_scraped,
            "scrape_errors": self._scrape_errors,
            "initial_scrape_done": list(self._initial_scrape_done),
            "scraper": scraper_stats,
        })
        return base
