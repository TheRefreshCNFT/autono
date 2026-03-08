# Autono

13 Autonomous Agents for a Cardano Sidechain — faster, cheaper, user-friendly blockchain.

## Agents

| Agent | Role |
|-------|------|
| **Bridge Keeper** | Cross-chain asset transfers between Cardano mainchain and sidechain |
| **Chain Architect** | Sidechain configuration, genesis, and network topology |
| **Creator Studio** | NFT minting, metadata, and marketplace integration |
| **DeFi Engine** | Liquidity pools, swaps, and yield strategies |
| **Dev Forge** | Smart contract compilation, deployment, and testing |
| **Governance Oracle** | On-chain proposals, voting, and treasury governance |
| **Growth Catalyst** | Network adoption metrics, incentives, and partnerships |
| **Infra Ops** | Node management, monitoring, and infrastructure scaling |
| **Research Lab** | Protocol research, benchmarking, and optimization |
| **Sentinel Guard** | Security monitoring, threat detection, and incident response |
| **Token Forge** | Native token creation, policy management, and distribution |
| **Treasury Vault** | Treasury management, budgeting, and fund allocation |
| **Wallet Smith** | Wallet generation, key management, and transaction signing |

## Architecture

```
autono/
  agents/       # 13 autonomous agent implementations
  core/         # Agent base, message bus, council, autonomy engine
  services/     # Orchestrator for multi-agent coordination
  sidechain/    # Block production, consensus, bridge, state management
  cli.py        # Command-line interface
config/         # Default configuration (TOML)
tests/          # Unit and integration tests
```

## Quick Start

```bash
pip install -e ".[dev]"
autono --help
```

## Development

```bash
pip install -e ".[dev]"
pytest
ruff check .
mypy autono/
```

## License

MIT
