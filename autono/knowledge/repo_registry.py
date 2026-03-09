"""Official Repository Registry — canonical sources of truth.

Every repository listed here is monitored by the RepoWatcherAgent.
Only OFFICIAL repositories. Community forks and unofficial repos are excluded.

Monitoring includes:
- Releases (tags, changelogs)
- Issues (breaking changes, security advisories)
- Pull Requests (upcoming features, betas)
- Commits to main/master branch
- CI/CD status
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class WatchPriority(str, Enum):
    CRITICAL = "critical"    # Core protocol — every change matters
    HIGH = "high"            # Key dependencies — breaking changes matter
    MEDIUM = "medium"        # Tools/SDKs — new features matter
    LOW = "low"              # Reference/docs — periodic check


class WatchScope(str, Enum):
    RELEASES = "releases"
    ISSUES = "issues"
    PULL_REQUESTS = "pull_requests"
    COMMITS = "commits"
    SECURITY = "security"
    ALL = "all"


@dataclass
class WatchedRepo:
    owner: str
    repo: str
    domain: str          # cardano, bitcoin, charms, bitcoinos, night_chain
    subdomain: str = ""
    priority: WatchPriority = WatchPriority.MEDIUM
    watch_scopes: list[WatchScope] = field(default_factory=lambda: [WatchScope.RELEASES])
    branch: str = "main"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    # How often to check (seconds)
    poll_interval: int = 3600  # 1 hour default
    # Track what we've already seen
    last_seen_release: str = ""
    last_seen_commit: str = ""
    last_checked: str = ""

    @property
    def full_name(self) -> str:
        return f"{self.owner}/{self.repo}"

    @property
    def github_url(self) -> str:
        return f"https://github.com/{self.owner}/{self.repo}"

    @property
    def api_url(self) -> str:
        return f"https://api.github.com/repos/{self.owner}/{self.repo}"


# ---------------------------------------------------------------------------
# CARDANO REPOSITORIES
# ---------------------------------------------------------------------------

_CARDANO_CRITICAL: list[WatchedRepo] = [
    WatchedRepo(
        owner="IntersectMBO",
        repo="cardano-node",
        domain="cardano",
        subdomain="core",
        priority=WatchPriority.CRITICAL,
        watch_scopes=[WatchScope.ALL],
        branch="master",
        description="The Cardano full node — consensus, networking, block production",
        tags=["node", "consensus", "haskell", "core"],
        poll_interval=1800,  # 30 min
    ),
    WatchedRepo(
        owner="IntersectMBO",
        repo="cardano-cli",
        domain="cardano",
        subdomain="core",
        priority=WatchPriority.CRITICAL,
        watch_scopes=[WatchScope.ALL],
        branch="main",
        description="Official Cardano CLI tools for node interaction",
        tags=["cli", "tools", "core"],
        poll_interval=1800,
    ),
    WatchedRepo(
        owner="IntersectMBO",
        repo="cardano-ledger",
        domain="cardano",
        subdomain="core",
        priority=WatchPriority.CRITICAL,
        watch_scopes=[WatchScope.ALL],
        branch="master",
        description="Cardano ledger rules — validation, fees, protocol parameters",
        tags=["ledger", "validation", "protocol", "core"],
        poll_interval=1800,
    ),
    WatchedRepo(
        owner="IntersectMBO",
        repo="plutus",
        domain="cardano",
        subdomain="smart_contracts",
        priority=WatchPriority.CRITICAL,
        watch_scopes=[WatchScope.ALL],
        branch="master",
        description="Plutus smart contract platform — PlutusTx, Plutus Core",
        tags=["plutus", "smart-contract", "haskell", "core"],
        poll_interval=1800,
    ),
]

_CARDANO_HIGH: list[WatchedRepo] = [
    WatchedRepo(
        owner="IntersectMBO",
        repo="cardano-db-sync",
        domain="cardano",
        subdomain="indexer",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES, WatchScope.SECURITY],
        branch="master",
        description="Cardano chain indexer — PostgreSQL sync of on-chain data",
        tags=["indexer", "database", "sync", "postgresql"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="CardanoSolutions",
        repo="ogmios",
        domain="cardano",
        subdomain="bridge",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES, WatchScope.SECURITY],
        branch="master",
        description="WebSocket JSON/RPC bridge to cardano-node",
        tags=["websocket", "bridge", "api", "ogmios"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="cardano-foundation",
        repo="CIPs",
        domain="cardano",
        subdomain="standards",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.PULL_REQUESTS, WatchScope.COMMITS],
        branch="master",
        description="Cardano Improvement Proposals — community standards",
        tags=["cip", "standards", "governance", "proposals"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="blockfrost",
        repo="blockfrost-backend-rpc",
        domain="cardano",
        subdomain="api",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="master",
        description="Blockfrost API backend RPC service",
        tags=["blockfrost", "api", "backend", "rpc"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="blockfrost",
        repo="openapi",
        domain="cardano",
        subdomain="api",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.RELEASES, WatchScope.COMMITS],
        branch="master",
        description="Blockfrost OpenAPI specification",
        tags=["blockfrost", "openapi", "spec", "api"],
        poll_interval=3600,
    ),
]

_CARDANO_MEDIUM: list[WatchedRepo] = [
    WatchedRepo(
        owner="MeshJS",
        repo="mesh",
        domain="cardano",
        subdomain="sdk",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="main",
        description="MeshJS — JavaScript/TypeScript SDK for Cardano dApps",
        tags=["meshjs", "javascript", "typescript", "sdk", "dapp"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="OpShin",
        repo="opshin",
        domain="cardano",
        subdomain="smart_contracts",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="main",
        description="OpShin — Python smart contracts for Cardano (compiles to Plutus Core)",
        tags=["opshin", "python", "smart-contract", "plutus"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="Hyperion-BT",
        repo="helios",
        domain="cardano",
        subdomain="smart_contracts",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="main",
        description="Helios — TypeScript/JavaScript smart contract toolkit for Cardano",
        tags=["helios", "typescript", "javascript", "smart-contract"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="aiken-lang",
        repo="aiken",
        domain="cardano",
        subdomain="smart_contracts",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="main",
        description="Aiken — modern smart contract language for Cardano",
        tags=["aiken", "smart-contract", "language"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="spacebudz",
        repo="lucid",
        domain="cardano",
        subdomain="sdk",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="main",
        description="Lucid — TypeScript SDK for Cardano (lucid-evolution)",
        tags=["lucid", "typescript", "sdk", "dapp"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="blinklabs-io",
        repo="gouroboros",
        domain="cardano",
        subdomain="sdk",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="main",
        description="Gouroboros — Go implementation of the Cardano Ouroboros protocol",
        tags=["go", "ouroboros", "protocol", "library"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="cardano-foundation",
        repo="cardano-wallet",
        domain="cardano",
        subdomain="wallet",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES, WatchScope.SECURITY],
        branch="master",
        description="Cardano wallet backend — HTTP API for wallet operations",
        tags=["wallet", "backend", "api", "haskell"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="koios-official",
        repo="koios-artifacts",
        domain="cardano",
        subdomain="api",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.COMMITS],
        branch="main",
        description="Koios API artifacts — decentralized Cardano API",
        tags=["koios", "api", "decentralized", "query"],
        poll_interval=3600,
    ),
]

_CARDANO_LOW: list[WatchedRepo] = [
    WatchedRepo(
        owner="IntersectMBO",
        repo="cardano-haskell-packages",
        domain="cardano",
        subdomain="packages",
        priority=WatchPriority.LOW,
        watch_scopes=[WatchScope.RELEASES],
        branch="main",
        description="Cardano Haskell package repository (CHaP)",
        tags=["haskell", "packages", "chap", "dependencies"],
        poll_interval=86400,  # daily
    ),
    WatchedRepo(
        owner="IntersectMBO",
        repo="ouroboros-network",
        domain="cardano",
        subdomain="core",
        priority=WatchPriority.LOW,
        watch_scopes=[WatchScope.RELEASES, WatchScope.COMMITS],
        branch="master",
        description="Ouroboros consensus and networking protocols",
        tags=["ouroboros", "consensus", "networking", "protocol"],
        poll_interval=86400,
    ),
]

# ---------------------------------------------------------------------------
# BITCOIN REPOSITORIES
# ---------------------------------------------------------------------------

_BITCOIN_CRITICAL: list[WatchedRepo] = [
    WatchedRepo(
        owner="bitcoin",
        repo="bitcoin",
        domain="bitcoin",
        subdomain="core",
        priority=WatchPriority.CRITICAL,
        watch_scopes=[WatchScope.ALL],
        branch="master",
        description="Bitcoin Core — the reference implementation",
        tags=["core", "node", "consensus", "c++"],
        poll_interval=1800,
    ),
]

_BITCOIN_HIGH: list[WatchedRepo] = [
    WatchedRepo(
        owner="bitcoin",
        repo="bips",
        domain="bitcoin",
        subdomain="standards",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.PULL_REQUESTS, WatchScope.COMMITS],
        branch="master",
        description="Bitcoin Improvement Proposals — protocol standards",
        tags=["bip", "standards", "proposals"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="bitcoinjs",
        repo="bitcoinjs-lib",
        domain="bitcoin",
        subdomain="sdk",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES, WatchScope.SECURITY],
        branch="master",
        description="bitcoinjs-lib — JavaScript Bitcoin library",
        tags=["javascript", "library", "sdk", "transactions"],
        poll_interval=3600,
    ),
]

_BITCOIN_MEDIUM: list[WatchedRepo] = [
    WatchedRepo(
        owner="mempool",
        repo="mempool",
        domain="bitcoin",
        subdomain="explorer",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="master",
        description="mempool.space — Bitcoin mempool visualizer and explorer",
        tags=["mempool", "explorer", "visualization"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="Blockstream",
        repo="esplora",
        domain="bitcoin",
        subdomain="explorer",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="master",
        description="Esplora — Blockstream block explorer backend API",
        tags=["explorer", "api", "blockstream"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="rust-bitcoin",
        repo="rust-bitcoin",
        domain="bitcoin",
        subdomain="sdk",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="master",
        description="rust-bitcoin — Rust Bitcoin library",
        tags=["rust", "library", "bitcoin"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="btcsuite",
        repo="btcd",
        domain="bitcoin",
        subdomain="node",
        priority=WatchPriority.MEDIUM,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES],
        branch="master",
        description="btcd — Go full node implementation of Bitcoin",
        tags=["go", "node", "full-node"],
        poll_interval=3600,
    ),
]

# ---------------------------------------------------------------------------
# CHARMS REPOSITORIES
# ---------------------------------------------------------------------------

_CHARMS_CRITICAL: list[WatchedRepo] = [
    WatchedRepo(
        owner="proven-network",
        repo="charms",
        domain="charms",
        subdomain="core",
        priority=WatchPriority.CRITICAL,
        watch_scopes=[WatchScope.ALL],
        branch="main",
        description="Charms — programmable tokens on Bitcoin via spells",
        tags=["charms", "spells", "bitcoin", "tokens", "zk"],
        poll_interval=1800,
    ),
]

_CHARMS_HIGH: list[WatchedRepo] = [
    WatchedRepo(
        owner="proven-network",
        repo="proven-node",
        domain="charms",
        subdomain="node",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES, WatchScope.SECURITY],
        branch="main",
        description="Proven node — runtime for Charms spell verification",
        tags=["proven", "node", "verification", "runtime"],
        poll_interval=3600,
    ),
]

# ---------------------------------------------------------------------------
# BITCOINOS REPOSITORIES
# ---------------------------------------------------------------------------

_BITCOINOS_CRITICAL: list[WatchedRepo] = [
    WatchedRepo(
        owner="BitcoinOS-Labs",
        repo="BitcoinOS",
        domain="bitcoinos",
        subdomain="core",
        priority=WatchPriority.CRITICAL,
        watch_scopes=[WatchScope.ALL],
        branch="main",
        description="BitcoinOS — operating system layer for Bitcoin (main repos TBD)",
        tags=["bitcoinos", "layer", "core"],
        poll_interval=1800,
    ),
]

# ---------------------------------------------------------------------------
# MIDNIGHT / NIGHT CHAIN REPOSITORIES
# ---------------------------------------------------------------------------

_NIGHT_CHAIN_HIGH: list[WatchedRepo] = [
    WatchedRepo(
        owner="input-output-hk",
        repo="partner-chains",
        domain="night_chain",
        subdomain="framework",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.RELEASES, WatchScope.ISSUES, WatchScope.COMMITS],
        branch="main",
        description="IOG partner chains framework — substrate-based sidechains for Cardano",
        tags=["partner-chains", "sidechain", "substrate", "iog"],
        poll_interval=3600,
    ),
    WatchedRepo(
        owner="midnight-network",
        repo="midnight-core",
        domain="night_chain",
        subdomain="core",
        priority=WatchPriority.HIGH,
        watch_scopes=[WatchScope.ALL],
        branch="main",
        description="Midnight network core (if public) — data-protection blockchain",
        tags=["midnight", "night-chain", "privacy", "zk"],
        poll_interval=3600,
    ),
]


# ---------------------------------------------------------------------------
# MASTER REGISTRY
# ---------------------------------------------------------------------------

WATCHED_REPOS: list[WatchedRepo] = [
    # Cardano
    *_CARDANO_CRITICAL,
    *_CARDANO_HIGH,
    *_CARDANO_MEDIUM,
    *_CARDANO_LOW,
    # Bitcoin
    *_BITCOIN_CRITICAL,
    *_BITCOIN_HIGH,
    *_BITCOIN_MEDIUM,
    # Charms
    *_CHARMS_CRITICAL,
    *_CHARMS_HIGH,
    # BitcoinOS
    *_BITCOINOS_CRITICAL,
    # Night Chain / Midnight
    *_NIGHT_CHAIN_HIGH,
]


# ---------------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------------

def get_repos_by_domain(domain: str) -> list[WatchedRepo]:
    """Return all watched repos for a given domain (e.g. 'cardano', 'bitcoin')."""
    return [r for r in WATCHED_REPOS if r.domain == domain]


def get_repos_by_priority(priority: WatchPriority) -> list[WatchedRepo]:
    """Return all watched repos at a given priority level."""
    return [r for r in WATCHED_REPOS if r.priority == priority]


def get_critical_repos() -> list[WatchedRepo]:
    """Return all CRITICAL priority repos — these are checked most frequently."""
    return get_repos_by_priority(WatchPriority.CRITICAL)


def get_all_repos() -> list[WatchedRepo]:
    """Return every repo in the registry."""
    return list(WATCHED_REPOS)
