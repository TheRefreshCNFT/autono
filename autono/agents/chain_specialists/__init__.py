"""Chain specialist agents — one expert per blockchain + repo watcher.

Each agent wraps the WALI wallet's chain-specific modules and adds
cross-chain awareness via the Links & Locks knowledge system.

THE CHAIN SPECIALISTS:
1. CardanoChainAgent  — Cardano protocol, Plutus, CIP standards, MeshJS
2. BitcoinChainAgent  — Bitcoin protocol, BIP standards, Taproot, PSBT
3. NightChainAgent    — Night/Midnight chain, encrypted storage, recovery
4. CharmsAgent        — Charms spells on Bitcoin, ZK proofs, BitcoinOS bridge
5. RepoWatcherAgent   — Monitors all official repos for releases, issues, betas
6. SpellCasterAgent   — Cross-chain spell coordination (construct, prove, cast)

These agents coordinate cross-chain operations through the message bus.
They use the knowledge graph for instant protocol lookups (Locks) and
cross-chain routing decisions (mLocks/Links).

Spells are the universal cross-chain instruction format:
  Lock ADA, mint charm on BTC  -> spell
  Burn charm, unlock ADA       -> spell
  Private transfer via Night   -> spell with ZK proof
"""

from autono.agents.chain_specialists.cardano_agent import CardanoChainAgent
from autono.agents.chain_specialists.bitcoin_agent import BitcoinChainAgent
from autono.agents.chain_specialists.night_agent import NightChainAgent
from autono.agents.chain_specialists.charms_agent import CharmsAgent
from autono.agents.chain_specialists.repo_watcher import RepoWatcherAgent
from autono.agents.chain_specialists.spell_caster import SpellCasterAgent

ALL_CHAIN_SPECIALISTS = [
    CardanoChainAgent,
    BitcoinChainAgent,
    NightChainAgent,
    CharmsAgent,
    RepoWatcherAgent,
    SpellCasterAgent,
]

__all__ = [
    "CardanoChainAgent", "BitcoinChainAgent",
    "NightChainAgent", "CharmsAgent", "RepoWatcherAgent",
    "SpellCasterAgent",
    "ALL_CHAIN_SPECIALISTS",
]
