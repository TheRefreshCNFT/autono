"""Comprehensive protocol knowledge base — ALL known facts for brain initialization.

This is the canonical source of truth for the Links & Locks knowledge graph.
Every fact here becomes a Lock (deterministic, bypass inference).
Organized by domain, subdomain, and volatility tier.

When the KnowledgeExpansionEngine runs seed_all_facts(), every entry in
ALL_PROTOCOL_FACTS is turned into a KnowledgeNode + Lock pair.

Volatility tiers control re-validation scheduling:
- permanent: never changes (math, protocol constants baked into genesis)
- stable: changes via hard forks or CIP/BIP process (weekly check)
- moderate: SDK versions, library APIs (daily check)
- volatile: API endpoints, current events (hourly check)
"""

from __future__ import annotations

from typing import Any

from autono.knowledge.types import VolatilityTier

# Type alias for readability
ProtocolFact = dict[str, Any]
# Keys: fact, domain, subdomain, answer, answer_type, source, tags, volatility


# ============================================================================
# CARDANO — Protocol Constants
# ============================================================================

_CARDANO_PROTOCOL: list[ProtocolFact] = [
    {
        "fact": "1 ADA = 1,000,000 Lovelace",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 1_000_000, "answer_type": "integer",
        "source": "Cardano Specification",
        "tags": ["ada", "lovelace", "conversion", "unit"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano maximum supply is 45,000,000,000 ADA",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 45_000_000_000, "answer_type": "integer",
        "source": "Cardano Genesis",
        "tags": ["supply", "maximum", "economics"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano slot duration is 1 second",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 1, "answer_type": "integer",
        "source": "Shelley Genesis Parameters",
        "tags": ["slot", "timing", "consensus"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano epoch length is 432,000 slots (5 days)",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 432_000, "answer_type": "integer",
        "source": "Shelley Genesis Parameters",
        "tags": ["epoch", "length", "timing"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano block time is approximately 20 seconds",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 20, "answer_type": "integer",
        "source": "Ouroboros Praos",
        "tags": ["block", "time", "consensus"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano security parameter k is 2160",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 2160, "answer_type": "integer",
        "source": "Shelley Genesis Parameters",
        "tags": ["security", "k-parameter", "consensus"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano max block body size is 90,112 bytes (88 KB)",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 90_112, "answer_type": "integer",
        "source": "Cardano Protocol Parameters",
        "tags": ["block", "size", "limit"],
        "volatility": "stable",
    },
    {
        "fact": "Cardano max transaction size is 16,384 bytes",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 16_384, "answer_type": "integer",
        "source": "Cardano Protocol Parameters",
        "tags": ["transaction", "size", "limit"],
        "volatility": "stable",
    },
    {
        "fact": "Cardano mainnet protocol magic is 764824073",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 764824073, "answer_type": "integer",
        "source": "Cardano Genesis",
        "tags": ["protocol-magic", "mainnet", "network"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano testnet protocol magic is 1",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 1, "answer_type": "integer",
        "source": "Cardano Genesis",
        "tags": ["protocol-magic", "testnet", "network"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano preprod protocol magic is 1",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 1, "answer_type": "integer",
        "source": "Cardano Genesis",
        "tags": ["protocol-magic", "preprod", "network"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano preview protocol magic is 2",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 2, "answer_type": "integer",
        "source": "Cardano Genesis",
        "tags": ["protocol-magic", "preview", "network"],
        "volatility": "permanent",
    },
    {
        "fact": "Shelley era started at epoch 208",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 208, "answer_type": "integer",
        "source": "Cardano Mainnet History",
        "tags": ["shelley", "epoch", "era", "history"],
        "volatility": "permanent",
    },
    {
        "fact": "Byron slot duration was 20 seconds",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 20, "answer_type": "integer",
        "source": "Byron Specification",
        "tags": ["byron", "slot", "timing", "history"],
        "volatility": "permanent",
    },
    {
        "fact": "Minimum UTXO value on Cardano is approximately 1 ADA (1,000,000 lovelace)",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 1_000_000, "answer_type": "integer",
        "source": "Cardano Protocol Parameters",
        "tags": ["utxo", "minimum", "lovelace"],
        "volatility": "stable",
    },
    {
        "fact": "Cardano treasury tax rate is 20% of rewards",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 0.2, "answer_type": "float",
        "source": "Cardano Protocol Parameters (tau)",
        "tags": ["treasury", "tax", "rewards", "economics"],
        "volatility": "stable",
    },
    {
        "fact": "Cardano collateral percentage for Plutus scripts is 150%",
        "domain": "cardano", "subdomain": "protocol",
        "answer": 150, "answer_type": "integer",
        "source": "Cardano Protocol Parameters",
        "tags": ["collateral", "plutus", "script"],
        "volatility": "stable",
    },
]


# ============================================================================
# CARDANO — Address Types
# ============================================================================

_CARDANO_ADDRESSES: list[ProtocolFact] = [
    {
        "fact": "Cardano mainnet Shelley address prefix is addr1",
        "domain": "cardano", "subdomain": "address",
        "answer": "addr1", "answer_type": "string",
        "source": "CIP-0019",
        "tags": ["address", "mainnet", "shelley", "bech32"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano testnet Shelley address prefix is addr_test1",
        "domain": "cardano", "subdomain": "address",
        "answer": "addr_test1", "answer_type": "string",
        "source": "CIP-0019",
        "tags": ["address", "testnet", "shelley", "bech32"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano mainnet stake address prefix is stake1",
        "domain": "cardano", "subdomain": "address",
        "answer": "stake1", "answer_type": "string",
        "source": "CIP-0019",
        "tags": ["address", "mainnet", "stake", "bech32"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano testnet stake address prefix is stake_test1",
        "domain": "cardano", "subdomain": "address",
        "answer": "stake_test1", "answer_type": "string",
        "source": "CIP-0019",
        "tags": ["address", "testnet", "stake", "bech32"],
        "volatility": "permanent",
    },
    {
        "fact": "Byron mainnet Daedalus addresses start with DdzFF",
        "domain": "cardano", "subdomain": "address",
        "answer": "DdzFF", "answer_type": "string",
        "source": "Byron Specification",
        "tags": ["address", "byron", "daedalus", "base58", "mainnet"],
        "volatility": "permanent",
    },
    {
        "fact": "Byron mainnet Icarus/Yoroi addresses start with Ae2td",
        "domain": "cardano", "subdomain": "address",
        "answer": "Ae2td", "answer_type": "string",
        "source": "Byron Specification",
        "tags": ["address", "byron", "icarus", "yoroi", "base58", "mainnet"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano script addresses start with addr1z (mainnet) or addr_test1z (testnet)",
        "domain": "cardano", "subdomain": "address",
        "answer": {"mainnet": "addr1z", "testnet": "addr_test1z"},
        "answer_type": "json",
        "source": "CIP-0019",
        "tags": ["address", "script", "plutus"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano uses BIP-1852 purpose for key derivation (purpose 1852')",
        "domain": "cardano", "subdomain": "wallet",
        "answer": 1852, "answer_type": "integer",
        "source": "CIP-1852",
        "tags": ["wallet", "derivation", "bip-1852", "purpose"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano coin type in BIP-44 derivation is 1815",
        "domain": "cardano", "subdomain": "wallet",
        "answer": 1815, "answer_type": "integer",
        "source": "SLIP-0044",
        "tags": ["wallet", "derivation", "coin-type"],
        "volatility": "permanent",
    },
]


# ============================================================================
# CARDANO — CIP Standards
# ============================================================================

_CARDANO_CIPS: list[ProtocolFact] = [
    {
        "fact": "CIP-25: NFT Metadata Standard — metadata label 721",
        "domain": "cardano", "subdomain": "cip",
        "answer": 721, "answer_type": "integer",
        "source": "CIP-0025",
        "tags": ["nft", "metadata", "cip-25", "label"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-26: Cardano Off-chain Metadata",
        "domain": "cardano", "subdomain": "cip",
        "answer": "Off-chain metadata standard for Cardano tokens",
        "answer_type": "string",
        "source": "CIP-0026",
        "tags": ["metadata", "off-chain", "cip-26"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-27: CNFT Community Royalties Standard",
        "domain": "cardano", "subdomain": "cip",
        "answer": "Royalty payments for CNFT secondary sales",
        "answer_type": "string",
        "source": "CIP-0027",
        "tags": ["nft", "royalties", "cnft", "cip-27"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-30: Cardano dApp-Wallet Web Bridge",
        "domain": "cardano", "subdomain": "cip",
        "answer": "JavaScript API for dApps to interact with wallets",
        "answer_type": "string",
        "source": "CIP-0030",
        "tags": ["dapp", "wallet", "bridge", "cip-30", "javascript"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-36: Catalyst Registration and Voting",
        "domain": "cardano", "subdomain": "cip",
        "answer": "Catalyst fund voting registration via metadata",
        "answer_type": "string",
        "source": "CIP-0036",
        "tags": ["catalyst", "voting", "governance", "cip-36"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-67: Asset Name Label Standard (first 4 bytes of asset name encode label)",
        "domain": "cardano", "subdomain": "cip",
        "answer": "First 4 bytes of asset name = label (e.g., 000643b0 = reference NFT)",
        "answer_type": "string",
        "source": "CIP-0067",
        "tags": ["asset-name", "label", "cip-67"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-68: Datum Metadata Standard using reference tokens",
        "domain": "cardano", "subdomain": "cip",
        "answer": "On-chain metadata via reference tokens with datum",
        "answer_type": "string",
        "source": "CIP-0068",
        "tags": ["metadata", "datum", "reference-token", "cip-68"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-2: Coin Selection Algorithm for Cardano wallets",
        "domain": "cardano", "subdomain": "cip",
        "answer": "Random-improve coin selection with multi-asset support",
        "answer_type": "string",
        "source": "CIP-0002",
        "tags": ["wallet", "coin-selection", "cip-2"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-5: Common Bech32 Prefixes for Cardano",
        "domain": "cardano", "subdomain": "cip",
        "answer": "addr, stake, pool, vk, sk, datum, script prefixes",
        "answer_type": "string",
        "source": "CIP-0005",
        "tags": ["bech32", "prefix", "encoding", "cip-5"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-8: Message Signing for Cardano",
        "domain": "cardano", "subdomain": "cip",
        "answer": "COSE-based message signing with Cardano keys",
        "answer_type": "string",
        "source": "CIP-0008",
        "tags": ["signing", "message", "cose", "cip-8"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-20: Transaction Message/Comment Metadata — label 674",
        "domain": "cardano", "subdomain": "cip",
        "answer": 674, "answer_type": "integer",
        "source": "CIP-0020",
        "tags": ["metadata", "message", "comment", "cip-20", "label"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-86: NFT Metadata Update Standard",
        "domain": "cardano", "subdomain": "cip",
        "answer": "Protocol for updating NFT metadata post-mint",
        "answer_type": "string",
        "source": "CIP-0086",
        "tags": ["nft", "metadata", "update", "cip-86"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-105: Conway Era Key Chains for HD Wallets",
        "domain": "cardano", "subdomain": "cip",
        "answer": "Extended key derivation for Conway governance keys",
        "answer_type": "string",
        "source": "CIP-0105",
        "tags": ["conway", "governance", "wallet", "cip-105"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-381: Plutus Support for Pairings over BLS12-381",
        "domain": "cardano", "subdomain": "cip",
        "answer": "BLS12-381 curve support in Plutus for ZK proof verification",
        "answer_type": "string",
        "source": "CIP-0381",
        "tags": ["plutus", "bls", "zk-proof", "cryptography", "cip-381"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-19: Cardano Address structure specification",
        "domain": "cardano", "subdomain": "cip",
        "answer": "Bech32 address format with payment + stake credentials",
        "answer_type": "string",
        "source": "CIP-0019",
        "tags": ["address", "bech32", "specification", "cip-19"],
        "volatility": "stable",
    },
    {
        "fact": "CIP-1854: Multi-signature HD wallets for Cardano",
        "domain": "cardano", "subdomain": "cip",
        "answer": "HD derivation path for multi-sig wallets (purpose 1854')",
        "answer_type": "string",
        "source": "CIP-1854",
        "tags": ["wallet", "multi-sig", "derivation", "cip-1854"],
        "volatility": "stable",
    },
]


# ============================================================================
# CARDANO — Plutus / Smart Contracts
# ============================================================================

_CARDANO_PLUTUS: list[ProtocolFact] = [
    {
        "fact": "Plutus V1 introduced in Alonzo era at epoch 290",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": {"version": "V1", "era": "Alonzo", "epoch": 290},
        "answer_type": "json",
        "source": "Alonzo Hard Fork",
        "tags": ["plutus", "v1", "alonzo", "smart-contract", "epoch"],
        "volatility": "permanent",
    },
    {
        "fact": "Plutus V2 introduced in Vasil era at epoch 365",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": {"version": "V2", "era": "Vasil", "epoch": 365},
        "answer_type": "json",
        "source": "Vasil Hard Fork",
        "tags": ["plutus", "v2", "vasil", "smart-contract", "epoch"],
        "volatility": "permanent",
    },
    {
        "fact": "Plutus V3 introduced in Chang era at epoch 503",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": {"version": "V3", "era": "Chang", "epoch": 503},
        "answer_type": "json",
        "source": "Chang Hard Fork",
        "tags": ["plutus", "v3", "chang", "smart-contract", "epoch"],
        "volatility": "permanent",
    },
    {
        "fact": "Plutus V3 is the current smart contract language version",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": "PlutusV3", "answer_type": "string",
        "source": "Chang Hard Fork",
        "tags": ["plutus", "current", "version"],
        "volatility": "stable",
    },
    {
        "fact": "Plutus script purposes: Spend, Mint, Certify, Reward, Vote, Propose",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": ["Spend", "Mint", "Certify", "Reward", "Vote", "Propose"],
        "answer_type": "json",
        "source": "Plutus V3 Specification",
        "tags": ["plutus", "script-purpose", "conway"],
        "volatility": "stable",
    },
    {
        "fact": "Plutus cost model uses CPU and memory units for execution budgets",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": "CPU steps + Memory units per execution",
        "answer_type": "string",
        "source": "Plutus Core Specification",
        "tags": ["plutus", "cost-model", "execution"],
        "volatility": "stable",
    },
    {
        "fact": "Cardano script hash is 28-byte Blake2b-224",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": "Blake2b-224 (28 bytes)",
        "answer_type": "string",
        "source": "Cardano Ledger Specification",
        "tags": ["hash", "script", "blake2b"],
        "volatility": "permanent",
    },
    {
        "fact": "Cardano datum hash is 32-byte Blake2b-256",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": "Blake2b-256 (32 bytes)",
        "answer_type": "string",
        "source": "Cardano Ledger Specification",
        "tags": ["hash", "datum", "blake2b"],
        "volatility": "permanent",
    },
    {
        "fact": "CIP-33: Reference scripts (Vasil) — scripts stored on-chain and referenced by hash",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": "Store scripts in UTXOs, reference by hash in transactions",
        "answer_type": "string",
        "source": "CIP-0033 (Vasil Hard Fork)",
        "tags": ["reference-script", "vasil", "cip-33"],
        "volatility": "permanent",
    },
    {
        "fact": "CIP-32: Inline datums (Vasil) — datums stored directly in UTXOs",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": "Datums embedded directly in transaction outputs",
        "answer_type": "string",
        "source": "CIP-0032 (Vasil Hard Fork)",
        "tags": ["inline-datum", "vasil", "cip-32"],
        "volatility": "permanent",
    },
    {
        "fact": "CIP-31: Reference inputs (Vasil) — read UTXOs without consuming them",
        "domain": "cardano", "subdomain": "smart-contracts",
        "answer": "Read-only UTXO references in transactions",
        "answer_type": "string",
        "source": "CIP-0031 (Vasil Hard Fork)",
        "tags": ["reference-input", "vasil", "cip-31"],
        "volatility": "permanent",
    },
]


# ============================================================================
# CARDANO — SDK / Tools
# ============================================================================

_CARDANO_SDK: list[ProtocolFact] = [
    {
        "fact": "MeshJS is a JavaScript/TypeScript SDK for Cardano dApp development",
        "domain": "cardano", "subdomain": "sdk",
        "answer": "meshjs.dev — @meshsdk/core", "answer_type": "string",
        "source": "https://meshjs.dev",
        "tags": ["meshjs", "javascript", "typescript", "sdk"],
        "volatility": "moderate",
    },
    {
        "fact": "Opshin compiles Python to Plutus Core for Cardano smart contracts",
        "domain": "cardano", "subdomain": "sdk",
        "answer": "opshin", "answer_type": "string",
        "source": "https://github.com/OpShin/opshin",
        "tags": ["opshin", "python", "smart-contract", "plutus"],
        "volatility": "moderate",
    },
    {
        "fact": "Helios is a JavaScript/TypeScript toolkit for Cardano smart contracts",
        "domain": "cardano", "subdomain": "sdk",
        "answer": "helios", "answer_type": "string",
        "source": "https://github.com/Hyperion-BT/helios",
        "tags": ["helios", "javascript", "smart-contract"],
        "volatility": "moderate",
    },
    {
        "fact": "Aiken is a Rust-like smart contract language for Cardano",
        "domain": "cardano", "subdomain": "sdk",
        "answer": "aiken-lang.org — Rust-like syntax, compiles to UPLC",
        "answer_type": "string",
        "source": "https://aiken-lang.org",
        "tags": ["aiken", "smart-contract", "rust-like"],
        "volatility": "moderate",
    },
    {
        "fact": "Lucid Evolution is a TypeScript SDK for Cardano transactions",
        "domain": "cardano", "subdomain": "sdk",
        "answer": "lucid-evolution by Anastasia Labs",
        "answer_type": "string",
        "source": "https://github.com/Anastasia-Labs/lucid-evolution",
        "tags": ["lucid", "typescript", "sdk", "transactions"],
        "volatility": "moderate",
    },
    {
        "fact": "Ogmios is a WebSocket bridge to cardano-node",
        "domain": "cardano", "subdomain": "sdk",
        "answer": "ogmios.dev — lightweight bridge for node queries",
        "answer_type": "string",
        "source": "https://ogmios.dev",
        "tags": ["ogmios", "websocket", "node", "bridge"],
        "volatility": "moderate",
    },
    {
        "fact": "cardano-db-sync indexes the Cardano blockchain into PostgreSQL",
        "domain": "cardano", "subdomain": "sdk",
        "answer": "PostgreSQL indexer for the full Cardano chain",
        "answer_type": "string",
        "source": "https://github.com/IntersectMBO/cardano-db-sync",
        "tags": ["db-sync", "postgresql", "indexer"],
        "volatility": "moderate",
    },
]


# ============================================================================
# CARDANO — API Endpoints
# ============================================================================

_CARDANO_API: list[ProtocolFact] = [
    {
        "fact": "Blockfrost mainnet API endpoint",
        "domain": "cardano", "subdomain": "api",
        "answer": "https://cardano-mainnet.blockfrost.io/api/v0",
        "answer_type": "url",
        "source": "Blockfrost Documentation",
        "tags": ["blockfrost", "api", "mainnet", "endpoint"],
        "volatility": "volatile",
    },
    {
        "fact": "Blockfrost testnet API endpoint",
        "domain": "cardano", "subdomain": "api",
        "answer": "https://cardano-testnet.blockfrost.io/api/v0",
        "answer_type": "url",
        "source": "Blockfrost Documentation",
        "tags": ["blockfrost", "api", "testnet", "endpoint"],
        "volatility": "volatile",
    },
    {
        "fact": "Blockfrost preview API endpoint",
        "domain": "cardano", "subdomain": "api",
        "answer": "https://cardano-preview.blockfrost.io/api/v0",
        "answer_type": "url",
        "source": "Blockfrost Documentation",
        "tags": ["blockfrost", "api", "preview", "endpoint"],
        "volatility": "volatile",
    },
    {
        "fact": "Blockfrost preprod API endpoint",
        "domain": "cardano", "subdomain": "api",
        "answer": "https://cardano-preprod.blockfrost.io/api/v0",
        "answer_type": "url",
        "source": "Blockfrost Documentation",
        "tags": ["blockfrost", "api", "preprod", "endpoint"],
        "volatility": "volatile",
    },
    {
        "fact": "Koios mainnet API endpoint",
        "domain": "cardano", "subdomain": "api",
        "answer": "https://api.koios.rest/api/v1",
        "answer_type": "url",
        "source": "Koios Documentation",
        "tags": ["koios", "api", "mainnet", "endpoint"],
        "volatility": "volatile",
    },
    {
        "fact": "Koios testnet API endpoint",
        "domain": "cardano", "subdomain": "api",
        "answer": "https://testnet.koios.rest/api/v1",
        "answer_type": "url",
        "source": "Koios Documentation",
        "tags": ["koios", "api", "testnet", "endpoint"],
        "volatility": "volatile",
    },
]


# ============================================================================
# CARDANO — Governance / Conway
# ============================================================================

_CARDANO_GOVERNANCE: list[ProtocolFact] = [
    {
        "fact": "Conway era introduces DReps (Delegated Representatives) for on-chain governance",
        "domain": "cardano", "subdomain": "governance",
        "answer": "DRep delegation for governance voting",
        "answer_type": "string",
        "source": "CIP-1694 (Conway Governance)",
        "tags": ["conway", "drep", "governance", "voting"],
        "volatility": "stable",
    },
    {
        "fact": "Conway governance has Constitutional Committee, DReps, and SPOs as voting bodies",
        "domain": "cardano", "subdomain": "governance",
        "answer": ["Constitutional Committee", "DReps", "SPOs"],
        "answer_type": "json",
        "source": "CIP-1694",
        "tags": ["conway", "governance", "voting-bodies"],
        "volatility": "stable",
    },
    {
        "fact": "Conway governance action types",
        "domain": "cardano", "subdomain": "governance",
        "answer": ["NoConfidence", "UpdateCommittee", "NewConstitution",
                    "TreasuryWithdrawal", "HardForkInitiation", "ParameterChange", "InfoAction"],
        "answer_type": "json",
        "source": "CIP-1694",
        "tags": ["conway", "governance", "actions"],
        "volatility": "stable",
    },
]


# ============================================================================
# BITCOIN — Protocol Constants
# ============================================================================

_BITCOIN_PROTOCOL: list[ProtocolFact] = [
    {
        "fact": "1 BTC = 100,000,000 satoshis",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 100_000_000, "answer_type": "integer",
        "source": "Bitcoin Protocol",
        "tags": ["btc", "satoshi", "conversion", "unit"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin maximum supply is 21,000,000 BTC",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 21_000_000, "answer_type": "integer",
        "source": "Bitcoin Protocol",
        "tags": ["supply", "maximum", "economics"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin block time target is 10 minutes (600 seconds)",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 600, "answer_type": "integer",
        "source": "Bitcoin Whitepaper",
        "tags": ["block", "time", "consensus"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin block subsidy halves every 210,000 blocks (~4 years)",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 210_000, "answer_type": "integer",
        "source": "Bitcoin Protocol",
        "tags": ["halving", "subsidy", "economics"],
        "volatility": "permanent",
    },
    {
        "fact": "Current Bitcoin block subsidy is 3.125 BTC (post April 2024 halving)",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 3.125, "answer_type": "float",
        "source": "Bitcoin Block 840,000 (April 2024)",
        "tags": ["subsidy", "halving", "current", "block-reward"],
        "volatility": "stable",
    },
    {
        "fact": "Next Bitcoin halving expected at approximately block 1,050,000 (~2028)",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 1_050_000, "answer_type": "integer",
        "source": "Bitcoin Protocol (210,000 block intervals)",
        "tags": ["halving", "next", "future", "block"],
        "volatility": "stable",
    },
    {
        "fact": "Bitcoin max block weight is 4,000,000 weight units",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 4_000_000, "answer_type": "integer",
        "source": "BIP-141 (SegWit)",
        "tags": ["block", "weight", "limit", "segwit"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin legacy max block size is 1,000,000 bytes",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 1_000_000, "answer_type": "integer",
        "source": "Bitcoin Protocol",
        "tags": ["block", "size", "limit", "legacy"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin SegWit witness discount is 4x (witness bytes count as 1/4 weight)",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 4, "answer_type": "integer",
        "source": "BIP-141",
        "tags": ["segwit", "witness", "discount", "weight"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin P2PKH dust limit is 546 satoshis",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 546, "answer_type": "integer",
        "source": "Bitcoin Core",
        "tags": ["dust", "limit", "p2pkh", "minimum"],
        "volatility": "stable",
    },
    {
        "fact": "Bitcoin P2WPKH dust limit is 294 satoshis",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 294, "answer_type": "integer",
        "source": "Bitcoin Core",
        "tags": ["dust", "limit", "p2wpkh", "segwit", "minimum"],
        "volatility": "stable",
    },
    {
        "fact": "Bitcoin coinbase maturity is 100 blocks",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 100, "answer_type": "integer",
        "source": "Bitcoin Protocol",
        "tags": ["coinbase", "maturity", "mining"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin difficulty adjusts every 2016 blocks (~2 weeks)",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 2016, "answer_type": "integer",
        "source": "Bitcoin Protocol",
        "tags": ["difficulty", "adjustment", "mining", "consensus"],
        "volatility": "permanent",
    },
    {
        "fact": "SegWit activated at Bitcoin block 481,824 (August 2017)",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 481_824, "answer_type": "integer",
        "source": "BIP-141 Activation",
        "tags": ["segwit", "activation", "block", "history"],
        "volatility": "permanent",
    },
    {
        "fact": "Taproot activated at Bitcoin block 709,632 (November 2021)",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": 709_632, "answer_type": "integer",
        "source": "BIP-341 Activation",
        "tags": ["taproot", "activation", "block", "history"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin genesis block hash",
        "domain": "bitcoin", "subdomain": "protocol",
        "answer": "000000000019d6689c085ae165831e934ff763ae46a2a6c172b3f1b60a8ce26f",
        "answer_type": "string",
        "source": "Bitcoin Genesis (Block 0)",
        "tags": ["genesis", "block", "hash", "history"],
        "volatility": "permanent",
    },
]


# ============================================================================
# BITCOIN — Address Types
# ============================================================================

_BITCOIN_ADDRESSES: list[ProtocolFact] = [
    {
        "fact": "Bitcoin mainnet address prefixes: 1 (P2PKH), 3 (P2SH), bc1q (P2WPKH), bc1p (P2TR)",
        "domain": "bitcoin", "subdomain": "address",
        "answer": {"P2PKH": "1", "P2SH": "3", "P2WPKH": "bc1q", "P2TR": "bc1p"},
        "answer_type": "json",
        "source": "BIP-173, BIP-350",
        "tags": ["address", "mainnet", "prefix"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin testnet bech32 addresses start with tb1",
        "domain": "bitcoin", "subdomain": "address",
        "answer": "tb1", "answer_type": "string",
        "source": "BIP-173",
        "tags": ["address", "testnet", "bech32"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin testnet legacy addresses start with m or n",
        "domain": "bitcoin", "subdomain": "address",
        "answer": ["m", "n"], "answer_type": "json",
        "source": "Bitcoin Protocol",
        "tags": ["address", "testnet", "legacy"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin testnet P2SH addresses start with 2",
        "domain": "bitcoin", "subdomain": "address",
        "answer": "2", "answer_type": "string",
        "source": "Bitcoin Protocol",
        "tags": ["address", "testnet", "p2sh"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin coin type for mainnet in BIP-44 derivation is 0",
        "domain": "bitcoin", "subdomain": "wallet",
        "answer": 0, "answer_type": "integer",
        "source": "SLIP-0044",
        "tags": ["wallet", "derivation", "coin-type", "mainnet"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin coin type for testnet in BIP-44 derivation is 1",
        "domain": "bitcoin", "subdomain": "wallet",
        "answer": 1, "answer_type": "integer",
        "source": "SLIP-0044",
        "tags": ["wallet", "derivation", "coin-type", "testnet"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin BIP-44 purpose 44' for legacy P2PKH addresses",
        "domain": "bitcoin", "subdomain": "wallet",
        "answer": 44, "answer_type": "integer",
        "source": "BIP-0044",
        "tags": ["wallet", "derivation", "legacy", "bip-44", "purpose"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin BIP-49 purpose 49' for P2SH-wrapped SegWit",
        "domain": "bitcoin", "subdomain": "wallet",
        "answer": 49, "answer_type": "integer",
        "source": "BIP-0049",
        "tags": ["wallet", "derivation", "segwit", "bip-49", "purpose"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin BIP-84 purpose 84' for native SegWit P2WPKH",
        "domain": "bitcoin", "subdomain": "wallet",
        "answer": 84, "answer_type": "integer",
        "source": "BIP-0084",
        "tags": ["wallet", "derivation", "segwit", "bip-84", "purpose"],
        "volatility": "permanent",
    },
    {
        "fact": "Bitcoin BIP-86 purpose 86' for Taproot P2TR",
        "domain": "bitcoin", "subdomain": "wallet",
        "answer": 86, "answer_type": "integer",
        "source": "BIP-0086",
        "tags": ["wallet", "derivation", "taproot", "bip-86", "purpose"],
        "volatility": "permanent",
    },
]


# ============================================================================
# BITCOIN — BIP Standards
# ============================================================================

_BITCOIN_BIPS: list[ProtocolFact] = [
    {"fact": "BIP-32: Hierarchical Deterministic Wallets", "domain": "bitcoin", "subdomain": "bip", "answer": "HD wallet key derivation from master seed", "answer_type": "string", "source": "BIP-0032", "tags": ["bip-32", "hd-wallet", "derivation"], "volatility": "permanent"},
    {"fact": "BIP-39: Mnemonic code for generating deterministic keys", "domain": "bitcoin", "subdomain": "bip", "answer": "12/24 word seed phrases from 2048-word wordlist", "answer_type": "string", "source": "BIP-0039", "tags": ["bip-39", "mnemonic", "seed"], "volatility": "permanent"},
    {"fact": "BIP-44: Multi-Account Hierarchy for Deterministic Wallets", "domain": "bitcoin", "subdomain": "bip", "answer": "m/purpose'/coin_type'/account'/change/address_index", "answer_type": "string", "source": "BIP-0044", "tags": ["bip-44", "derivation", "path"], "volatility": "permanent"},
    {"fact": "BIP-141: Segregated Witness (Consensus layer)", "domain": "bitcoin", "subdomain": "bip", "answer": "Moves signature data to witness, fixes tx malleability", "answer_type": "string", "source": "BIP-0141", "tags": ["bip-141", "segwit", "consensus"], "volatility": "permanent"},
    {"fact": "BIP-143: Transaction Signature Verification for SegWit", "domain": "bitcoin", "subdomain": "bip", "answer": "New sighash algorithm for witness programs", "answer_type": "string", "source": "BIP-0143", "tags": ["bip-143", "segwit", "sighash"], "volatility": "permanent"},
    {"fact": "BIP-174: Partially Signed Bitcoin Transactions (PSBT)", "domain": "bitcoin", "subdomain": "bip", "answer": "Standard format for unsigned/partially-signed transactions", "answer_type": "string", "source": "BIP-0174", "tags": ["bip-174", "psbt", "transaction"], "volatility": "permanent"},
    {"fact": "BIP-340: Schnorr Signatures for secp256k1", "domain": "bitcoin", "subdomain": "bip", "answer": "64-byte Schnorr signatures on secp256k1 curve", "answer_type": "string", "source": "BIP-0340", "tags": ["bip-340", "schnorr", "taproot", "signature"], "volatility": "permanent"},
    {"fact": "BIP-341: Taproot — SegWit version 1 spending rules", "domain": "bitcoin", "subdomain": "bip", "answer": "Key-path and script-path spending with MAST", "answer_type": "string", "source": "BIP-0341", "tags": ["bip-341", "taproot", "mast", "segwit-v1"], "volatility": "permanent"},
    {"fact": "BIP-342: Validation of Taproot Scripts (Tapscript)", "domain": "bitcoin", "subdomain": "bip", "answer": "Script validation rules for SegWit version 1", "answer_type": "string", "source": "BIP-0342", "tags": ["bip-342", "tapscript", "validation"], "volatility": "permanent"},
    {"fact": "BIP-370: PSBT Version 2 — enhanced partial signing format", "domain": "bitcoin", "subdomain": "bip", "answer": "PSBTv2 with per-input/output modifiable flags", "answer_type": "string", "source": "BIP-0370", "tags": ["bip-370", "psbt", "v2", "transaction"], "volatility": "permanent"},
]


# ============================================================================
# BITCOIN — Script / Opcodes
# ============================================================================

_BITCOIN_SCRIPT: list[ProtocolFact] = [
    {"fact": "OP_RETURN (0x6a) marks output as provably unspendable, used for data embedding", "domain": "bitcoin", "subdomain": "script", "answer": "0x6a", "answer_type": "string", "source": "Bitcoin Script", "tags": ["opcode", "op_return", "data"], "volatility": "permanent"},
    {"fact": "OP_CHECKSIG (0xac) verifies a signature against a public key", "domain": "bitcoin", "subdomain": "script", "answer": "0xac", "answer_type": "string", "source": "Bitcoin Script", "tags": ["opcode", "signature"], "volatility": "permanent"},
    {"fact": "OP_CHECKMULTISIG (0xae) verifies multiple signatures", "domain": "bitcoin", "subdomain": "script", "answer": "0xae", "answer_type": "string", "source": "Bitcoin Script", "tags": ["opcode", "multisig"], "volatility": "permanent"},
    {"fact": "OP_HASH160 (0xa9) performs SHA256 then RIPEMD160", "domain": "bitcoin", "subdomain": "script", "answer": "0xa9", "answer_type": "string", "source": "Bitcoin Script", "tags": ["opcode", "hash"], "volatility": "permanent"},
    {"fact": "OP_EQUAL (0x87) checks if two stack items are equal", "domain": "bitcoin", "subdomain": "script", "answer": "0x87", "answer_type": "string", "source": "Bitcoin Script", "tags": ["opcode", "comparison"], "volatility": "permanent"},
    {"fact": "OP_DUP (0x76) duplicates top stack item", "domain": "bitcoin", "subdomain": "script", "answer": "0x76", "answer_type": "string", "source": "Bitcoin Script", "tags": ["opcode", "stack"], "volatility": "permanent"},
    {"fact": "OP_CHECKLOCKTIMEVERIFY (0xb1) enforces absolute timelock", "domain": "bitcoin", "subdomain": "script", "answer": "0xb1", "answer_type": "string", "source": "BIP-65", "tags": ["opcode", "timelock", "cltv"], "volatility": "permanent"},
    {"fact": "OP_CHECKSEQUENCEVERIFY (0xb2) enforces relative timelock", "domain": "bitcoin", "subdomain": "script", "answer": "0xb2", "answer_type": "string", "source": "BIP-112", "tags": ["opcode", "timelock", "csv"], "volatility": "permanent"},
    {"fact": "Tapscript uses witness version 1", "domain": "bitcoin", "subdomain": "script", "answer": 1, "answer_type": "integer", "source": "BIP-341", "tags": ["tapscript", "witness", "version"], "volatility": "permanent"},
    {"fact": "Schnorr signature size is 64 bytes", "domain": "bitcoin", "subdomain": "script", "answer": 64, "answer_type": "integer", "source": "BIP-340", "tags": ["schnorr", "signature", "size"], "volatility": "permanent"},
]


# ============================================================================
# BITCOIN — API Endpoints
# ============================================================================

_BITCOIN_API: list[ProtocolFact] = [
    {"fact": "Blockstream mainnet API endpoint", "domain": "bitcoin", "subdomain": "api", "answer": "https://blockstream.info/api", "answer_type": "url", "source": "Blockstream", "tags": ["blockstream", "api", "mainnet"], "volatility": "volatile"},
    {"fact": "Blockstream testnet API endpoint", "domain": "bitcoin", "subdomain": "api", "answer": "https://blockstream.info/testnet/api", "answer_type": "url", "source": "Blockstream", "tags": ["blockstream", "api", "testnet"], "volatility": "volatile"},
    {"fact": "Mempool.space mainnet API endpoint", "domain": "bitcoin", "subdomain": "api", "answer": "https://mempool.space/api", "answer_type": "url", "source": "mempool.space", "tags": ["mempool", "api", "mainnet"], "volatility": "volatile"},
    {"fact": "Mempool.space testnet API endpoint", "domain": "bitcoin", "subdomain": "api", "answer": "https://mempool.space/testnet/api", "answer_type": "url", "source": "mempool.space", "tags": ["mempool", "api", "testnet"], "volatility": "volatile"},
    {"fact": "Bitcoin Core RPC default port mainnet is 8332", "domain": "bitcoin", "subdomain": "api", "answer": 8332, "answer_type": "integer", "source": "Bitcoin Core", "tags": ["rpc", "port", "mainnet"], "volatility": "stable"},
    {"fact": "Bitcoin Core RPC default port testnet is 18332", "domain": "bitcoin", "subdomain": "api", "answer": 18332, "answer_type": "integer", "source": "Bitcoin Core", "tags": ["rpc", "port", "testnet"], "volatility": "stable"},
    {"fact": "Bitcoin Core RPC default port regtest is 18443", "domain": "bitcoin", "subdomain": "api", "answer": 18443, "answer_type": "integer", "source": "Bitcoin Core", "tags": ["rpc", "port", "regtest"], "volatility": "stable"},
]


# ============================================================================
# CHARMS — Protocol & Spells
# ============================================================================

_CHARMS_PROTOCOL: list[ProtocolFact] = [
    {"fact": "Charms are entries of mapping app→data on top of a Bitcoin UTXO", "domain": "charms", "subdomain": "protocol", "answer": "app→data mapping on Bitcoin UTXO", "answer_type": "string", "source": "Charms Documentation", "tags": ["charms", "utxo", "definition"], "volatility": "stable"},
    {"fact": "Charms spell on-chain format: OP_RETURN OP_PUSH 'spell' OP_PUSH CBOR(NormalizedSpell, Groth16Proof)", "domain": "charms", "subdomain": "spell_format", "answer": "OP_RETURN OP_PUSH 'spell' OP_PUSH CBOR(NormalizedSpell, Groth16Proof)", "answer_type": "string", "source": "Charms Protocol Spec", "tags": ["spell", "op_return", "cbor", "groth16"], "volatility": "stable"},
    {"fact": "Charms app tag 'n' = NFT, tag 't' = Token (fungible)", "domain": "charms", "subdomain": "spell_format", "answer": {"n": "NFT", "t": "Token"}, "answer_type": "json", "source": "Charms Spell Specification", "tags": ["charm", "nft", "token", "tag"], "volatility": "stable"},
    {"fact": "Charms app identity is 32 bytes", "domain": "charms", "subdomain": "spell_format", "answer": 32, "answer_type": "integer", "source": "Charms Spell Specification", "tags": ["identity", "app", "bytes"], "volatility": "stable"},
    {"fact": "Charms apps are written in Rust with app_contract entry point", "domain": "charms", "subdomain": "development", "answer": "Rust with app_contract(context: &AppContractContext) entry point", "answer_type": "string", "source": "Charms App Documentation", "tags": ["rust", "app", "smart-contract", "development"], "volatility": "stable"},
    {"fact": "Scaffold new Charms app: charms app new <name>", "domain": "charms", "subdomain": "development", "answer": "charms app new <name>", "answer_type": "string", "source": "Charms CLI", "tags": ["cli", "scaffold", "development"], "volatility": "moderate"},
    {"fact": "Charms spell validity requires: parseable, logically consistent, valid ZK proof", "domain": "charms", "subdomain": "protocol", "answer": ["successfully_parses", "logically_consistent", "valid_proof"], "answer_type": "json", "source": "Charms Protocol", "tags": ["spell", "validity", "proof"], "volatility": "stable"},
    {"fact": "Charms requires Bitcoin Core v28.0+ with testnet4 for development", "domain": "charms", "subdomain": "development", "answer": "Bitcoin Core v28.0+ with testnet4", "answer_type": "string", "source": "Charms Prerequisites", "tags": ["bitcoin-core", "testnet4", "prerequisites"], "volatility": "moderate"},
    {"fact": "NormalizedSpell contains app_public_inputs and tx (ins, outs, coins)", "domain": "charms", "subdomain": "spell_format", "answer": {"fields": ["app_public_inputs", "tx.ins", "tx.outs", "tx.coins"]}, "answer_type": "json", "source": "Charms Spell Specification", "tags": ["spell", "structure", "normalized"], "volatility": "stable"},
    {"fact": "Charms spell transactions have exactly 2 outputs: actual output + OP_RETURN", "domain": "charms", "subdomain": "spell_format", "answer": 2, "answer_type": "integer", "source": "Charms Protocol Spec", "tags": ["spell", "outputs", "transaction"], "volatility": "stable"},
    {"fact": "Charms uses client-side validation with Groth16 ZK proofs", "domain": "charms", "subdomain": "protocol", "answer": "Client-side validation with Groth16 proofs", "answer_type": "string", "source": "Charms Protocol", "tags": ["validation", "groth16", "zk-proof", "client-side"], "volatility": "stable"},
    {"fact": "Charms tick is a unique lowercase string identifier for fungible tokens", "domain": "charms", "subdomain": "spell_format", "answer": "Unique lowercase string (e.g., 'gold', 'usd')", "answer_type": "string", "source": "Charms Token Specification", "tags": ["tick", "token", "identifier", "fungible"], "volatility": "stable"},
    {"fact": "charms app build compiles a Charms app to WASM", "domain": "charms", "subdomain": "development", "answer": "charms app build", "answer_type": "string", "source": "Charms CLI", "tags": ["cli", "build", "wasm"], "volatility": "moderate"},
    {"fact": "charms spell create creates a new spell definition", "domain": "charms", "subdomain": "development", "answer": "charms spell create", "answer_type": "string", "source": "Charms CLI", "tags": ["cli", "spell", "create"], "volatility": "moderate"},
    {"fact": "charms spell prove generates a ZK proof for a spell", "domain": "charms", "subdomain": "development", "answer": "charms spell prove", "answer_type": "string", "source": "Charms CLI", "tags": ["cli", "spell", "prove", "zk-proof"], "volatility": "moderate"},
    {"fact": "charms spell cast submits a spell transaction to the network", "domain": "charms", "subdomain": "development", "answer": "charms spell cast", "answer_type": "string", "source": "Charms CLI", "tags": ["cli", "spell", "cast", "submit"], "volatility": "moderate"},
]


# ============================================================================
# BITCOINOS — Grail Bridge, BitSNARK, zkBTC
# ============================================================================

_BITCOINOS_PROTOCOL: list[ProtocolFact] = [
    {"fact": "BitcoinOS first verified ZK proof on Bitcoin mainnet at Block 853,626 (July 2024)", "domain": "bitcoinos", "subdomain": "protocol", "answer": 853_626, "answer_type": "integer", "source": "BitcoinOS History", "tags": ["milestone", "zk-proof", "bitcoin", "history"], "volatility": "permanent"},
    {"fact": "Grail Bridge locks BTC in Taproot address, mints on L2 with ZK proof verification", "domain": "bitcoinos", "subdomain": "bridge", "answer": "Lock BTC in Taproot → ZK verify → Mint on L2", "answer_type": "string", "source": "BitcoinOS Grail Bridge Spec", "tags": ["grail", "bridge", "taproot", "zk-proof"], "volatility": "stable"},
    {"fact": "Grail Bridge security: 1/n trust assumption — single honest verifier guarantees integrity", "domain": "bitcoinos", "subdomain": "bridge", "answer": "1/n honest verifier trust model", "answer_type": "string", "source": "BitcoinOS Security Model", "tags": ["grail", "security", "trust", "verifier"], "volatility": "stable"},
    {"fact": "zkBTC is a 1:1 BTC-backed programmable token for DeFi", "domain": "bitcoinos", "subdomain": "protocol", "answer": "1:1 BTC-backed, non-custodial, ZK-verified", "answer_type": "string", "source": "BitcoinOS zkBTC Spec", "tags": ["zkbtc", "defi", "collateral"], "volatility": "stable"},
    {"fact": "BitSNARK is the ZK verification VM for Bitcoin, used by BitcoinOS", "domain": "bitcoinos", "subdomain": "protocol", "answer": "BitSNARK", "answer_type": "string", "source": "BitcoinOS Documentation", "tags": ["bitsnark", "zk-proof", "verification", "vm"], "volatility": "stable"},
    {"fact": "MerkleMesh is BitcoinOS rollup infrastructure on Bitcoin", "domain": "bitcoinos", "subdomain": "protocol", "answer": "Rollup infrastructure for Bitcoin-based L2s", "answer_type": "string", "source": "BitcoinOS Documentation", "tags": ["merklemesh", "rollup", "l2"], "volatility": "stable"},
]


# ============================================================================
# NIGHT CHAIN / MIDNIGHT
# ============================================================================

_NIGHT_CHAIN_PROTOCOL: list[ProtocolFact] = [
    {"fact": "Midnight is a privacy-preserving sidechain from IOG (Input Output Global)", "domain": "night_chain", "subdomain": "protocol", "answer": "Privacy sidechain by IOG using ZK proofs", "answer_type": "string", "source": "Midnight Network", "tags": ["midnight", "privacy", "iog", "sidechain"], "volatility": "stable"},
    {"fact": "Midnight uses the Compact language for ZK-powered smart contracts", "domain": "night_chain", "subdomain": "protocol", "answer": "Compact", "answer_type": "string", "source": "Midnight Documentation", "tags": ["compact", "language", "smart-contract", "zk"], "volatility": "stable"},
    {"fact": "Night Chain uses Ed25519 keypairs", "domain": "night_chain", "subdomain": "protocol", "answer": "Ed25519", "answer_type": "string", "source": "Night Chain Specification", "tags": ["keypair", "ed25519", "cryptography"], "volatility": "stable"},
    {"fact": "Night Chain address prefix is night1 (bech32 encoded)", "domain": "night_chain", "subdomain": "protocol", "answer": "night1", "answer_type": "string", "source": "Night Chain Specification", "tags": ["address", "prefix", "bech32"], "volatility": "stable"},
    {"fact": "Night Chain uses AES-256-GCM encryption with PBKDF2 key derivation (100,000 iterations)", "domain": "night_chain", "subdomain": "encryption", "answer": "AES-256-GCM + PBKDF2-SHA256 (100,000 iterations)", "answer_type": "string", "source": "Night Chain Encryption Spec", "tags": ["encryption", "aes", "pbkdf2"], "volatility": "stable"},
    {"fact": "Midnight supports selective disclosure — prove properties without revealing data", "domain": "night_chain", "subdomain": "protocol", "answer": "ZK-based selective disclosure of private state", "answer_type": "string", "source": "Midnight Documentation", "tags": ["privacy", "selective-disclosure", "zk-proof"], "volatility": "stable"},
    {"fact": "DarkShield nodes handle private state in the Midnight network", "domain": "night_chain", "subdomain": "protocol", "answer": "DarkShield nodes manage encrypted/private state", "answer_type": "string", "source": "Midnight Architecture", "tags": ["darkshield", "node", "privacy"], "volatility": "stable"},
    {"fact": "DUST is the native utility token of the Midnight network", "domain": "night_chain", "subdomain": "protocol", "answer": "DUST", "answer_type": "string", "source": "Midnight Network", "tags": ["dust", "token", "native", "utility"], "volatility": "stable"},
    {"fact": "Midnight uses IOG's partner chains framework", "domain": "night_chain", "subdomain": "protocol", "answer": "IOG Partner Chains (Substrate-based)", "answer_type": "string", "source": "IOG Partner Chains", "tags": ["partner-chains", "iog", "framework", "substrate"], "volatility": "stable"},
    {"fact": "Compact language distinguishes between public and private contract state", "domain": "night_chain", "subdomain": "compact", "answer": "pub (public on-chain) vs private (ZK-protected) state", "answer_type": "string", "source": "Compact Language Specification", "tags": ["compact", "public", "private", "state"], "volatility": "stable"},
    {"fact": "Recovery dialog uses 4-line challenge-response pattern", "domain": "night_chain", "subdomain": "recovery", "answer": "4 lines: user-4-words, bot-4-words, user-4-words, bot-4-words", "answer_type": "string", "source": "Recovery Protocol", "tags": ["recovery", "dialog", "challenge"], "volatility": "stable"},
    {"fact": "Access key control: 3 max failed attempts, 15-minute lockout", "domain": "night_chain", "subdomain": "security", "answer": {"max_attempts": 3, "lockout_minutes": 15}, "answer_type": "json", "source": "Access Control Specification", "tags": ["security", "rate-limit", "lockout"], "volatility": "stable"},
]


# ============================================================================
# CROSS-CHAIN — Interoperability Facts
# ============================================================================

_CROSS_CHAIN: list[ProtocolFact] = [
    {"fact": "Charms enables bridgeless cross-chain transfers — tokens materialize natively on each chain", "domain": "cross_chain", "subdomain": "bridge", "answer": "Native materialization — no wrapped tokens, no custodians", "answer_type": "string", "source": "Charms Cross-Chain Specification", "tags": ["bridge", "cross-chain", "native", "cardano", "bitcoin"], "volatility": "stable"},
    {"fact": "Cardano tokens via Charms land as CIP-25/CNT native assets", "domain": "cross_chain", "subdomain": "bridge", "answer": "CIP-25/CNT native Cardano assets", "answer_type": "string", "source": "Charms Cardano Integration", "tags": ["cardano", "cip-25", "native-token", "cross-chain"], "volatility": "stable"},
    {"fact": "All three chains (BTC, ADA, Night) share UTXO model compatibility", "domain": "cross_chain", "subdomain": "protocol", "answer": "UTXO model shared across Bitcoin, Cardano, and Midnight", "answer_type": "string", "source": "UTXO Alliance", "tags": ["utxo", "compatibility", "cross-chain"], "volatility": "stable"},
    {"fact": "Cross-chain spells are the coordination primitive between chains in autono", "domain": "cross_chain", "subdomain": "protocol", "answer": "Spell = universal cross-chain instruction format (CBOR-encoded)", "answer_type": "string", "source": "Autono Architecture", "tags": ["spell", "coordination", "cross-chain", "cbor"], "volatility": "stable"},
    {"fact": "ZK proofs serve as the universal verification layer across all chains", "domain": "cross_chain", "subdomain": "protocol", "answer": "Groth16 ZK proofs verify cross-chain state transitions", "answer_type": "string", "source": "BitcoinOS + Charms", "tags": ["zk-proof", "verification", "groth16", "cross-chain"], "volatility": "stable"},
    {"fact": "Bitcoin to L2 via Grail Bridge: lock BTC in Taproot → mint zkBTC", "domain": "cross_chain", "subdomain": "bridge", "answer": "Lock BTC (Taproot) → ZK verify → Mint zkBTC on L2", "answer_type": "string", "source": "BitcoinOS Grail Bridge", "tags": ["grail", "bridge", "btc", "zkbtc", "l2"], "volatility": "stable"},
]


# ============================================================================
# MASTER REGISTRIES
# ============================================================================

CARDANO_FACTS: list[ProtocolFact] = (
    _CARDANO_PROTOCOL + _CARDANO_ADDRESSES + _CARDANO_CIPS +
    _CARDANO_PLUTUS + _CARDANO_SDK + _CARDANO_API + _CARDANO_GOVERNANCE
)

BITCOIN_FACTS: list[ProtocolFact] = (
    _BITCOIN_PROTOCOL + _BITCOIN_ADDRESSES + _BITCOIN_BIPS +
    _BITCOIN_SCRIPT + _BITCOIN_API
)

CHARMS_FACTS: list[ProtocolFact] = _CHARMS_PROTOCOL

BITCOINOS_FACTS: list[ProtocolFact] = _BITCOINOS_PROTOCOL

NIGHT_CHAIN_FACTS: list[ProtocolFact] = _NIGHT_CHAIN_PROTOCOL

CROSS_CHAIN_FACTS: list[ProtocolFact] = _CROSS_CHAIN

ALL_PROTOCOL_FACTS: list[ProtocolFact] = (
    CARDANO_FACTS + BITCOIN_FACTS + CHARMS_FACTS +
    BITCOINOS_FACTS + NIGHT_CHAIN_FACTS + CROSS_CHAIN_FACTS
)

FACTS_BY_DOMAIN: dict[str, list[ProtocolFact]] = {
    "cardano": CARDANO_FACTS,
    "bitcoin": BITCOIN_FACTS,
    "charms": CHARMS_FACTS,
    "bitcoinos": BITCOINOS_FACTS,
    "night_chain": NIGHT_CHAIN_FACTS,
    "cross_chain": CROSS_CHAIN_FACTS,
}


# ============================================================================
# Utility Functions
# ============================================================================

def get_facts_by_volatility(tier: str) -> list[ProtocolFact]:
    """Get all facts matching a volatility tier."""
    return [f for f in ALL_PROTOCOL_FACTS if f.get("volatility") == tier]


def get_facts_by_domain(domain: str) -> list[ProtocolFact]:
    """Get all facts for a domain."""
    return FACTS_BY_DOMAIN.get(domain, [])


def get_facts_by_tag(tag: str) -> list[ProtocolFact]:
    """Get all facts containing a specific tag."""
    return [f for f in ALL_PROTOCOL_FACTS if tag in f.get("tags", [])]


def get_facts_count() -> dict[str, int]:
    """Get count of facts per domain and total."""
    counts = {domain: len(facts) for domain, facts in FACTS_BY_DOMAIN.items()}
    counts["total"] = len(ALL_PROTOCOL_FACTS)
    return counts


def get_volatility_breakdown() -> dict[str, int]:
    """Get count of facts per volatility tier."""
    breakdown: dict[str, int] = {}
    for fact in ALL_PROTOCOL_FACTS:
        tier = fact.get("volatility", "unknown")
        breakdown[tier] = breakdown.get(tier, 0) + 1
    return breakdown
