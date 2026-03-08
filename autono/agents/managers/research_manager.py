"""ResearchManager — scrapes new data and creates .md files.

Research managers are REQUIRED to always create .md files for new
information not in embeds. The ExpansionManager watches for these
file creations and updates embeds automatically.

When things get busy, ResearchManager can spawn sub-agents to handle
parallel research tasks — always asking ThrottleManager first.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message


class ResearchManager(AutonomousAgent):
    """Knowledge researcher and documenter.

    Scrapes web sources, blockchain docs, protocol specs, and creates
    structured .md files that the ExpansionManager ingests into the
    knowledge graph.

    Handles the "dead link" recovery: when ExpansionManager can't find
    a source, ResearchManager searches for replacements.
    """

    def __init__(self) -> None:
        super().__init__(
            name="ResearchManager",
            role="Knowledge researcher — scrapes data and creates .md reference files",
            capabilities=[AgentCapability.RESEARCH, AgentCapability.BUILD_PRODUCT],
        )
        self._store = None
        self._research_queue: list[dict[str, Any]] = []
        self._completed_research: int = 0
        self._replacement_requests: list[dict[str, Any]] = []

        # Known research sources by domain
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
        return 120.0  # research is slower, runs less often

    def set_store(self, store: Any) -> None:
        """Inject the knowledge store."""
        self._store = store

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
            })
            await self.send(msg.sender, "response", {
                "type": "research_queued",
                "topic": msg.payload.get("topic", ""),
                "queue_position": len(self._research_queue),
            })

        elif msg.kind == "request" and msg.payload.get("type") == "find_replacement":
            # ExpansionManager needs us to find a replacement for dead source
            self._replacement_requests.append({
                "domain": msg.payload.get("original_domain", ""),
                "subdomain": msg.payload.get("original_subdomain", ""),
                "content_hint": msg.payload.get("original_content_summary", ""),
                "tags": msg.payload.get("tags", []),
                "requester": msg.sender,
            })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "research_methodology",
            "topics": [
                "web_scraping_best_practices",
                "blockchain_documentation_indexing",
                "source_reliability_scoring",
                "url_backtracking_recovery",
            ],
        })

    # -- Research processing ----------------------------------------------

    async def _process_research_queue(self) -> None:
        """Process queued research tasks, creating .md files."""
        if not self._research_queue:
            return

        # Sort by priority
        self._research_queue.sort(key=lambda r: -r.get("priority", 1))

        task = self._research_queue.pop(0)
        topic = task.get("topic", "")
        domain = task.get("domain", "general")

        # Create research output as .md file
        md_content = self._create_research_file(task)
        filename = self._generate_filename(topic, domain)

        if self._store:
            self._store.save_research(filename, md_content)
            self._completed_research += 1

            # Notify ExpansionManager
            await self.send("ExpansionManager", "request", {
                "type": "ingest_research",
                "filename": filename,
            })

            self.log.info("research.file_created",
                          filename=filename, domain=domain, topic=topic)

    async def _handle_replacement_requests(self) -> None:
        """Find replacement sources for dead links.

        The topic didn't go away — the resource went away.
        Search from known sources in the domain for equivalent content.
        """
        if not self._replacement_requests:
            return

        request = self._replacement_requests.pop(0)
        domain = request.get("domain", "")
        content_hint = request.get("content_hint", "")

        # Queue a research task to find replacement
        self._research_queue.append({
            "topic": f"replacement:{content_hint[:100]}",
            "domain": domain,
            "subdomain": request.get("subdomain", ""),
            "requester": request.get("requester", ""),
            "priority": 2,  # higher priority than regular research
            "sources": self._sources.get(domain, []),
            "is_replacement": True,
        })

        self.log.info("research.replacement_queued",
                      domain=domain, hint=content_hint[:50])

    def _create_research_file(self, task: dict) -> str:
        """Create a structured .md research file.

        All research outputs follow a consistent format so the
        ExpansionManager can reliably parse them.
        """
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
            f"**Subdomain**: {subdomain}" if subdomain else "",
            f"**Researched**: {now}",
            f"**Type**: {'replacement' if is_replacement else 'original'}",
            "",
            "## Summary",
            "",
            f"Research on: {topic}",
            "",
            "## Sources",
            "",
        ]

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
            "*(To be populated by scraping agent)*",
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
        # Sanitize topic for filename
        clean = topic.lower()
        clean = clean.replace(":", "_").replace(" ", "_")
        clean = "".join(c for c in clean if c.isalnum() or c == "_")
        clean = clean[:60]  # limit length

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"{domain}_{clean}_{timestamp}.md"

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "completed_research": self._completed_research,
            "queue_size": len(self._research_queue),
            "replacement_requests": len(self._replacement_requests),
            "known_source_domains": list(self._sources.keys()),
        })
        return base
