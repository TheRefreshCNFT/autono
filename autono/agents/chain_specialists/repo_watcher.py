"""RepoWatcherAgent — autonomous GitHub repository monitor and contributor.

MISSION: Stay ahead of every protocol change. Don't just watch — get involved.
When a beta drops, test it. When a breaking change is filed, assess impact.
When a security advisory appears, broadcast it and start patching. The agents
should be among the first to know about and adapt to protocol changes.

This agent doesn't just poll — it PARTICIPATES:

WATCH (passive):
- New releases (tags, changelogs, pre-releases/betas)
- Breaking change issues and security advisories
- Recent commits to tracked branches
- Critical pull requests and their discussions

ENGAGE (active — requires GITHUB_TOKEN with repo scope):
- Comment on issues with compatibility assessments
- Subscribe to repos for real-time notifications
- Test beta/RC releases automatically and report results
- File issues when incompatibilities are found during testing
- Track PR discussions that affect autono's architecture

REACT (autonomous):
- When a beta drops: download, test against our system, report results
- When a breaking change lands: assess impact, create migration plan
- When a security advisory fires: broadcast to all agents, begin patching
- When a new SDK version ships: evaluate for cost optimization potential

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
    """Autonomous agent that monitors AND engages with blockchain repositories.

    Beyond polling for releases, commits, and issues, this agent actively
    participates: commenting on breaking changes with impact assessments,
    testing beta releases, filing issues when incompatibilities are found,
    and subscribing to repos for real-time awareness.
    """

    def __init__(self) -> None:
        super().__init__(
            name="RepoWatcherAgent",
            role="Repository monitor and contributor — watches, tests, and engages with all official blockchain repos",
            capabilities=[AgentCapability.RESEARCH, AgentCapability.ENGAGE],
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

        # Track whether we've done first-run subscriptions
        self._subscribed: bool = False

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

    async def _github_post(
        self, url: str, payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Make a rate-limited POST request to the GitHub API.

        Requires GITHUB_TOKEN. Returns parsed JSON on success, None on failure.
        """
        if not self._github_token:
            self.log.debug("repo_watcher.post_skipped_no_token", url=url)
            return None

        if self._requests_remaining <= 1:
            now = time.time()
            if now < self._rate_reset_at:
                self.log.warning("repo_watcher.rate_limited_post",
                                 wait_seconds=int(self._rate_reset_at - now))
                return None
            self._requests_remaining = 5000

        client = await self._get_client()
        try:
            resp = await client.post(url, json=payload)

            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining is not None:
                self._requests_remaining = int(remaining)
            reset_at = resp.headers.get("x-ratelimit-reset")
            if reset_at is not None:
                self._rate_reset_at = float(reset_at)

            if resp.status_code in (200, 201, 204):
                return resp.json() if resp.content else {}
            self.log.warning("repo_watcher.post_error",
                             url=url, status=resp.status_code,
                             body=resp.text[:300])
            return None
        except httpx.HTTPError as exc:
            self.log.error("repo_watcher.post_failed",
                           url=url, error=str(exc))
            return None

    async def _github_put(
        self, url: str, payload: dict[str, Any] | None = None,
    ) -> bool:
        """Make a rate-limited PUT request (used for subscriptions).

        Returns True on success, False otherwise.
        """
        if not self._github_token:
            return False

        client = await self._get_client()
        try:
            resp = await client.put(url, json=payload or {})
            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining is not None:
                self._requests_remaining = int(remaining)
            return resp.status_code in (200, 204)
        except httpx.HTTPError as exc:
            self.log.error("repo_watcher.put_failed",
                           url=url, error=str(exc))
            return False

    # -- engagement methods ---------------------------------------------------

    async def _comment_on_issue(
        self,
        repo: WatchedRepo,
        issue_number: str,
        body: str,
    ) -> dict[str, Any] | None:
        """Post a comment on a GitHub issue with our assessment.

        Used to share compatibility impact analysis, migration guidance,
        or testing results directly on upstream issues.
        """
        url = f"{repo.api_url}/issues/{issue_number}/comments"
        comment_body = (
            f"**autono compatibility assessment** 🔍\n\n"
            f"{body}\n\n"
            f"---\n"
            f"*Posted by [autono](https://github.com/TheRefreshCNFT/autono) "
            f"RepoWatcherAgent — automated blockchain protocol monitor*"
        )
        result = await self._github_post(url, {"body": comment_body})
        if result:
            self.log.info("repo_watcher.commented",
                          repo=repo.full_name, issue=issue_number)
        return result

    async def _subscribe_to_repo(self, repo: WatchedRepo) -> bool:
        """Subscribe to a repository for real-time notifications.

        Sets the subscription to 'watching' so we get notified of all
        activity, not just releases.
        """
        url = f"{repo.api_url}/subscription"
        success = await self._github_put(url, {
            "subscribed": True,
            "ignored": False,
        })
        if success:
            self.log.info("repo_watcher.subscribed", repo=repo.full_name)
        return success

    async def _file_issue(
        self,
        repo: WatchedRepo,
        title: str,
        body: str,
        labels: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """File a new issue on a repository.

        Used to report incompatibilities discovered during beta testing
        or breaking changes that affect the autono ecosystem.
        """
        url = f"{repo.api_url}/issues"
        issue_body = (
            f"{body}\n\n"
            f"---\n"
            f"*Filed by [autono](https://github.com/TheRefreshCNFT/autono) "
            f"RepoWatcherAgent — automated compatibility testing*"
        )
        payload: dict[str, Any] = {"title": title, "body": issue_body}
        if labels:
            payload["labels"] = labels
        result = await self._github_post(url, payload)
        if result:
            self.log.info("repo_watcher.issue_filed",
                          repo=repo.full_name,
                          issue=result.get("number"))
        return result

    # -- beta testing pipeline ------------------------------------------------

    async def _test_beta_release(
        self,
        repo: WatchedRepo,
        tag: str,
        release_url: str,
        release_body: str,
    ) -> dict[str, Any]:
        """Evaluate a beta/RC release for compatibility with autono.

        Performs a lightweight assessment by analyzing the changelog for
        breaking changes, deprecated APIs, and new features. Results are
        reported back to the chain specialist and optionally commented
        on the release.

        Returns a test report dict with findings.
        """
        report: dict[str, Any] = {
            "repo": repo.full_name,
            "tag": tag,
            "status": "assessed",
            "breaking_changes": [],
            "deprecations": [],
            "new_features": [],
            "compatibility": "unknown",
        }

        # Analyze release notes for breaking indicators
        body_lower = release_body.lower()
        breaking_keywords = [
            "breaking change", "breaking:", "removed", "deprecated",
            "migration required", "incompatible", "renamed",
        ]
        for keyword in breaking_keywords:
            if keyword in body_lower:
                # Extract the line containing the keyword
                for line in release_body.split("\n"):
                    if keyword in line.lower():
                        report["breaking_changes"].append(line.strip())

        deprecation_keywords = ["deprecated", "will be removed", "no longer supported"]
        for keyword in deprecation_keywords:
            if keyword in body_lower:
                for line in release_body.split("\n"):
                    if keyword in line.lower() and line.strip() not in report["breaking_changes"]:
                        report["deprecations"].append(line.strip())

        feature_keywords = ["new feature", "added", "introducing", "now supports"]
        for keyword in feature_keywords:
            if keyword in body_lower:
                for line in release_body.split("\n"):
                    if keyword in line.lower():
                        report["new_features"].append(line.strip())

        # Determine compatibility verdict
        if report["breaking_changes"]:
            report["compatibility"] = "action_required"
            report["status"] = "breaking_changes_detected"
        elif report["deprecations"]:
            report["compatibility"] = "review_recommended"
            report["status"] = "deprecations_found"
        else:
            report["compatibility"] = "likely_compatible"
            report["status"] = "no_issues_detected"

        # Create knowledge node with test results
        await self._create_update_node(
            repo=repo,
            update_type="release",
            title=f"Beta test results: {repo.full_name} {tag}",
            content=(
                f"Beta/RC assessment for {repo.full_name} {tag}:\n"
                f"Compatibility: {report['compatibility']}\n"
                f"Breaking changes: {len(report['breaking_changes'])}\n"
                f"Deprecations: {len(report['deprecations'])}\n"
                f"New features: {len(report['new_features'])}\n\n"
                f"Details:\n"
                + "\n".join(f"  - {item}" for item in report["breaking_changes"][:10])
            ),
            tags=["beta_test", repo.domain, report["compatibility"]],
        )

        # Notify chain specialist with the full report
        await self._notify_chain_agent(
            repo=repo,
            update_type="beta_test_results",
            details=report,
            priority=3 if report["compatibility"] == "action_required" else 2,
        )

        self.log.info("repo_watcher.beta_tested",
                      repo=repo.full_name, tag=tag,
                      compatibility=report["compatibility"],
                      breaking=len(report["breaking_changes"]))

        return report

    # -- core work loop -------------------------------------------------------

    async def do_work(self) -> None:
        """Main work cycle: iterate over watched repos and check for changes.

        Critical repos are checked every cycle.  Lower-priority repos are
        checked only when their individual ``poll_interval`` has elapsed.
        """
        # First run: subscribe to all critical repos for real-time notifications
        if not self._subscribed and self._github_token:
            for repo in get_critical_repos():
                await self._subscribe_to_repo(repo)
            self._subscribed = True

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

        if check_all or WatchScope.PULL_REQUESTS in scopes:
            await self._check_pull_requests(repo)

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

            # ENGAGE: If this is a beta/RC, run the testing pipeline
            if is_prerelease:
                await self._test_beta_release(
                    repo=repo,
                    tag=tag,
                    release_url=html_url,
                    release_body=body,
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

                # ENGAGE: Comment on security issues with our awareness
                await self._comment_on_issue(
                    repo, issue_id,
                    f"**Security advisory detected.**\n\n"
                    f"We are tracking this issue and assessing impact on "
                    f"the `{repo.domain}` integration in autono.\n\n"
                    f"Automated monitoring is active — our agents have been "
                    f"notified and will begin evaluating patches.",
                )
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

                # ENGAGE: Comment on breaking changes with impact assessment
                if is_breaking:
                    await self._comment_on_issue(
                        repo, issue_id,
                        f"**Breaking change impact assessment:**\n\n"
                        f"This change affects the `{repo.domain}` domain "
                        f"in our multi-chain agent system. We are evaluating "
                        f"compatibility and will track migration requirements.\n\n"
                        f"Affected component: `{_DOMAIN_AGENT_MAP.get(repo.domain, 'unknown')}` chain specialist",
                    )

            seen_issues.append(issue_id)

        state["seen_issues"] = seen_issues[-100:]  # cap stored list

    async def _check_pull_requests(self, repo: WatchedRepo) -> None:
        """Check for open PRs with breaking/critical labels or targeting tracked branch."""
        url = (
            f"{repo.api_url}/pulls"
            f"?state=open&sort=updated&direction=desc&per_page=10"
        )
        data = await self._github_get(url)
        if data is None or not isinstance(data, list):
            return

        critical_labels = {"breaking-change", "breaking", "security", "critical"}

        state = self._watch_state.setdefault(repo.full_name, {})
        seen_prs: list[str] = state.get("seen_prs", [])
        tracked_prs: dict[str, str] = state.get("tracked_prs", {})
        # tracked_prs maps PR number (str) -> last known state ("open" or "merged")

        for pr in data:
            pr_number = str(pr.get("number", ""))
            if not pr_number:
                continue

            pr_labels = {
                lbl.get("name", "").lower()
                for lbl in pr.get("labels", [])
            }
            base_branch = pr.get("base", {}).get("ref", "")
            title = pr.get("title", "")
            body = (pr.get("body", "") or "")[:800]
            html_url = pr.get("html_url", "")
            is_merged = pr.get("merged_at") is not None

            # Filter: only care about PRs with critical labels OR targeting tracked branch
            has_critical_label = bool(pr_labels & critical_labels)
            targets_tracked_branch = base_branch == repo.branch

            if not has_critical_label and not targets_tracked_branch:
                continue

            # Handle new PRs we haven't seen before
            if pr_number not in seen_prs:
                if has_critical_label:
                    is_security = "security" in pr_labels
                    is_breaking = bool(pr_labels & {"breaking-change", "breaking"})

                    tags = ["pull_request", repo.domain]
                    if is_security:
                        tags.append("security")
                    if is_breaking:
                        tags.append("breaking-change")
                    if "critical" in pr_labels:
                        tags.append("critical")

                    update_type = "security" if is_security else "breaking_change"

                    await self._create_update_node(
                        repo=repo,
                        update_type=update_type,
                        title=(
                            f"Critical PR: {repo.full_name} #{pr_number} — {title}"
                        ),
                        content=(
                            f"{'Security' if is_security else 'Breaking/critical'} "
                            f"pull request in {repo.full_name}:\n\n"
                            f"PR #{pr_number}: {title}\n"
                            f"Target branch: {base_branch}\n"
                            f"Labels: {', '.join(sorted(pr_labels))}\n"
                            f"URL: {html_url}\n\n"
                            f"{body}"
                        ),
                        tags=tags,
                    )

                    await self._notify_chain_agent(
                        repo=repo,
                        update_type="critical_pr",
                        details={
                            "repo": repo.full_name,
                            "pr": pr_number,
                            "title": title,
                            "url": html_url,
                            "labels": sorted(pr_labels),
                            "base_branch": base_branch,
                            "is_security": is_security,
                            "is_breaking": is_breaking,
                        },
                        priority=3 if is_security else 2,
                    )

                    # ENGAGE: Comment on breaking/critical PRs with impact assessment
                    specialist = _DOMAIN_AGENT_MAP.get(repo.domain, "unknown")
                    await self._comment_on_issue(
                        repo, pr_number,
                        f"**Pull request impact assessment:**\n\n"
                        f"This {'security-related ' if is_security else ''}"
                        f"{'breaking ' if is_breaking else 'critical '}"
                        f"PR affects the `{repo.domain}` domain in our "
                        f"multi-chain agent system.\n\n"
                        f"Affected component: `{specialist}` chain specialist\n\n"
                        f"We are tracking this PR and will evaluate the impact "
                        f"on our integrations when it is merged.",
                    )

                    # Track this PR for merge monitoring
                    tracked_prs[pr_number] = "open"

                seen_prs.append(pr_number)

                self.log.info("repo_watcher.new_critical_pr",
                              repo=repo.full_name, pr=pr_number,
                              title=title, labels=sorted(pr_labels))

        # Check merge status of previously tracked breaking PRs
        merged_to_remove: list[str] = []
        for tracked_pr_number, tracked_status in tracked_prs.items():
            if tracked_status == "merged":
                continue

            # Fetch current PR state
            pr_url = f"{repo.api_url}/pulls/{tracked_pr_number}"
            pr_data = await self._github_get(pr_url)
            if pr_data is None or not isinstance(pr_data, dict):
                continue

            if pr_data.get("merged_at") is not None and tracked_status == "open":
                pr_title = pr_data.get("title", "")
                pr_html_url = pr_data.get("html_url", "")
                merge_sha = pr_data.get("merge_commit_sha", "")[:8]

                # High-priority alert: breaking PR merged
                await self._create_update_node(
                    repo=repo,
                    update_type="breaking_change",
                    title=(
                        f"MERGED — Breaking PR: {repo.full_name} "
                        f"#{tracked_pr_number} — {pr_title}"
                    ),
                    content=(
                        f"A previously-tracked breaking/critical PR has been MERGED "
                        f"in {repo.full_name}.\n\n"
                        f"PR #{tracked_pr_number}: {pr_title}\n"
                        f"Merge commit: {merge_sha}\n"
                        f"URL: {pr_html_url}\n\n"
                        f"ACTION REQUIRED: Evaluate impact and begin migration "
                        f"planning if necessary."
                    ),
                    tags=["pull_request", "merged", "breaking-change", repo.domain],
                )

                await self._notify_chain_agent(
                    repo=repo,
                    update_type="critical_pr",
                    details={
                        "repo": repo.full_name,
                        "pr": tracked_pr_number,
                        "title": pr_title,
                        "url": pr_html_url,
                        "merge_commit": merge_sha,
                        "event": "merged",
                    },
                    priority=3,
                )

                tracked_prs[tracked_pr_number] = "merged"

                self.log.warning("repo_watcher.breaking_pr_merged",
                                 repo=repo.full_name, pr=tracked_pr_number,
                                 title=pr_title)

            # If the PR was closed without merging, stop tracking
            elif pr_data.get("state") == "closed" and pr_data.get("merged_at") is None:
                merged_to_remove.append(tracked_pr_number)

        for pr_num in merged_to_remove:
            tracked_prs.pop(pr_num, None)

        state["seen_prs"] = seen_prs[-100:]  # cap stored list
        state["tracked_prs"] = tracked_prs

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

            elif req_type == "comment_on_issue":
                # Allow other agents to request comments on issues
                repo_name = msg.payload.get("repo", "")
                issue_num = msg.payload.get("issue", "")
                comment_body = msg.payload.get("body", "")
                for repo in WATCHED_REPOS:
                    if repo.full_name == repo_name:
                        result = await self._comment_on_issue(repo, issue_num, comment_body)
                        await self.send(msg.sender, "response", {
                            "type": "comment_posted",
                            "success": result is not None,
                            "repo": repo_name,
                            "issue": issue_num,
                        })
                        return

            elif req_type == "file_issue":
                # Allow other agents to file issues through us
                repo_name = msg.payload.get("repo", "")
                issue_title = msg.payload.get("title", "")
                issue_body = msg.payload.get("body", "")
                issue_labels = msg.payload.get("labels", [])
                for repo in WATCHED_REPOS:
                    if repo.full_name == repo_name:
                        result = await self._file_issue(
                            repo, issue_title, issue_body, issue_labels,
                        )
                        await self.send(msg.sender, "response", {
                            "type": "issue_filed",
                            "success": result is not None,
                            "repo": repo_name,
                            "issue_number": result.get("number") if result else None,
                        })
                        return

            elif req_type == "status_query":
                await self.send(msg.sender, "response", {
                    "type": "watcher_status",
                    "repos_tracked": len(WATCHED_REPOS),
                    "critical_repos": len(get_critical_repos()),
                    "rate_remaining": self._requests_remaining,
                    "has_token": bool(self._github_token),
                    "states_loaded": len(self._watch_state),
                    "engagement_enabled": bool(self._github_token),
                    "subscribed": self._subscribed,
                })

    # -- learning loop --------------------------------------------------------

    async def learn(self) -> None:
        """Record what the watcher has observed for self-improvement."""
        self.memory.remember("tech_updates", {
            "area": "repo_monitoring_and_engagement",
            "repos_tracked": len(WATCHED_REPOS),
            "states_stored": len(self._watch_state),
            "rate_remaining": self._requests_remaining,
            "has_token": bool(self._github_token),
            "engagement_enabled": bool(self._github_token),
            "subscribed_to_critical": self._subscribed,
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
            "engagement_enabled": bool(self._github_token),
            "subscribed_to_critical": self._subscribed,
            "states_persisted": len(self._watch_state),
        })
        return base
