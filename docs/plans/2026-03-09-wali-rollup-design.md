# Wali Rollup Design

**Date:** 2026-03-09
**Status:** Approved design, pending research agent validation
**Author:** Ian + Claude (collaborative brainstorm)

---

## What Wali Is

Wali is an AI-powered multi-chain wallet. It connects to Cardano, Bitcoin, and Night Chain like any other wallet, but uses AI agents to optimize every transaction for minimum cost.

Behind the scenes, Wali uses a rollup — a batching layer that collects transactions off-chain and periodically settles compressed proofs on Cardano L1. Users see a normal wallet. The rollup is invisible infrastructure.

**Wali is a character agent** inside the wallet. It talks to users, knows their patterns, suggests optimizations. "Gas is cheap right now, want me to batch those 3 pending transfers?" Every other wallet is a dumb tool. Wali is smart.

### Product tiers

- **Wali Lite** — Chrome extension, mobile app, desktop. Keys stay on device. Connects to any Wali Full node. Has a local Wali agent for UX and suggestions. Zero infrastructure.
- **Wali Full** — Server node running the rollup engine + full AI agent orchestration (25 agents). Knowledge graph, self-healing, learning. Anyone can run one on cheap hardware.

---

## Architecture

```
User → Wali Lite (signs locally) → Wali Full node → Rollup Engine → Cardano L1
```

Wali Full node internals:
- **Rollup Engine** — compiled binary, tiny footprint. Transaction validation, state tree (merkle), batch builder, P2P sync with other Full nodes.
- **AI Agent Layer** — nullclaw gateway, 25-agent orchestration, knowledge graph, local Ollama fallback. The brains that optimize, heal, learn.
- **Chain Connectors** — Blockfrost (Cardano), Bitcoin RPC, Night Chain.
- **Storage** — State DB (SQLite or LevelDB), knowledge store (JSON).

---

## Transaction Model

### Three paths

| Scenario | What happens | Cost | Speed |
|----------|-------------|------|-------|
| Wali → Wali | State update in rollup only | Near zero (share of batch settlement) | ~100ms |
| Wali → External wallet | Agent builds optimal L1 tx | ~170k lovelace (optimized) | ~20-40s (L1) |
| External → Wali | Detected on L1, credited in rollup | 0 (sender paid L1 fee) | ~20-40s + confirmation |

### Batch settlement cycle

Transactions accumulate in rollup state. Settlement triggers on whichever comes first:
- **Time trigger:** Every 10 minutes (adjustable by agents based on traffic)
- **Count trigger:** Every 100 transactions
- **Emergency:** Any user can force-settle immediately (pays full L1 fee)

Each batch settlement submits ONE transaction to Cardano L1 containing:
- New state root (merkle hash of all account balances)
- Proof covering all transactions in the batch
- Any withdrawal requests

**Cost math:** 50 rollup transactions settled in one L1 tx costing ~300k lovelace = ~6k lovelace per user. That's 97% cheaper than Vespr's 200k fee.

### Key insight

Two Wali users transacting never touch L1 at all until exit. The more users on Wali, the cheaper per-user cost gets. Network effect drives adoption which drives cost down further.

---

## AUTO Token Economics

### Purpose

AUTO is a pure utility token. It is earned by running Full nodes and spent on transaction fee discounts. It is never sold by the project. No ICO, no token sale, no promises of returns.

### Three phases

**Phase 1: Bootstrap (early adoption)**
- Genesis supply of AUTO exists in an internal system pool
- Users do NOT need AUTO — system covers rollup costs from the pool
- Full nodes earn AUTO rewards based on uptime and efficiency metrics
- User pitch: "It's just cheaper. Try it."

**Phase 2: Transition (pool depleting)**
- Internal AUTO pool running low
- Users start needing AUTO for cheap rollup transaction rates
- Can always use L1 path without AUTO (normal Cardano fees)
- AUTO has organic demand — node operators earned it, users want it for savings

**Phase 3: Sustaining (pool empty)**
- Users hold AUTO for access to cheap rollup transactions
- Each cycle: burn 25%, distribute 75% to Full node operators
- Deflationary — AUTO gets scarcer over time
- Node operators incentivized by ongoing rewards
- Users incentivized by ongoing savings vs L1

### Research needed (for research agents)

- Total genesis supply — how much AUTO exists?
- Emission curve — depletion rate of internal pool
- Burn/distribute ratio modeling (25/75 is starting point)
- AUTO representation: CNT on Cardano L1 AND internal rollup token
- Utility token compliance structures that have held up legally

### Hard constraint

AUTO must remain a pure utility token with no investment characteristics. Structure must avoid Howey test classification. Research agents must flag any design choice that creates compliance risk.

---

## Bridge (Security-Critical)

### Deposit (ADA to Wali rollup)

1. User sends ADA to bridge smart contract on Cardano L1
2. Smart contract locks the ADA
3. Wali Full nodes detect the lock (via Blockfrost)
4. Rollup credits user's account with equivalent ADA
5. User sees ADA in Wali

### Withdrawal (Wali rollup to Cardano L1)

1. User requests withdrawal in Wali
2. Rollup burns ADA from user's rollup account
3. Next batch settlement includes withdrawal proof
4. Smart contract verifies proof, unlocks ADA to user's L1 address

### Force exit (emergency, trustless)

Any user can exit directly to L1 without Full node cooperation:
1. User submits merkle proof of their balance to the smart contract
2. Contract verifies against latest posted state root
3. ADA unlocked directly to user

This is non-negotiable. No one can trap user funds.

### Implementation

- Smart contract language: Opshin (Python) or Helios (JavaScript-like). Both compile to UPLC. Research agents evaluate which is better for bridge contracts.
- The bridge contract is the ONE component that requires professional security audit before mainnet. This is a hard gate — no launch without audit.

### Research needed

- Optimistic vs ZK proof verification on Cardano (Plutus/UPLC constraints)
- Existing bridge patterns on Cardano (SundaeSwap, Minswap, WingRiders)
- Opshin vs Helios for bridge contract complexity
- Mithril state proof integration for L1 verification
- Challenge period design (optimistic) or proof generation cost (ZK)

---

## Node Architecture

### Hardware requirements

| Tier | Specs | Cost |
|------|-------|------|
| Wali Full (with AI) | 8GB RAM, modern CPU | ~$15-30/month VPS or old laptop |
| Wali Full (rollup only) | 2GB RAM, any CPU | Raspberry Pi, ~$5/month |
| Wali Lite | Phone, browser | Zero |

### Self-healing

- Heartbeat every 30s between Full nodes
- 3 missed heartbeats → neighbors flag the node
- Local agent restarts rollup engine if crash detected
- Network routes around dead nodes — no halt, no downtime
- Returning nodes sync state from peers automatically
- No user interaction required

### Genesis and equality

- Initial group of Full nodes forms the genesis set
- Once live, all Full nodes are equal — no special privileges for genesis nodes
- The chain runs one way — no straying from protocol rules
- Nodes crash, that's expected. Can't break the network. Chain never halts.

---

## Core Mission Update

Add to CORE_MISSION in autonomy.py:

> "Security is never sacrificed for cost. As cheap as securely possible, never cheaper than safely possible. Every optimization must pass security review before deployment."

---

## What Already Exists in Codebase (Honest Assessment)

| Component | File | Status |
|-----------|------|--------|
| Consensus (OuroborosTurbo) | sidechain/consensus.py | Working data structures, leader selection, slashing. No networking. |
| Block production | sidechain/block.py | Working in-memory chain. No persistence, no P2P. |
| State manager | sidechain/state.py | Working hybrid UTXO+account. No merkle proofs. |
| Bridge protocol | sidechain/bridge.py | Lifecycle correct. No smart contract, no real crypto. |
| 25 agents | agents/* | All load, all mission-gated. Operational. |
| Knowledge graph | knowledge/* | 202 nodes, 34 locks. Working. |
| Wali extension | (separate repo) | Chrome extension connects. Not yet functional wallet. |
| Mission enforcement | core/autonomy.py | Multi-chain cost targets, mission_gate on 14 agents. |

**Honest: ~5% of the rollup is built.** The agent infrastructure is strong. The rollup engine, bridge contract, P2P layer, persistence, and real cryptography are all ahead.

---

## Research Agent Work Orders

These are the questions the expert engineer agents must investigate before implementation begins:

### RO-1: Rollup Architecture for Cardano
- Compare optimistic vs ZK rollup approaches on Cardano's eUTXO model
- Analyze Polygon, Arbitrum, Optimism architectures — what applies, what doesn't
- Cardano Partner Chains (Substrate) — is this a better base than custom?
- Fee models: how do existing rollups calculate per-tx cost?
- Batch settlement: optimal frequency and size for Cardano's 20s block time

### RO-2: Bridge Contract Design
- Opshin vs Helios for bridge validator scripts
- Existing Cardano bridge patterns (survey DEX contracts)
- Force exit mechanism on eUTXO (different from account-model chains)
- State root posting: inline datum vs reference scripts
- Estimated bridge contract size and execution cost

### RO-3: AUTO Token Structure
- Utility token frameworks that avoid securities classification
- Emission and depletion curve modeling
- Burn/distribute ratio optimization
- Token representation: CNT on L1 + rollup internal
- Comparable projects: BNB, MATIC utility token models

### RO-4: P2P and Networking
- Lightweight P2P protocol for rollup state sync
- libp2p vs custom protocol for Wali Full nodes
- State sync: full sync vs checkpoint-based for rejoining nodes
- Gossip protocol for transaction propagation

### RO-5: Security Model
- What's the minimum viable security for a Cardano rollup?
- Where is the security line we cannot cross?
- Threat model: malicious sequencer, malicious Full node, network partition
- Audit requirements and estimated cost
- Formal verification scope (bridge contract at minimum)
