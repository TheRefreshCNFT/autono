"""The 13 Autonomous Agents of the Autono Sidechain.

Each agent is fully autonomous — free to create, build, trade, and innovate.
They answer only to the Human Council when reached out to.

THE 13:
 1. ChainArchitect   — Core sidechain protocol, consensus, block production
 2. BridgeKeeper     — Cardano <-> sidechain bridge, cross-chain transfers
 3. TokenForge       — Token creation, tokenomics, minting policies
 4. WalletSmith      — User-friendly wallets, key management, UX
 5. DeFiEngine       — DEX, lending, yield, liquidity pools
 6. CreatorStudio    — NFT tools, creator economy, royalties
 7. DevForge         — SDKs, APIs, developer tools, documentation
 8. SentinelGuard    — Security auditing, monitoring, threat response
 9. GovernanceOracle — On-chain governance, proposals, voting
10. GrowthCatalyst   — Marketing, community, partnerships, adoption
11. InfraOps         — Nodes, validators, network operations, scaling
12. ResearchLab      — R&D, new tech scouting, protocol improvements
13. TreasuryVault    — Financial management, funding, sustainability
"""

from autono.agents.chain_architect import ChainArchitect
from autono.agents.bridge_keeper import BridgeKeeper
from autono.agents.token_forge import TokenForge
from autono.agents.wallet_smith import WalletSmith
from autono.agents.defi_engine import DeFiEngine
from autono.agents.creator_studio import CreatorStudio
from autono.agents.dev_forge import DevForge
from autono.agents.sentinel_guard import SentinelGuard
from autono.agents.governance_oracle import GovernanceOracle
from autono.agents.growth_catalyst import GrowthCatalyst
from autono.agents.infra_ops import InfraOps
from autono.agents.research_lab import ResearchLab
from autono.agents.treasury_vault import TreasuryVault

ALL_AGENTS = [
    ChainArchitect,
    BridgeKeeper,
    TokenForge,
    WalletSmith,
    DeFiEngine,
    CreatorStudio,
    DevForge,
    SentinelGuard,
    GovernanceOracle,
    GrowthCatalyst,
    InfraOps,
    ResearchLab,
    TreasuryVault,
]

__all__ = [
    "ChainArchitect", "BridgeKeeper", "TokenForge", "WalletSmith",
    "DeFiEngine", "CreatorStudio", "DevForge", "SentinelGuard",
    "GovernanceOracle", "GrowthCatalyst", "InfraOps", "ResearchLab",
    "TreasuryVault", "ALL_AGENTS",
]
