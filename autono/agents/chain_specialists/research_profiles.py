"""Research profiles — god-level source configurations for each chain agent.

Each chain agent is a domain expert. These profiles define exactly:
- WHERE to scrape (URLs, repos, API endpoints)
- HOW to parse (CSS selectors, content areas)
- WHAT to extract (regex patterns for lockable facts)
- HOW DEEP to go (max depth, follow links)

When ResearchManager receives a research request from a chain agent,
it uses these profiles to scrape with surgical precision.
"""

from __future__ import annotations

from autono.services.scraper import ResearchSource


# ============================================================================
# CARDANO — eUTXO, CIPs, Plutus, MeshJS, Blockfrost, Opshin, Helios
# ============================================================================

CARDANO_SOURCES: list[ResearchSource] = [
    # Official docs
    ResearchSource(
        url="https://docs.cardano.org/about-cardano/introduction/",
        domain="cardano",
        subdomain="protocol",
        source_type="docs",
        selectors={"content": "main", "remove": "nav, footer, .sidebar"},
        extract_patterns=[
            {"pattern": r"(?:slot|epoch|block)\s*(?:time|length|duration)\s*(?:is|=|:)\s*(\d+\s*(?:seconds?|s|minutes?|m))", "type": "string", "tags": ["protocol", "timing"]},
            {"pattern": r"(?:minimum|min)\s+(?:UTXO|utxo|fee|deposit)\s*(?:is|=|:)\s*(\d[\d,]*\s*(?:lovelace|ADA)?)", "type": "string", "tags": ["protocol", "parameters"]},
        ],
        tags=["cardano", "protocol", "introduction"],
        max_depth=2,
    ),
    # CIP standards
    ResearchSource(
        url="https://cips.cardano.org/",
        domain="cardano",
        subdomain="cip",
        source_type="spec",
        selectors={"content": "main"},
        extract_patterns=[
            {"pattern": r"CIP-(\d+)[:\s]+([^\n]{10,80})", "type": "string", "tags": ["cip", "standard"]},
            {"pattern": r"metadata\s+(?:label|key|tag)\s*(?:is|=|:)\s*(\d+)", "type": "integer", "tags": ["metadata", "cip"]},
        ],
        tags=["cardano", "cip", "standards"],
        max_depth=2,
    ),
    # Developer portal
    ResearchSource(
        url="https://developers.cardano.org/docs/get-started/",
        domain="cardano",
        subdomain="sdk",
        source_type="docs",
        selectors={"content": "article, main"},
        extract_patterns=[
            {"pattern": r"cardano-cli\s+(\w+(?:\s+\w+){0,3})", "type": "string", "tags": ["cli", "command"]},
            {"pattern": r"--([a-z-]+)\s+<([^>]+)>", "type": "string", "tags": ["cli", "parameter"]},
        ],
        tags=["cardano", "developer", "getting-started"],
        max_depth=2,
    ),
    # MeshJS SDK
    ResearchSource(
        url="https://meshjs.dev/apis",
        domain="cardano",
        subdomain="sdk",
        source_type="docs",
        selectors={"content": "main"},
        extract_patterns=[
            {"pattern": r"(?:new\s+)?Mesh\w+\(([^)]*)\)", "type": "string", "tags": ["meshjs", "api"]},
            {"pattern": r"(?:import|from)\s+['\"]@meshsdk/(\w+)['\"]", "type": "string", "tags": ["meshjs", "import"]},
        ],
        tags=["cardano", "meshjs", "sdk", "javascript"],
        max_depth=2,
    ),
    # Blockfrost API
    ResearchSource(
        url="https://docs.blockfrost.io/",
        domain="cardano",
        subdomain="api",
        source_type="api",
        selectors={"content": "main"},
        extract_patterns=[
            {"pattern": r"(GET|POST|PUT|DELETE)\s+(/\w[\w/{}.-]+)", "type": "endpoint", "tags": ["blockfrost", "api"]},
            {"pattern": r"(?:rate\s+limit|ratelimit)\s*(?:is|=|:)\s*(\d+\s*(?:requests?|req)/\w+)", "type": "string", "tags": ["api", "rate-limit"]},
        ],
        tags=["cardano", "blockfrost", "api"],
        max_depth=2,
    ),
    # Opshin (Python smart contracts)
    ResearchSource(
        url="https://github.com/OpShin/opshin",
        domain="cardano",
        subdomain="sdk",
        source_type="github",
        extract_patterns=[
            {"pattern": r"opshin\s+(\w+)\s+([^\n]{5,60})", "type": "string", "tags": ["opshin", "command"]},
        ],
        tags=["cardano", "opshin", "python", "smart-contract", "plutus"],
        max_depth=1,
        follow_links=False,
    ),
    # Helios (JS smart contracts)
    ResearchSource(
        url="https://github.com/Hyperion-BT/helios",
        domain="cardano",
        subdomain="sdk",
        source_type="github",
        tags=["cardano", "helios", "javascript", "smart-contract"],
        max_depth=1,
        follow_links=False,
    ),
    # Koios API
    ResearchSource(
        url="https://api.koios.rest/",
        domain="cardano",
        subdomain="api",
        source_type="api",
        extract_patterns=[
            {"pattern": r"(GET|POST)\s+(/\w[\w/{}.-]+)", "type": "endpoint", "tags": ["koios", "api"]},
        ],
        tags=["cardano", "koios", "api"],
        max_depth=1,
    ),
]


# ============================================================================
# BITCOIN — UTXO, BIPs, Taproot, PSBT, Ordinals, Lightning
# ============================================================================

BITCOIN_SOURCES: list[ResearchSource] = [
    # Bitcoin developer reference
    ResearchSource(
        url="https://developer.bitcoin.org/reference/",
        domain="bitcoin",
        subdomain="protocol",
        source_type="docs",
        selectors={"content": "main, .body-content"},
        extract_patterns=[
            {"pattern": r"OP_([A-Z_]+)\s*\(?(0x[0-9a-fA-F]+)?\)?", "type": "string", "tags": ["opcode", "script"]},
            {"pattern": r"(?:BIP|bip)[- ]?(\d+)\s*[-:]\s*([^\n]{5,80})", "type": "string", "tags": ["bip", "standard"]},
            {"pattern": r"(?:max|maximum)\s+(?:block\s+)?(?:size|weight)\s*(?:is|=|:)\s*(\d[\d,]*\s*\w*)", "type": "string", "tags": ["protocol", "limit"]},
        ],
        tags=["bitcoin", "developer", "reference"],
        max_depth=2,
    ),
    # BIP repository
    ResearchSource(
        url="https://github.com/bitcoin/bips",
        domain="bitcoin",
        subdomain="bip",
        source_type="github",
        extract_patterns=[
            {"pattern": r"BIP:\s*(\d+)", "type": "integer", "tags": ["bip", "number"]},
            {"pattern": r"Status:\s*(\w+)", "type": "string", "tags": ["bip", "status"]},
            {"pattern": r"Type:\s*(\w[\w\s]+)", "type": "string", "tags": ["bip", "type"]},
        ],
        tags=["bitcoin", "bip", "standards"],
        max_depth=1,
        follow_links=False,
    ),
    # Bitcoin Wiki (Script)
    ResearchSource(
        url="https://en.bitcoin.it/wiki/Script",
        domain="bitcoin",
        subdomain="protocol",
        source_type="docs",
        selectors={"content": "#mw-content-text"},
        extract_patterns=[
            {"pattern": r"OP_([A-Z_]+)\s+(\(0x[0-9a-fA-F]+\)|\d+)", "type": "string", "tags": ["opcode"]},
        ],
        tags=["bitcoin", "script", "opcodes"],
        max_depth=1,
    ),
    # Bitcoin Core RPC
    ResearchSource(
        url="https://developer.bitcoin.org/reference/rpc/",
        domain="bitcoin",
        subdomain="api",
        source_type="api",
        extract_patterns=[
            {"pattern": r"(\w+)\s*(?:—|:)\s*([^\n]{10,80})", "type": "string", "tags": ["rpc", "command"]},
        ],
        tags=["bitcoin", "rpc", "api"],
        max_depth=2,
    ),
    # Taproot (BIP-340, 341, 342)
    ResearchSource(
        url="https://bitcoinops.org/en/topics/taproot/",
        domain="bitcoin",
        subdomain="protocol",
        source_type="docs",
        extract_patterns=[
            {"pattern": r"(?:Schnorr|schnorr)\s+([^\n]{5,60})", "type": "string", "tags": ["taproot", "schnorr"]},
            {"pattern": r"witness\s+(?:version|v)\s*(\d+)", "type": "integer", "tags": ["taproot", "witness"]},
        ],
        tags=["bitcoin", "taproot", "schnorr", "bip-340", "bip-341"],
        max_depth=1,
    ),
    # PSBT specification
    ResearchSource(
        url="https://bitcoinops.org/en/topics/psbt/",
        domain="bitcoin",
        subdomain="protocol",
        source_type="docs",
        tags=["bitcoin", "psbt", "transaction"],
        max_depth=1,
    ),
    # Mempool.space API
    ResearchSource(
        url="https://mempool.space/docs/api/rest",
        domain="bitcoin",
        subdomain="api",
        source_type="api",
        extract_patterns=[
            {"pattern": r"(GET|POST)\s+(/api/[\w/{}.-]+)", "type": "endpoint", "tags": ["mempool", "api"]},
        ],
        tags=["bitcoin", "mempool", "api", "fees"],
        max_depth=2,
    ),
]


# ============================================================================
# CHARMS — Programmable tokens on Bitcoin, spells, apps
# ============================================================================

CHARMS_SOURCES: list[ResearchSource] = [
    # Charms documentation
    ResearchSource(
        url="https://docs.charms.dev/",
        domain="charms",
        subdomain="protocol",
        source_type="docs",
        selectors={"content": "main, article"},
        extract_patterns=[
            {"pattern": r"charms?\s+(?:app|spell)\s+(\w+)\s*([^\n]{5,60})?", "type": "string", "tags": ["cli", "command"]},
            {"pattern": r"(?:tag|type)\s*['\"]([nt])['\"]", "type": "string", "tags": ["charm", "tag"]},
            {"pattern": r"app_contract\s*\(([^)]*)\)", "type": "string", "tags": ["contract", "entry-point"]},
        ],
        tags=["charms", "documentation", "protocol"],
        max_depth=3,
    ),
    # Charms website
    ResearchSource(
        url="https://charms.dev/",
        domain="charms",
        subdomain="protocol",
        source_type="docs",
        tags=["charms", "overview"],
        max_depth=1,
    ),
    # Charms GitHub
    ResearchSource(
        url="https://github.com/proven-network/charms",
        domain="charms",
        subdomain="development",
        source_type="github",
        extract_patterns=[
            {"pattern": r"(?:struct|enum|fn)\s+(\w+)", "type": "string", "tags": ["rust", "api"]},
        ],
        tags=["charms", "rust", "source-code"],
        max_depth=1,
        follow_links=False,
    ),
]


# ============================================================================
# BITCOINOS — Grail Bridge, BitSNARK, zkBTC, MerkleMesh
# ============================================================================

BITCOINOS_SOURCES: list[ResearchSource] = [
    # BitcoinOS documentation
    ResearchSource(
        url="https://docs.bitcoinos.build/",
        domain="bitcoinos",
        subdomain="protocol",
        source_type="docs",
        selectors={"content": "main, article"},
        extract_patterns=[
            {"pattern": r"(?:Grail|grail)\s+(?:Bridge|bridge)\s+([^\n]{5,80})", "type": "string", "tags": ["grail", "bridge"]},
            {"pattern": r"(?:BitSNARK|bitsnark)\s+([^\n]{5,60})", "type": "string", "tags": ["bitsnark", "zk"]},
            {"pattern": r"zkBTC\s+([^\n]{5,60})", "type": "string", "tags": ["zkbtc"]},
        ],
        tags=["bitcoinos", "grail-bridge", "bitsnark"],
        max_depth=3,
    ),
    # BitcoinOS website
    ResearchSource(
        url="https://www.bitcoinos.build/",
        domain="bitcoinos",
        subdomain="protocol",
        source_type="docs",
        tags=["bitcoinos", "overview"],
        max_depth=1,
    ),
    # BitcoinOS GitHub
    ResearchSource(
        url="https://github.com/BitcoinOS-Labs",
        domain="bitcoinos",
        subdomain="development",
        source_type="github",
        tags=["bitcoinos", "source-code"],
        max_depth=1,
        follow_links=False,
    ),
]


# ============================================================================
# NIGHT CHAIN — Midnight, ZK privacy, encrypted state
# ============================================================================

NIGHT_CHAIN_SOURCES: list[ResearchSource] = [
    # Midnight (IOG privacy sidechain)
    ResearchSource(
        url="https://midnight.network/",
        domain="night_chain",
        subdomain="protocol",
        source_type="docs",
        extract_patterns=[
            {"pattern": r"(?:Compact|compact)\s+([^\n]{5,60})", "type": "string", "tags": ["compact", "language"]},
            {"pattern": r"(?:zero.knowledge|ZK|zk)\s+([^\n]{5,60})", "type": "string", "tags": ["zk", "privacy"]},
        ],
        tags=["night-chain", "midnight", "privacy", "zk"],
        max_depth=2,
    ),
    # Midnight docs
    ResearchSource(
        url="https://docs.midnight.network/",
        domain="night_chain",
        subdomain="sdk",
        source_type="docs",
        selectors={"content": "main, article"},
        extract_patterns=[
            {"pattern": r"(?:Ed25519|ed25519)\s+([^\n]{5,40})", "type": "string", "tags": ["cryptography"]},
            {"pattern": r"(?:AES|aes)[- ]?(\d+)[- ]?(GCM|CBC|CTR)?", "type": "string", "tags": ["encryption"]},
        ],
        tags=["night-chain", "midnight", "documentation"],
        max_depth=2,
    ),
]


# ============================================================================
# PROFILE REGISTRY — maps agent names to their research sources
# ============================================================================

RESEARCH_PROFILES: dict[str, list[ResearchSource]] = {
    "CardanoChainAgent": CARDANO_SOURCES,
    "BitcoinChainAgent": BITCOIN_SOURCES,
    "CharmsAgent": CHARMS_SOURCES + BITCOINOS_SOURCES,
    "NightChainAgent": NIGHT_CHAIN_SOURCES,
}

# Domain → sources mapping for ResearchManager
DOMAIN_SOURCES: dict[str, list[ResearchSource]] = {
    "cardano": CARDANO_SOURCES,
    "bitcoin": BITCOIN_SOURCES,
    "charms": CHARMS_SOURCES,
    "bitcoinos": BITCOINOS_SOURCES,
    "night_chain": NIGHT_CHAIN_SOURCES,
}


def get_sources_for_agent(agent_name: str) -> list[ResearchSource]:
    """Get all research sources for a chain agent."""
    return RESEARCH_PROFILES.get(agent_name, [])


def get_sources_for_domain(domain: str) -> list[ResearchSource]:
    """Get all research sources for a knowledge domain."""
    return DOMAIN_SOURCES.get(domain, [])


def get_all_sources() -> list[ResearchSource]:
    """Get all research sources across all domains."""
    all_sources = []
    seen_urls = set()
    for sources in DOMAIN_SOURCES.values():
        for source in sources:
            if source.url not in seen_urls:
                seen_urls.add(source.url)
                all_sources.append(source)
    return all_sources
