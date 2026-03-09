"""Cross-agent compatibility test harness.

Provides a mixin class that chain specialist agents can use to respond to
beta test alerts from the RepoWatcherAgent.  When the watcher detects a new
pre-release or breaking change, it sends a ``repo_beta_test_results`` message
to the relevant chain agent.  The mixin intercepts that message, runs all
registered compatibility checks, and reports the results back.

Usage::

    class MyChainAgent(CompatibilityTestMixin, AutonomousAgent):
        def __init__(self):
            super().__init__(...)
            self.register_compatibility_check(
                "owner/repo",
                "api_health",
                check_api_endpoint_exists("https://api.example.com/health"),
            )

        async def handle_message(self, msg):
            if msg.payload.get("type") == "repo_beta_test_results":
                await self.handle_beta_test_alert(msg)
                return
            ...
"""

from __future__ import annotations

import fnmatch
import re
from datetime import datetime, timezone
from typing import Any, Callable

import structlog

from autono.core.agent_base import Message

log = structlog.get_logger()

# Type alias for a check function: () -> dict with at least {"passed": bool}
CheckFn = Callable[[], dict[str, Any]]


# ---------------------------------------------------------------------------
# Built-in check generators
# ---------------------------------------------------------------------------

def check_api_endpoint_exists(url: str) -> CheckFn:
    """Return a check function that verifies an API endpoint still responds.

    The check attempts an HTTP GET and considers any 2xx or 3xx status a pass.
    Network errors or 4xx/5xx responses are treated as failures.
    """

    def _check() -> dict[str, Any]:
        try:
            import httpx  # noqa: delayed import to keep module lightweight

            with httpx.Client(timeout=10.0, follow_redirects=True) as client:
                resp = client.get(url)
                passed = 200 <= resp.status_code < 400
                return {
                    "passed": passed,
                    "status_code": resp.status_code,
                    "url": url,
                    "detail": (
                        f"Endpoint responded with {resp.status_code}"
                        if passed
                        else f"Endpoint returned {resp.status_code}"
                    ),
                }
        except Exception as exc:
            return {
                "passed": False,
                "url": url,
                "detail": f"Request failed: {exc}",
            }

    return _check


def check_dependency_version(package: str, min_version: str) -> CheckFn:
    """Return a check function that verifies a Python package meets a minimum version.

    Uses ``importlib.metadata`` so no subprocess is needed.
    """

    def _parse_version(v: str) -> tuple[int, ...]:
        """Rough semver parser — handles ``1.2.3``, ``1.2.3a1``, etc."""
        parts = re.split(r"[^0-9]+", v.strip())
        return tuple(int(p) for p in parts if p)

    def _check() -> dict[str, Any]:
        try:
            from importlib.metadata import version as pkg_version

            installed = pkg_version(package)
            installed_tuple = _parse_version(installed)
            required_tuple = _parse_version(min_version)
            passed = installed_tuple >= required_tuple
            return {
                "passed": passed,
                "package": package,
                "installed_version": installed,
                "required_min": min_version,
                "detail": (
                    f"{package} {installed} >= {min_version}"
                    if passed
                    else f"{package} {installed} < {min_version}"
                ),
            }
        except Exception as exc:
            return {
                "passed": False,
                "package": package,
                "required_min": min_version,
                "detail": f"Could not determine version: {exc}",
            }

    return _check


def check_config_key_exists(config_dict: dict[str, Any], key_path: str) -> CheckFn:
    """Return a check function that verifies a nested config key still exists.

    ``key_path`` uses dot-notation, e.g. ``"protocol.plutus.costModel"``.
    """

    def _check() -> dict[str, Any]:
        current: Any = config_dict
        parts = key_path.split(".")
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return {
                    "passed": False,
                    "key_path": key_path,
                    "detail": f"Key '{part}' not found at path '{key_path}'",
                }
        return {
            "passed": True,
            "key_path": key_path,
            "detail": f"Config key '{key_path}' exists",
        }

    return _check


# ---------------------------------------------------------------------------
# Mixin
# ---------------------------------------------------------------------------

class CompatibilityTestMixin:
    """Mixin for chain specialist agents to handle beta test compatibility checks.

    Chain agents populate ``_compatibility_checks`` via
    ``register_compatibility_check`` in their ``__init__``.  When
    ``handle_beta_test_alert`` is called (typically from ``handle_message``
    on a ``repo_beta_test_results`` payload), the mixin runs every check
    whose repo pattern matches and sends aggregated results back to
    ``RepoWatcherAgent``.
    """

    def _init_compatibility_checks(self) -> None:
        """Initialise the internal registry.  Called lazily."""
        if not hasattr(self, "_compatibility_checks"):
            # { repo_pattern: [ (check_name, check_fn), ... ] }
            self._compatibility_checks: dict[
                str, list[tuple[str, CheckFn]]
            ] = {}

    # -- public API -----------------------------------------------------------

    def register_compatibility_check(
        self,
        repo_pattern: str,
        check_name: str,
        check_fn: CheckFn,
    ) -> None:
        """Register a compatibility check for repos matching *repo_pattern*.

        Parameters
        ----------
        repo_pattern:
            A glob pattern matched against the full repo name
            (e.g. ``"IntersectMBO/*"`` or ``"charms-dev/charms"``).
        check_name:
            A human-readable label for the check.
        check_fn:
            A callable ``() -> dict`` that returns at least ``{"passed": bool}``.
        """
        self._init_compatibility_checks()
        self._compatibility_checks.setdefault(repo_pattern, []).append(
            (check_name, check_fn)
        )

    async def handle_beta_test_alert(self, msg: Message) -> None:
        """Process a ``repo_beta_test_results`` message from RepoWatcherAgent.

        Extracts repo metadata, runs applicable checks, and sends a
        ``compatibility_result`` response back to the watcher.
        """
        self._init_compatibility_checks()

        payload = msg.payload
        repo_name: str = payload.get("repo", "")
        tag: str = payload.get("tag", "")
        breaking_changes: list[str] = payload.get("breaking_changes", [])
        deprecations: list[str] = payload.get("deprecations", [])

        # Find checks whose pattern matches this repo
        applicable: list[tuple[str, CheckFn]] = []
        for pattern, checks in self._compatibility_checks.items():
            if fnmatch.fnmatch(repo_name, pattern):
                applicable.extend(checks)

        # Run every applicable check and collect results
        results: list[dict[str, Any]] = []
        all_passed = True
        for check_name, check_fn in applicable:
            try:
                outcome = check_fn()
            except Exception as exc:
                outcome = {
                    "passed": False,
                    "detail": f"Check raised an exception: {exc}",
                }
            outcome["check_name"] = check_name
            results.append(outcome)
            if not outcome.get("passed", False):
                all_passed = False

        # Build summary
        summary = {
            "repo": repo_name,
            "tag": tag,
            "breaking_changes": breaking_changes,
            "deprecations": deprecations,
            "checks_run": len(results),
            "all_passed": all_passed,
            "results": results,
            "agent": getattr(self, "name", "unknown"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Log the outcome
        _log = getattr(self, "log", log)
        _log.info(
            "compatibility.test_complete",
            repo=repo_name,
            tag=tag,
            checks_run=len(results),
            all_passed=all_passed,
        )

        # Remember the test in agent memory
        memory = getattr(self, "memory", None)
        if memory is not None:
            memory.remember("tech_updates", {
                "type": "compatibility_test",
                "repo": repo_name,
                "tag": tag,
                "all_passed": all_passed,
                "checks_run": len(results),
            })

        # Send results back to RepoWatcherAgent
        send = getattr(self, "send", None)
        if send is not None:
            await send("RepoWatcherAgent", "response", {
                "type": "compatibility_result",
                **summary,
            })
