# Project Organization — Consolidation Plan

## The Vision
A fully autonomously running, self-healing, self-expanding, self-throttling
system of businesses — all orchestrated by evolving code with **hard outer
boundaries** and **inner freedom** to do what is needed and logical.

## Current Project Locations (Need Consolidation)

### 1. autono (this repo) — The Core System
- **Path**: This repository (`autono/`)
- **Contains**:
  - 13 autonomous Python agents (ChainArchitect, BridgeKeeper, etc.)
  - 6 manager agents (Throttle, Embed, Expansion, Research, Link, Lock)
  - 4 chain specialist agents (Cardano, Bitcoin, Night, Charms)
  - Links & Locks knowledge system
  - Sidechain infrastructure (consensus, bridge, state)
  - WALI wallet (TypeScript multi-chain wallet)

### 2. Cardano Agent System (Local Windows Machine)
- **Path**: `C:\Users\thisc\Documents\Projects\Ai\Cardano`
- **Contains**:
  - Agents at `agent\server\agents\` with system resource monitoring
  - Communication patterns for running on constrained systems
  - The original 85% resource throttle concept
- **ACTION**: Merge resource monitoring patterns into ThrottleManager
- **ACTION**: Port unique agent roles into the autono framework

### 3. WeBot Business System (Location TBD)
- **Contains**: Web business automation
- **ACTION**: Identify location, merge into autono as a service module

### 4. IDP Studio / Creator Tools (Location TBD)
- **Contains**: Creator economy tools, NFT minting
- **ACTION**: Identify location, integrate with CreatorStudio agent

### 5. Oracle Hosting Target
- **Goal**: Host the unified system on Oracle Cloud
- **ACTION**: Create deployment configs for Oracle infrastructure

## Consolidation Priority

1. **IMMEDIATE**: All concepts are now captured in this repo's architecture
2. **NEXT**: Locate all local Windows project directories
3. **THEN**: Port unique code/patterns from each into autono
4. **FINALLY**: Oracle deployment configuration

## Architecture After Consolidation

```
autono/                           # The unified system
├── autono/                       # Python core — agents, managers, knowledge
│   ├── agents/                   # 13 core + 6 managers + 4 chain specialists
│   ├── knowledge/                # Links & Locks brain
│   ├── core/                     # Agent base, message bus, autonomy engine
│   ├── sidechain/                # Consensus, bridge, state
│   └── services/                 # Orchestrator, API
├── wali-wallet/                  # TypeScript multi-chain wallet
├── webot/                        # (TO MERGE) Web business automation
├── idp-studio/                   # (TO MERGE) Creator tools
└── deploy/                       # Oracle Cloud configs
```

## Key Concepts Implemented

- **Links & Locks**: Deterministic reasoning system — JSON files beat LLM training
- **Managers**: Self-healing, self-expanding background processes
- **ThrottleManager**: Never exceed 85% system resources
- **mLocks**: Many paths to one truth (backward chaining)
- **Cascading Severance**: No ghost links, no dangling pointers
- **Night Chain Vault**: Knowledge graph encrypted and recoverable
- **Charms/BitcoinOS Bridge**: Cross-chain via ZK proofs, not wrapped tokens
