"""Lightweight GitHub webhook receiver for real-time event delivery.

Instead of relying solely on polling (every 5 minutes), this server lets
GitHub push events directly to the RepoWatcherAgent the moment they happen.

Configure a GitHub webhook to point at ``http://<host>:<port>/github/webhook``
with content type ``application/json``.  Set ``GITHUB_WEBHOOK_SECRET`` to the
same secret you entered in the GitHub UI so payloads are authenticated.

Environment variables:
    AUTONO_WEBHOOK_PORT   — port to listen on (default 8099)
    GITHUB_WEBHOOK_SECRET — HMAC secret for signature validation (optional)
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

import structlog
from aiohttp import web

from autono.core.agent_base import Message

log = structlog.get_logger()

_DEFAULT_PORT = 8099
_REPO_WATCHER_AGENT = "RepoWatcherAgent"

# Labels that trigger a force_check on issues events
_ALERT_LABELS = frozenset({
    "breaking", "breaking-change", "security", "vulnerability", "cve",
})


class WebhookReceiver:
    """Async HTTP server that receives GitHub webhook payloads and forwards
    them to the RepoWatcherAgent through the shared message bus.

    Parameters
    ----------
    bus:
        The :class:`~autono.core.message_bus.MessageBus` instance shared by
        all agents.  Used to deliver messages into agent inboxes.
    port:
        TCP port to bind to.  Falls back to ``AUTONO_WEBHOOK_PORT`` env var,
        then to 8099.
    """

    def __init__(self, bus: Any, port: int | None = None) -> None:
        self._bus = bus
        self._port = port or int(os.environ.get("AUTONO_WEBHOOK_PORT", _DEFAULT_PORT))
        self._secret: str = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
        self._app = web.Application()
        self._app.router.add_post("/github/webhook", self._handle_webhook)
        self._runner: web.AppRunner | None = None

    # -- public lifecycle -----------------------------------------------------

    async def start(self) -> None:
        """Start listening for incoming webhooks."""
        if not self._secret:
            log.warning(
                "webhook.no_secret_configured",
                hint="Set GITHUB_WEBHOOK_SECRET to validate payloads",
            )

        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, "0.0.0.0", self._port)
        await site.start()
        log.info("webhook.started", port=self._port)

    async def stop(self) -> None:
        """Gracefully shut down the HTTP server."""
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
        log.info("webhook.stopped")

    # -- signature verification -----------------------------------------------

    @staticmethod
    def _verify_signature(payload_body: bytes, signature: str, secret: str) -> bool:
        """Validate ``X-Hub-Signature-256`` using HMAC-SHA256.

        Parameters
        ----------
        payload_body:
            Raw request body bytes.
        signature:
            Value of the ``X-Hub-Signature-256`` header
            (e.g. ``sha256=abcdef...``).
        secret:
            The shared webhook secret.

        Returns
        -------
        bool
            ``True`` if the signature is valid, ``False`` otherwise.
        """
        if not signature.startswith("sha256="):
            return False
        expected = hmac.new(
            secret.encode("utf-8"),
            payload_body,
            hashlib.sha256,
        ).hexdigest()
        received = signature.removeprefix("sha256=")
        return hmac.compare_digest(expected, received)

    # -- request handler ------------------------------------------------------

    async def _handle_webhook(self, request: web.Request) -> web.Response:
        """Route an incoming GitHub webhook to the appropriate handler."""
        body = await request.read()

        # --- signature check ---
        if self._secret:
            sig = request.headers.get("X-Hub-Signature-256", "")
            if not self._verify_signature(body, sig, self._secret):
                log.warning("webhook.bad_signature")
                return web.Response(status=400, text="Bad signature")

        # --- parse event type ---
        event_type = request.headers.get("X-GitHub-Event", "")
        if not event_type:
            return web.Response(status=400, text="Missing X-GitHub-Event header")

        try:
            payload: dict[str, Any] = await request.json()
        except Exception:
            return web.Response(status=400, text="Invalid JSON")

        # --- dispatch ---
        handler = {
            "push": self._handle_push,
            "release": self._handle_release,
            "issues": self._handle_issues,
            "pull_request": self._handle_pull_request,
            "security_advisory": self._handle_security_advisory,
        }.get(event_type)

        if handler is None:
            log.debug("webhook.unhandled_event", event=event_type)
            return web.Response(status=202, text="Event type not handled")

        await handler(payload)
        return web.Response(status=200, text="OK")

    # -- event handlers -------------------------------------------------------

    async def _handle_push(self, payload: dict[str, Any]) -> None:
        repo = payload.get("repository", {}).get("full_name", "")
        ref = payload.get("ref", "")
        branch = ref.removeprefix("refs/heads/")
        commits = [
            {
                "sha": c.get("id", "")[:8],
                "message": c.get("message", "").split("\n", 1)[0],
                "author": c.get("author", {}).get("name", "unknown"),
            }
            for c in payload.get("commits", [])
        ]

        log.info("webhook.push", repo=repo, branch=branch, commits=len(commits))

        msg = Message(
            sender="WebhookReceiver",
            recipient=_REPO_WATCHER_AGENT,
            kind="request",
            payload={
                "type": "force_check",
                "repo": repo,
                "trigger": "webhook_push",
                "branch": branch,
                "commits": commits,
            },
            priority=2,
        )
        await self._bus._deliver(msg)

    async def _handle_release(self, payload: dict[str, Any]) -> None:
        release = payload.get("release", {})
        repo = payload.get("repository", {}).get("full_name", "")
        tag = release.get("tag_name", "")
        prerelease = release.get("prerelease", False)

        log.info("webhook.release", repo=repo, tag=tag, prerelease=prerelease)

        msg = Message(
            sender="WebhookReceiver",
            recipient=_REPO_WATCHER_AGENT,
            kind="request",
            payload={
                "type": "force_check",
                "repo": repo,
                "trigger": "webhook_release",
                "tag": tag,
                "prerelease": prerelease,
            },
            priority=2,
        )
        await self._bus._deliver(msg)

    async def _handle_issues(self, payload: dict[str, Any]) -> None:
        issue = payload.get("issue", {})
        repo = payload.get("repository", {}).get("full_name", "")
        issue_number = issue.get("number", 0)
        labels = [lbl.get("name", "").lower() for lbl in issue.get("labels", [])]

        # Only queue a force_check when labels match breaking/security
        matching = _ALERT_LABELS & set(labels)
        if not matching:
            log.debug("webhook.issues_skipped", repo=repo, issue=issue_number)
            return

        log.info(
            "webhook.issues",
            repo=repo,
            issue=issue_number,
            matching_labels=sorted(matching),
        )

        msg = Message(
            sender="WebhookReceiver",
            recipient=_REPO_WATCHER_AGENT,
            kind="request",
            payload={
                "type": "force_check",
                "repo": repo,
                "trigger": "webhook_issue",
                "issue_number": issue_number,
                "labels": labels,
            },
            priority=2,
        )
        await self._bus._deliver(msg)

    async def _handle_pull_request(self, payload: dict[str, Any]) -> None:
        pr = payload.get("pull_request", {})
        repo = payload.get("repository", {}).get("full_name", "")
        pr_number = pr.get("number", 0)
        action = payload.get("action", "")
        merged = pr.get("merged", False)
        labels = [lbl.get("name", "").lower() for lbl in pr.get("labels", [])]

        effective_action = "merged" if (action == "closed" and merged) else action

        log.info(
            "webhook.pull_request",
            repo=repo,
            pr=pr_number,
            action=effective_action,
        )

        msg = Message(
            sender="WebhookReceiver",
            recipient=_REPO_WATCHER_AGENT,
            kind="request",
            payload={
                "type": "force_check",
                "repo": repo,
                "trigger": "webhook_pull_request",
                "pr_number": pr_number,
                "action": effective_action,
                "labels": labels,
            },
            priority=2,
        )
        await self._bus._deliver(msg)

    async def _handle_security_advisory(self, payload: dict[str, Any]) -> None:
        advisory = payload.get("security_advisory", {})
        summary = advisory.get("summary", "")
        severity = advisory.get("severity", "unknown")
        ghsa_id = advisory.get("ghsa_id", "")
        references = [
            ref.get("url", "") for ref in advisory.get("references", [])
        ]

        log.warning(
            "webhook.security_advisory",
            ghsa_id=ghsa_id,
            severity=severity,
            summary=summary[:120],
        )

        # Broadcast to ALL agents — security advisories are critical
        msg = Message(
            sender="WebhookReceiver",
            recipient="broadcast",
            kind="alert",
            payload={
                "type": "security_advisory",
                "trigger": "webhook_security_advisory",
                "ghsa_id": ghsa_id,
                "severity": severity,
                "summary": summary,
                "references": references,
            },
            priority=3,
        )
        await self._bus._deliver(msg)
