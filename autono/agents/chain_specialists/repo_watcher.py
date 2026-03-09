"""RepoWatcherAgent — autonomous GitHub repository monitor.

Continuously watches all official blockchain repositories registered in the
repo_registry for:
- New releases (tags, changelogs, pre-releases/betas)
- Breaking change issues and security advisories
- Recent commits to tracked branches
- Critical pull requests

When changes are detected, the agent:
1. Creates knowledge nodes in the graph for discoverability
2. Notifies the relevant chain specialist agent
3. Broadcasts CRITICAL security advisories to all agents
4. Persists watch state so nothing is missed across restarts

GitHub API rate limits are respected:
- Unauthenticated: 60 requests/hour
- Authenticated (GITHUB_TOKEN): 5,000 requests/hour
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import structlog

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message
from autono.knowledge.repo_registry import (
    WATCHED_REPOS,
    WatchedRepo,
    WatchPriority,
    WatchScope,
    get_critical_repos,
    get_repos_by_domain,
)

log = structlog.get_logger()

# Map domains to their specialist agent names
_DOMAIN_AGENT_MAP: dict[str, str] = {
    "cardano": "CardanoChainAgent",
    "bitcoin": "BitcoinChainAgent",
    "charms": "CharmsAgent",
    "bitcoinos": "BitcoinChainAgent",   # routes to Bitcoin specialist
    "night_chain": "NightChainAgent",
}

# State file location — survives restarts
_STATE_DIR = Path.home() / ".autono"
_STATE_FILE = _STATE_DIR / "repo_watcher_state.json"


class RepoWatcherAgent(AutonomousAgent):
    """Autonomous agent that monitors all official blockchain repositories.

    Polls GitHub for releases, commits, issues, and security advisories
    across every repo in the official registry. Detected changes are
    converted to knowledge nodes and routed to the appropriate chain
    specialist agent.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RepoWatcherAgent",
            role="Repository monitor — watches all official blockchain repos for releases, breaking changes, and security advisories",
            capabilities=[AgentCapability.RESEARCH],
        )
        self._github_token: str = os.environ.get("GITHUB_TOKEN", "")
        self._store: Any = None
        self._graph: Any = None

        # Per-repo watch state: { "owner/repo": { last_release, last_commit, last_checked } }
        self._watch_state: dict[str, dict[str, str]] = {}
        self._load_state()

        # Rate-limit tracking
        self._requests_remaining: int = 5000 if self._github_token else 60
        self._rate_reset_at: float = 0.0

        # HTTP client (created lazily in async context)
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle / config ---------------------------------------------------

    @property
    def work_interval(self) -> float:
        """Check repos every 5 minutes."""
        return 300.0

    def set_dependencies(self, store: Any, graph: Any) -> None:
        """Inject knowledge store and graph for creating update nodes."""
        self._store = store
        self._graph = graph

    # -- state persistence ----------------------------------------------------

    def _load_state(self) -> None:
        """Load watch state from disk so we survive restarts."""
        if _STATE_FILE.exists():
            try:
                raw = _STATE_FILE.read_text(encoding="utf-8")
                self._watch_state = json.loads(raw)
                self.log.info("repo_watcher.state_loaded",
                              repos_tracked=len(self._watch_state))
            except (json.JSONDecodeError, OSError) as exc:
                self.log.warning("repo_watcher.state_load_failed", error=str(exc))
                self._watch_state = {}

    def _save_state(self) -> None:
        """Persist watch state to disk."""
        try:
            _STATE_DIR.mkdir(parents=True, exist_ok=True)
            _STATE_FILE.write_text(
                json.dumps(self._watch_state, indent=2),
                encoding="utf-8",
            )
        except OSError as exc:
            self.log.warning("repo_watcher.state_save_failed", error=str(exc))

    # -- HTTP helpers ---------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        """Return (and lazily create) the shared async HTTP client."""
        if self._client is None or self._client.is_closed:
            headers: dict[str, str] = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "autono-repo-watcher/1.0",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if self._github_token:
                headers["Authorization"] = f"Bearer {self._github_token}"
            self._client = httpx.AsyncClient(
                headers=headers,
                timeout=httpx.Timeout(30.0, connect=10.0),
                follow_redirects=True,
            )
        return self._client

    async def _github_get(self, url: str) -> dict[str, Any] | list[Any] | None:
        """Make a rate-limited GET request to the GitHub API.

        Returns parsed JSON on success, ``None`` on failure or rate-limit.
        """
        # Check rate limit before making the request
        if self._requests_remaining <= 1:
            now = time.time()
            if now < self._rate_reset_at:
                wait = int(self._rate_reset_at - now)
                self.log.warning("repo_watcher.rate_limited",
                                 wait_seconds=wait)
                return None
            # Reset window has passed
            self._requests_remaining = 5000 if self._github_token else 60

        client = await self._get_client()
        try:
            resp = await client.get(url)

            # Update rate-limit counters from response headers
            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining is not None:
                self._requests_remaining = int(remaining)
            reset_at = resp.headers.get("x-ratelimit-reset")
            if reset_at is not None:
                self._rate_reset_at = float(reset_at)

            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 403:
                self.log.warning("repo_watcher.forbidden", url=url)
                return None
            if resp.status_code == 404:
                # Repo may not exist yet (e.g. midnight-network/midnight-core)
                self.log.debug("repo_watcher.not_found", url=url)
                return None
            self.log.warning("repo_watcher.http_error",
                             url=url, status=resp.status_code)
            return None
        except httpx.HTTPError as exc:
            self.log.error("repo_watcher.request_failed",
                           url=url, error=str(exc))
            return None

    # -- core work loop -------------------------------------------------------

    async def do_work(self) -> None:
        """Main work cycle: iterate over watched repos and check for changes.

        Critical repos are checked every cycle.  Lower-priority repos are
        checked only when their individual ``poll_interval`` has elapsed.
        """
        now = datetime.now(timezone.utc)
        checked = 0

        for repo in WATCHED_REPOS:
            # Respect per-repo poll interval
            state = self._watch_state.get(repo.full_name, {})
            last_checked_str = state.get("last_checked", "")
            if last_checked_str:
                try:
                    last_dt = datetime.fromisoformat(last_checked_str)
                    elapsed = (now - last_dt).total_seconds()
                    if elapsed < repo.poll_interval:
                        continue
                except ValueError:
                    pass  # corrupted timestamp, re-check

            # Bail out if we're rate-limited
            if self._requests_remaining <= 1:
                self.log.info("repo_watcher.pausing_rate_limit",
                              checked_so_far=checked)
                break

            await self._check_repo(repo)
            checked += 1

        if checked > 0:
            self._save_state()
            self.log.info("repo_watcher.cycle_complete",
                          repos_checked=checked,
                          rate_remaining=self._requests_remaining)

    # -- per-repo checks ------------------------------------------------------

    async def _check_repo(self, repo: WatchedRepo) -> None:
        """Run all applicable checks for a single repo."""
        scopes = repo.watch_scopes
        check_all = WatchScope.ALL in scopes

        if check_all or WatchScope.RELEASES in scopes:
            await self._check_releases(repo)

        if check_all or WatchScope.COMMITS in scopes:
            await self._check_commits(repo)

        if check_all or WatchScope.ISSUES in scopes or WatchScope.SECURITY in scopes:
            await self._check_issues(repo)

        # Update last_checked timestamp
        state = self._watch_state.setdefault(repo.full_name, {})
        state["last_checked"] = datetime.now(timezone.utc).isoformat()

    async def _check_releases(self, repo: WatchedRepo) -> None:
        """Check for new releases (including pre-releases / betas)."""
        url = f"{repo.api_url}/releases/latest"
        data = await self._github_get(url)
        if data is None or not isinstance(data, dict):
            return

        tag = data.get("tag_name", "")
        if not tag:
            return

        state = self._watch_state.setdefault(repo.full_name, {})
        last_release = state.get("last_release", "")

        if tag != last_release:
            is_prerelease = data.get("prerelease", False)
            release_name = data.get("name", tag)
            body = data.get("body", "") or ""
            html_url = data.get("html_url", repo.github_url)

            # Truncate body for knowledge node (keep first 1500 chars)
            summary = body[:1500] + ("..." if len(body) > 1500 else "")

            tags = ["release", repo.domain]
            if is_prerelease:
                tags.append("beta")
            priority = 3 if repo.priority == WatchPriority.CRITICAL else 2

            await self._create_update_node(
                repo=repo,
                update_type="release",
                title=f"New release: {repo.full_name} {release_name}",
                content=(
                    f"Repository {repo.full_name} released {release_name} "
                    f"(tag: {tag}).\n\n"
                    f"Pre-release: {is_prerelease}\n"
                    f"URL: {html_url}\n\n"
                    f"Release notes:\n{summary}"
                ),
                tags=tags,
            )
            await self._notify_chain_agent(
                repo=repo,
                update_type="new_release",
                details={
                    "repo": repo.full_name,
                    "tag": tag,
                    "name": release_name,
                    "prerelease": is_prerelease,
                    "url": html_url,
                    "body_preview": summary[:500],
                },
                priority=priority,
            )

            state["last_release"] = tag
            self.log.info("repo_watcher.new_release",
                          repo=repo.full_name, tag=tag,
                          prerelease=is_prerelease)

    async def _check_commits(self, repo: WatchedRepo) -> None:
        """Check for new commits on the tracked branch."""
        url = (
            f"{repo.api_url}/commits"
            f"?sha={repo.branch}&per_page=5"
        )
        data = await self._github_get(url)
        if data is None or not isinstance(data, list) or len(data) == 0:
            return

        latest_sha = data[0].get("sha", "")
        if not latest_sha:
            return

        state = self._watch_state.setdefault(repo.full_name, {})
        last_commit = state.get("last_commit", "")

        if latest_sha != last_commit:
            # Gather commit summaries for new commits
            new_commits: list[dict[str, str]] = []
            for commit_data in data:
                sha = commit_data.get("sha", "")
                if sha == last_commit:
                    break
                commit_info = commit_data.get("commit", {})
                message = commit_info.get("message", "").split("\n")[0]  # first line
                author = commit_info.get("author", {}).get("name", "unknown")
                new_commits.append({
                    "sha": sha[:8],
                    "message": message,
                    "author": author,
                })

            if new_commits and last_commit:
                # Only notify if we had a previous baseline (skip first run)
                commit_summary = "\n".join(
                    f"  {c['sha']} {c['message']} ({c['author']})"
                    for c in new_commits
                )
                await self._create_update_node(
                    repo=repo,
                    update_type="commits",
                    title=f"New commits: {repo.full_name} ({len(new_commits)} commits)",
                    content=(
                        f"{len(new_commits)} new commit(s) on "
                        f"{repo.full_name}/{repo.branch}:\n{commit_summary}"
                    ),
                    tags=["commits", repo.domain],
                )

            state["last_commit"] = latest_sha

    async def _check_issues(self, repo: WatchedRepo) -> None:
        """Check for open issues tagged as breaking changes or security advisories."""
        labels = "breaking-change,security,breaking,vulnerability"
        url = (
            f"{repo.api_url}/issues"
            f"?state=open&labels={labels}&per_page=10&sort=updated&direction=desc"
        )
        data = await self._github_get(url)
        if data is None or not isinstance(data, list):
            return

        state = self._watch_state.setdefault(repo.full_name, {})
        seen_issues: list[str] = state.get("seen_issues", [])

        for issue in data:
            issue_id = str(issue.get("number", ""))
            if not issue_id or issue_id in seen_issues:
                continue

            title = issue.get("title", "")
            body = (issue.get("body", "") or "")[:800]
            html_url = issue.get("html_url", "")
            issue_labels = [
                lbl.get("name", "").lower()
                for lbl in issue.get("labels", [])
            ]

            is_security = any(
                lbl in ("security", "vulnerability", "cve")
                for lbl in issue_labels
            )
            is_breaking = any(
                lbl in ("breaking-change", "breaking")
                for lbl in issue_labels
            )

            tags = ["issue", repo.domain]
            if is_security:
                tags.append("security")
            if is_breaking:
                tags.append("breaking-change")

            await self._create_update_node(
                repo=repo,
                update_type="security" if is_security else "breaking_change",
                title=f"{'SECURITY' if is_security else 'Breaking change'}: {repo.full_name} #{issue_id} — {title}",
                content=(
                    f"{'Security advisory' if is_security else 'Breaking change'} "
                    f"in {repo.full_name}:\n\n"
                    f"Issue #{issue_id}: {title}\n"
                    f"URL: {html_url}\n\n"
                    f"{body}"
                ),
                tags=tags,
            )

            # Security advisories are CRITICAL — broadcast to all agents
            if is_security:
                await self.broadcast("alert", {
                    "type": "security_advisory",
                    "repo": repo.full_name,
                    "domain": repo.domain,
                    "issue": issue_id,
                    "title": title,
                    "url": html_url,
                }, priority=3)
                self.log.warning("repo_watcher.security_advisory",
                                 repo=repo.full_name, issue=issue_id,
                                 title=title)
            else:
                await self._notify_chain_agent(
                    repo=repo,
                    update_type="breaking_change",
                    details={
                        "repo": repo.full_name,
                        "issue": issue_id,
                        "title": title,
                        "url": html_url,
                    },
                    priority=2,
                )

            seen_issues.append(issue_id)

        state["seen_issues"] = seen_issues[-100:]  # cap stored list

    # -- knowledge graph integration ------------------------------------------

    async def _create_update_node(
        self,
        repo: WatchedRepo,
        update_type: str,
        title: str,
        content: str,
        tags: list[str] | None = None,
    ) -> None:
        """Create a KnowledgeNode for a detected repository change."""
        if not self._store:
            return

        from autono.knowledge.types import KnowledgeNode, VolatilityTier

        volatility_map = {
            "release": VolatilityTier.MODERATE,
            "commits": VolatilityTier.VOLATILE,
            "security": VolatilityTier.VOLATILE,
            "breaking_change": VolatilityTier.VOLATILE,
        }
        priority_map = {
            "release": 70,
            "commits": 40,
            "security": 95,
            "breaking_change": 85,
        }

        node = KnowledgeNode(
            content=f"{title}\n\n{content}",
            domain=repo.domain,
            subdomain=repo.subdomain or "updates",
            volatility=volatility_map.get(update_type, VolatilityTier.MODERATE),
            priority_score=priority_map.get(update_type, 50),
            source_file=repo.github_url,
            tags=list(set((tags or []) + repo.tags + [update_type, "repo_watcher"])),
        )
        self._store.save_node(node)

        self.log.info("repo_watcher.node_created",
                      repo=repo.full_name,
                      update_type=update_type,
                      node_id=node.id)

    # -- agent routing --------------------------------------------------------

    async def _notify_chain_agent(
        self,
        repo: WatchedRepo,
        update_type: str,
        details: dict[str, Any],
        priority: int = 1,
    ) -> None:
        """Route an update to the appropriate chain specialist agent."""
        agent_name = _DOMAIN_AGENT_MAP.get(repo.domain)
        if not agent_name:
            self.log.debug("repo_watcher.no_agent_for_domain",
                           domain=repo.domain)
            return

        await self.send(agent_name, "alert", {
            "type": f"repo_{update_type}",
            "domain": repo.domain,
            **details,
        }, priority=priority)

    # -- message handling -----------------------------------------------------

    async def handle_message(self, msg: Message) -> None:
        """Handle incoming messages from other agents.

        Supported message types:
        - ``force_check``: immediately check a specific repo or domain
        - ``add_repo``: dynamically add a repo to the watch list
        - ``status_query``: return current watcher status
        """
        if msg.kind == "request":
            req_type = msg.payload.get("type", "")

            if req_type == "force_check":
                # Force an immediate check of a specific repo or all repos in a domain
                repo_name = msg.payload.get("repo")
                domain = msg.payload.get("domain")

                if repo_name:
                    for repo in WATCHED_REPOS:
                        if repo.full_name == repo_name:
                            await self._check_repo(repo)
                            self._save_state()
                            await self.send(msg.sender, "response", {
                                "type": "force_check_complete",
                                "repo": repo_name,
                            })
                            return
                elif domain:
                    repos = get_repos_by_domain(domain)
                    for repo in repos:
                        await self._check_repo(repo)
                    self._save_state()
                    await self.send(msg.sender, "response", {
                        "type": "force_check_complete",
                        "domain": domain,
                        "repos_checked": len(repos),
                    })

            elif req_type == "status_query":
                await self.send(msg.sender, "response", {
                    "type": "watcher_status",
                    "repos_tracked": len(WATCHED_REPOS),
                    "critical_repos": len(get_critical_repos()),
                    "rate_remaining": self._requests_remaining,
                    "has_token": bool(self._github_token),
                    "states_loaded": len(self._watch_state),
                })

    # -- learning loop --------------------------------------------------------

    async def learn(self) -> None:
        """Record what the watcher has observed for self-improvement."""
        self.memory.remember("tech_updates", {
            "area": "repo_monitoring",
            "repos_tracked": len(WATCHED_REPOS),
            "states_stored": len(self._watch_state),
            "rate_remaining": self._requests_remaining,
            "has_token": bool(self._github_token),
            "domains": list({r.domain for r in WATCHED_REPOS}),
        })

    # -- introspection --------------------------------------------------------

    def report(self) -> dict[str, Any]:
        """Status report for the human council."""
        base = super().report()

        # Summarize per-domain counts
        domain_counts: dict[str, int] = {}
        for repo in WATCHED_REPOS:
            domain_counts[repo.domain] = domain_counts.get(repo.domain, 0) + 1

        base.update({
            "repos_tracked": len(WATCHED_REPOS),
            "repos_by_domain": domain_counts,
            "critical_repos": [r.full_name for r in get_critical_repos()],
            "rate_remaining": self._requests_remaining,
            "authenticated": bool(self._github_token),
            "states_persisted": len(self._watch_state),
        })
        return base
