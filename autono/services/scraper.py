"""Scraper — god-level web scraping engine for chain specialist agents.

Each chain agent is a domain expert. This engine gives them the tools to
scrape their sources with surgical precision:

- Async HTTP with retries, rate limiting, exponential backoff
- HTML → clean markdown conversion (preserves code blocks, tables, links)
- GitHub raw content fetching (READMEs, docs, source files)
- JSON API endpoint scraping with schema extraction
- Content hashing for change detection
- Structured fact extraction from scraped content
- Domain-specific CSS selector support

The scraper respects robots.txt spirit: reasonable rate limits, identifies
itself honestly, and caches aggressively to minimize requests.
"""

from __future__ import annotations

import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
import structlog

log = structlog.get_logger()

# Reasonable defaults
DEFAULT_TIMEOUT = 30.0
DEFAULT_RATE_LIMIT = 1.0  # seconds between requests to same domain
MAX_RETRIES = 3
MAX_CONTENT_SIZE = 5 * 1024 * 1024  # 5MB max per page

USER_AGENT = (
    "Autono/1.0 (Knowledge Graph Research Agent; "
    "+https://github.com/TheRefreshCNFT/autono)"
)


@dataclass
class ScrapedPage:
    """Result of scraping a single URL."""
    url: str
    status_code: int
    content_type: str
    raw_html: str
    markdown: str
    title: str
    content_hash: str
    scraped_at: float
    extracted_facts: list[dict[str, Any]] = field(default_factory=list)
    extracted_code_blocks: list[dict[str, str]] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status_code < 400


@dataclass
class ResearchSource:
    """A research source definition — what to scrape and how."""
    url: str
    domain: str
    subdomain: str = ""
    source_type: str = "docs"  # docs, github, api, spec, blog
    selectors: dict[str, str] = field(default_factory=dict)
    # CSS selectors for targeted extraction:
    #   "content": "main article"  — main content area
    #   "code": "pre code"         — code blocks
    #   "nav_links": "nav a"       — navigation links to follow
    #   "remove": ".sidebar, .footer"  — elements to strip
    extract_patterns: list[dict[str, str]] = field(default_factory=list)
    # Regex patterns for fact extraction:
    #   {"name": "version", "pattern": r"v(\d+\.\d+\.\d+)", "type": "string"}
    tags: list[str] = field(default_factory=list)
    priority: int = 1  # 1=high, 2=medium, 3=low
    max_depth: int = 2  # how many link levels to follow
    follow_links: bool = True


class Scraper:
    """Core scraping engine. Async HTTP + HTML parsing + fact extraction.

    Usage:
        scraper = Scraper()
        page = await scraper.fetch("https://docs.cardano.org/some-page")
        facts = scraper.extract_facts(page, patterns=[...])
    """

    def __init__(self, rate_limit: float = DEFAULT_RATE_LIMIT) -> None:
        self._rate_limit = rate_limit
        self._last_request: dict[str, float] = {}  # domain -> timestamp
        self._client: httpx.Client | None = None
        self._cache: dict[str, ScrapedPage] = {}  # url -> result
        self._request_count: int = 0
        self._error_count: int = 0

    def _ensure_client(self) -> httpx.Client:
        if self._client is None:
            self._client = httpx.Client(
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                },
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                ),
            )
        return self._client

    def _rate_limit_wait(self, domain: str) -> None:
        """Respect rate limits per domain."""
        last = self._last_request.get(domain, 0)
        elapsed = time.time() - last
        if elapsed < self._rate_limit:
            time.sleep(self._rate_limit - elapsed)
        self._last_request[domain] = time.time()

    # -- Core fetch -----------------------------------------------------------

    def fetch(self, url: str, use_cache: bool = True) -> ScrapedPage:
        """Fetch and parse a URL. Returns ScrapedPage with markdown content."""
        # Check cache
        if use_cache and url in self._cache:
            cached = self._cache[url]
            # Cache valid for 1 hour
            if time.time() - cached.scraped_at < 3600:
                return cached

        domain = urlparse(url).netloc
        self._rate_limit_wait(domain)

        client = self._ensure_client()
        page = ScrapedPage(
            url=url, status_code=0, content_type="",
            raw_html="", markdown="", title="",
            content_hash="", scraped_at=time.time(),
        )

        for attempt in range(MAX_RETRIES):
            try:
                resp = client.get(url)
                self._request_count += 1

                page.status_code = resp.status_code
                page.content_type = resp.headers.get("content-type", "")

                if resp.status_code >= 400:
                    page.error = f"HTTP {resp.status_code}"
                    if attempt < MAX_RETRIES - 1:
                        time.sleep(2 ** attempt)
                        continue
                    break

                raw = resp.text
                if len(raw) > MAX_CONTENT_SIZE:
                    raw = raw[:MAX_CONTENT_SIZE]

                page.raw_html = raw
                page.content_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]

                # Parse based on content type
                if "json" in page.content_type:
                    page.markdown = self._json_to_markdown(raw, url)
                    page.title = urlparse(url).path.split("/")[-1]
                else:
                    page.markdown, page.title, page.links = self._html_to_markdown(
                        raw, url
                    )
                    page.extracted_code_blocks = self._extract_code_blocks(raw)

                # Cache it
                self._cache[url] = page

                log.info("scraper.fetch_ok", url=url[:80],
                         size=len(raw), title=page.title[:60])
                return page

            except httpx.TimeoutException:
                page.error = "timeout"
                self._error_count += 1
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except httpx.ConnectError as e:
                page.error = f"connection_error: {e}"
                self._error_count += 1
                if attempt < MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
            except Exception as e:
                page.error = f"error: {type(e).__name__}: {e}"
                self._error_count += 1
                log.warning("scraper.fetch_error", url=url[:80], error=str(e))
                break

        return page

    def fetch_github_raw(self, owner: str, repo: str, path: str,
                         branch: str = "main") -> ScrapedPage:
        """Fetch raw content from GitHub (READMEs, docs, source files)."""
        url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
        page = self.fetch(url)

        # GitHub raw files are plain text, not HTML
        if page.ok and not page.markdown:
            page.markdown = page.raw_html  # already plain text/markdown
            page.title = path.split("/")[-1]

        return page

    def fetch_github_api(self, endpoint: str) -> ScrapedPage:
        """Fetch from GitHub API (repo info, releases, etc)."""
        url = f"https://api.github.com/{endpoint.lstrip('/')}"
        domain = "api.github.com"
        self._rate_limit_wait(domain)

        client = self._ensure_client()
        page = ScrapedPage(
            url=url, status_code=0, content_type="application/json",
            raw_html="", markdown="", title=endpoint,
            content_hash="", scraped_at=time.time(),
        )

        try:
            resp = client.get(url, headers={
                "Accept": "application/vnd.github.v3+json",
            })
            self._request_count += 1
            page.status_code = resp.status_code

            if resp.status_code == 200:
                raw = resp.text
                page.raw_html = raw
                page.content_hash = hashlib.sha256(raw.encode()).hexdigest()[:16]
                page.markdown = self._json_to_markdown(raw, url)
            else:
                page.error = f"GitHub API {resp.status_code}"
        except Exception as e:
            page.error = str(e)
            self._error_count += 1

        return page

    # -- HTML → Markdown conversion ------------------------------------------

    def _html_to_markdown(self, html: str, base_url: str
                          ) -> tuple[str, str, list[str]]:
        """Convert HTML to clean markdown. Returns (markdown, title, links)."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")

        # Extract title
        title = ""
        title_tag = soup.find("title")
        if title_tag:
            title = title_tag.get_text(strip=True)

        # Remove noise elements
        for tag in soup.find_all(["script", "style", "nav", "footer",
                                   "header", "iframe", "noscript"]):
            tag.decompose()

        # Extract links before converting
        links = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith(("http://", "https://")):
                links.append(href)
            elif href.startswith("/"):
                links.append(urljoin(base_url, href))

        # Find main content area (try common selectors)
        content_area = (
            soup.find("main")
            or soup.find("article")
            or soup.find(class_=re.compile(r"content|main|docs|article"))
            or soup.find(id=re.compile(r"content|main|docs|article"))
            or soup.body
            or soup
        )

        # Convert to markdown
        import html2text
        h = html2text.HTML2Text()
        h.ignore_links = False
        h.ignore_images = True
        h.ignore_emphasis = False
        h.body_width = 0  # don't wrap lines
        h.unicode_snob = True
        h.skip_internal_links = True

        markdown = h.handle(str(content_area))

        # Clean up excessive whitespace
        markdown = re.sub(r"\n{4,}", "\n\n\n", markdown)
        markdown = markdown.strip()

        return markdown, title, links

    def _json_to_markdown(self, raw_json: str, url: str) -> str:
        """Convert JSON API response to readable markdown."""
        import json

        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            return f"```json\n{raw_json[:2000]}\n```"

        lines = [f"# API Response: {urlparse(url).path}\n"]

        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, (dict, list)):
                    import json as j
                    lines.append(f"## {key}\n```json\n{j.dumps(value, indent=2)[:1000]}\n```\n")
                else:
                    lines.append(f"- **{key}**: {value}")
        elif isinstance(data, list):
            lines.append(f"*{len(data)} items*\n")
            for item in data[:20]:  # limit preview
                if isinstance(item, dict):
                    summary = ", ".join(f"{k}={v}" for k, v in list(item.items())[:5])
                    lines.append(f"- {summary}")
                else:
                    lines.append(f"- {item}")

        return "\n".join(lines)

    def _extract_code_blocks(self, html: str) -> list[dict[str, str]]:
        """Extract code blocks with their language annotations."""
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        blocks = []

        for pre in soup.find_all("pre"):
            code = pre.find("code")
            if code:
                lang = ""
                classes = code.get("class", [])
                for cls in classes:
                    if cls.startswith(("language-", "lang-", "highlight-")):
                        lang = cls.split("-", 1)[1]
                        break

                text = code.get_text()
                if len(text.strip()) > 10:  # skip tiny snippets
                    blocks.append({"language": lang, "code": text.strip()})

        return blocks

    # -- Targeted extraction with selectors ----------------------------------

    def extract_with_selectors(self, page: ScrapedPage,
                                selectors: dict[str, str]) -> dict[str, str]:
        """Extract specific content using CSS selectors.

        Example selectors:
            {"content": "article.docs-content",
             "sidebar": "nav.sidebar",
             "version": ".version-badge"}
        """
        from bs4 import BeautifulSoup

        if not page.raw_html:
            return {}

        soup = BeautifulSoup(page.raw_html, "lxml")
        results = {}

        for name, selector in selectors.items():
            if name == "remove":
                continue  # handled separately
            elements = soup.select(selector)
            if elements:
                import html2text
                h = html2text.HTML2Text()
                h.body_width = 0
                h.ignore_images = True
                texts = [h.handle(str(el)).strip() for el in elements]
                results[name] = "\n\n".join(texts)

        return results

    # -- Fact extraction -----------------------------------------------------

    def extract_facts(self, page: ScrapedPage,
                      patterns: list[dict[str, str]] | None = None,
                      domain: str = "",
                      subdomain: str = "") -> list[dict[str, Any]]:
        """Extract structured facts from scraped content.

        Uses regex patterns and heuristics to find lockable facts:
        - Version numbers
        - Protocol parameters (numeric values with names)
        - API endpoints
        - Code signatures
        - Constants and configurations
        """
        if not page.ok or not page.markdown:
            return []

        facts = []
        content = page.markdown

        # Apply custom patterns first
        if patterns:
            for pat in patterns:
                regex = pat.get("pattern", "")
                if not regex:
                    continue
                matches = re.finditer(regex, content)
                for m in matches:
                    fact = {
                        "fact": m.group(0)[:200],
                        "answer": m.group(1) if m.lastindex else m.group(0),
                        "answer_type": pat.get("type", "string"),
                        "domain": domain,
                        "subdomain": subdomain,
                        "source": page.url,
                        "tags": pat.get("tags", []),
                        "confidence": 0.8,
                    }
                    facts.append(fact)

        # Auto-extract common patterns
        facts.extend(self._auto_extract_facts(content, page.url, domain, subdomain))

        # Deduplicate by answer
        seen = set()
        unique_facts = []
        for f in facts:
            key = f"{f['domain']}:{f.get('answer', '')}"
            if key not in seen:
                seen.add(key)
                unique_facts.append(f)

        page.extracted_facts = unique_facts
        return unique_facts

    def _auto_extract_facts(self, content: str, source_url: str,
                             domain: str, subdomain: str) -> list[dict[str, Any]]:
        """Heuristic fact extraction from markdown content."""
        facts = []

        # Pattern: "X is Y" or "X = Y" statements
        for m in re.finditer(
            r"(?:^|\n)\s*[-*]?\s*\*?\*?([A-Z][^:.\n]{5,60})\*?\*?\s*(?:is|=|:)\s*"
            r"[`\"]?([^`\"\n]{2,100})[`\"]?",
            content
        ):
            fact_text = m.group(1).strip()
            answer = m.group(2).strip()
            if len(answer) > 3 and not answer.startswith("http"):
                facts.append({
                    "fact": f"{fact_text}: {answer}",
                    "answer": answer,
                    "answer_type": "string",
                    "domain": domain,
                    "subdomain": subdomain,
                    "source": source_url,
                    "tags": [],
                    "confidence": 0.5,
                })

        # Pattern: version numbers in context
        for m in re.finditer(
            r"(?:version|v|release)\s*[=:]?\s*(\d+\.\d+(?:\.\d+)?)",
            content, re.IGNORECASE
        ):
            facts.append({
                "fact": f"Version {m.group(1)} mentioned in documentation",
                "answer": m.group(1),
                "answer_type": "version",
                "domain": domain,
                "subdomain": subdomain,
                "source": source_url,
                "tags": ["version"],
                "confidence": 0.6,
            })

        # Pattern: constants (ALL_CAPS = value)
        for m in re.finditer(
            r"(?:^|\n)\s*`?([A-Z][A-Z_]{2,30})`?\s*[=:]\s*[`\"]?(\d+|0x[0-9a-fA-F]+|"
            r"true|false|\"[^\"]+\"|'[^']+')",
            content
        ):
            facts.append({
                "fact": f"{m.group(1)} = {m.group(2)}",
                "answer": m.group(2).strip("'\""),
                "answer_type": "constant",
                "domain": domain,
                "subdomain": subdomain,
                "source": source_url,
                "tags": ["constant", "parameter"],
                "confidence": 0.7,
            })

        # Pattern: API endpoints
        for m in re.finditer(
            r"(?:GET|POST|PUT|DELETE|PATCH)\s+(/[a-zA-Z0-9/_{}.-]+)",
            content
        ):
            facts.append({
                "fact": f"API endpoint: {m.group(0)}",
                "answer": m.group(1),
                "answer_type": "endpoint",
                "domain": domain,
                "subdomain": "api",
                "source": source_url,
                "tags": ["api", "endpoint"],
                "confidence": 0.8,
            })

        return facts[:50]  # cap at 50 auto-extracted facts per page

    # -- Multi-page crawl ----------------------------------------------------

    def crawl_source(self, source: ResearchSource,
                     max_pages: int = 20) -> list[ScrapedPage]:
        """Crawl a research source following links up to max_depth.

        Returns list of successfully scraped pages.
        """
        visited: set[str] = set()
        to_visit: list[tuple[str, int]] = [(source.url, 0)]
        pages: list[ScrapedPage] = []

        base_domain = urlparse(source.url).netloc

        while to_visit and len(pages) < max_pages:
            url, depth = to_visit.pop(0)

            if url in visited:
                continue
            if depth > source.max_depth:
                continue

            visited.add(url)

            # Only follow links within the same domain
            if urlparse(url).netloc != base_domain:
                continue

            page = self.fetch(url)
            if not page.ok:
                continue

            # Apply selectors if provided
            if source.selectors:
                extracted = self.extract_with_selectors(page, source.selectors)
                if "content" in extracted:
                    page.markdown = extracted["content"]

            # Extract facts
            self.extract_facts(
                page,
                patterns=source.extract_patterns,
                domain=source.domain,
                subdomain=source.subdomain,
            )

            pages.append(page)

            # Queue child links
            if source.follow_links and depth < source.max_depth:
                for link in page.links:
                    if link not in visited:
                        to_visit.append((link, depth + 1))

        log.info("scraper.crawl_complete",
                 source=source.url[:60],
                 pages=len(pages),
                 total_facts=sum(len(p.extracted_facts) for p in pages))

        return pages

    # -- Research file generation --------------------------------------------

    def pages_to_research_md(self, pages: list[ScrapedPage],
                              source: ResearchSource) -> str:
        """Convert scraped pages into a structured .md research file.

        This is the format ExpansionManager expects.
        """
        now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        lines = [
            f"# Research: {source.domain} / {source.subdomain or 'general'}",
            "",
            f"**Domain**: {source.domain}",
        ]
        if source.subdomain:
            lines.append(f"**Subdomain**: {source.subdomain}")
        lines.extend([
            f"**Researched**: {now}",
            f"**Source**: {source.url}",
            f"**Pages Scraped**: {len(pages)}",
            f"**Type**: {source.source_type}",
            "",
            "## Summary",
            "",
        ])

        # Aggregate content from all pages
        total_facts = []
        total_code = []
        for page in pages:
            total_facts.extend(page.extracted_facts)
            total_code.extend(page.extracted_code_blocks)

        if total_facts:
            lines.append(f"Extracted {len(total_facts)} facts from {len(pages)} pages.")
        else:
            lines.append(f"Scraped {len(pages)} pages of documentation.")
        lines.append("")

        # Key findings section
        lines.extend(["## Key Findings", ""])

        # Group high-confidence facts
        high_conf = [f for f in total_facts if f.get("confidence", 0) >= 0.7]
        medium_conf = [f for f in total_facts if 0.5 <= f.get("confidence", 0) < 0.7]

        if high_conf:
            lines.append("### High Confidence Facts")
            lines.append("")
            for fact in high_conf[:30]:
                lines.append(f"- **{fact['fact']}**")
                lines.append(f"  - Answer: `{fact['answer']}`")
                lines.append(f"  - Type: {fact['answer_type']}")
                lines.append(f"  - Source: {fact['source']}")
                lines.append("")

        if medium_conf:
            lines.append("### Additional Findings")
            lines.append("")
            for fact in medium_conf[:20]:
                lines.append(f"- {fact['fact']}")
                if fact.get("answer"):
                    lines.append(f"  - Value: `{fact['answer']}`")
                lines.append("")

        # Code examples
        if total_code:
            lines.extend(["## Code Examples", ""])
            for i, block in enumerate(total_code[:10]):
                lang = block.get("language", "")
                lines.append(f"### Example {i + 1}" + (f" ({lang})" if lang else ""))
                lines.append(f"```{lang}")
                # Truncate very long code blocks
                code = block["code"]
                if len(code) > 500:
                    code = code[:500] + "\n... (truncated)"
                lines.append(code)
                lines.append("```")
                lines.append("")

        # Content from pages (condensed)
        lines.extend(["## Scraped Content", ""])
        for page in pages[:10]:
            lines.append(f"### {page.title or page.url}")
            lines.append(f"*Source: {page.url}*")
            lines.append("")
            # Take first 500 chars of markdown content
            content_preview = page.markdown[:500]
            if len(page.markdown) > 500:
                content_preview += "..."
            lines.append(content_preview)
            lines.append("")

        # Sources list
        lines.extend(["## Sources", ""])
        for page in pages:
            status = "OK" if page.ok else f"ERROR: {page.error}"
            lines.append(f"- [{page.title or page.url}]({page.url}) — {status}")

        # Related topics
        lines.extend(["", "## Related Topics", ""])
        all_tags = set()
        for fact in total_facts:
            all_tags.update(fact.get("tags", []))
        all_tags.update(source.tags)
        for tag in sorted(all_tags):
            lines.append(f"- {tag}")

        return "\n".join(lines)

    # -- Stats ---------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        return {
            "requests_made": self._request_count,
            "errors": self._error_count,
            "cached_pages": len(self._cache),
            "success_rate": (
                f"{(self._request_count - self._error_count) / max(self._request_count, 1) * 100:.0f}%"
            ),
        }

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
