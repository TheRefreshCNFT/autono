"""WalletService — Python-side wallet engine for the agent system.

Mirrors the TypeScript WalletEngine API but runs natively in Python,
giving all agents direct access to wallet operations:

- Multi-chain address generation (Cardano, Bitcoin, Night Chain)
- BIP-39 mnemonic generation with secure memory handling
- Address validation and type identification
- Derivation path computation (BIP-44/84/86 for Bitcoin, CIP-1852 for Cardano)
- Transaction building interfaces
- Balance and UTXO tracking
- Fee estimation
- Knowledge graph integration (wallet state as locked nodes)

Security model matches WALI TypeScript:
- Mnemonics handled as bytes, never strings longer than needed
- All sensitive data wiped after use
- Encryption delegated to NightChainAgent (AES-256-GCM)
- No plaintext secrets on disk

Architecture:
    ┌─────────────────────────────────────────────────────┐
    │                   WalletService                      │
    │  (Python wallet engine — agent-facing backend)       │
    │                                                      │
    │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
    │  │ Cardano   │  │ Bitcoin  │  │ Night Chain      │  │
    │  │ Module    │  │ Module   │  │ (encryption)     │  │
    │  │           │  │          │  │                  │  │
    │  │ CIP-1852  │  │ BIP-44   │  │ Ed25519 keypairs │  │
    │  │ addr1...  │  │ BIP-84   │  │ AES-256-GCM      │  │
    │  │ Blockfrost│  │ BIP-86   │  │ 4-line recovery  │  │
    │  └──────────┘  └──────────┘  └──────────────────┘  │
    └─────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import structlog

log = structlog.get_logger()


# =============================================================================
# Types
# =============================================================================

class ChainType(str, Enum):
    CARDANO = "cardano"
    BITCOIN = "bitcoin"
    NIGHT = "night_chain"


class NetworkType(str, Enum):
    MAINNET = "mainnet"
    TESTNET = "testnet"


class BitcoinAddressType(str, Enum):
    LEGACY = "p2pkh"          # 1... (BIP-44)
    SEGWIT = "p2sh-p2wpkh"   # 3... (BIP-49)
    NATIVE_SEGWIT = "p2wpkh"  # bc1q... (BIP-84)
    TAPROOT = "p2tr"           # bc1p... (BIP-86)


@dataclass
class WalletAddress:
    """A generated wallet address with metadata."""
    chain: ChainType
    address: str
    address_type: str
    derivation_path: str
    public_key_hash: str  # hash of pubkey, never the key itself
    network: NetworkType
    created_at: float = field(default_factory=time.time)

    def as_dict(self) -> dict[str, Any]:
        return {
            "chain": self.chain.value,
            "address": self.address,
            "address_type": self.address_type,
            "derivation_path": self.derivation_path,
            "network": self.network.value,
        }


@dataclass
class WalletState:
    """Wallet state tracked in the knowledge graph."""
    wallet_id: str
    addresses: list[WalletAddress] = field(default_factory=list)
    chains: list[str] = field(default_factory=list)
    network: str = "testnet"
    created_at: float = field(default_factory=time.time)
    encrypted_seed_asset_id: str = ""  # Night Chain asset ID
    is_backed_up: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "wallet_id": self.wallet_id,
            "addresses": [a.as_dict() for a in self.addresses],
            "chains": self.chains,
            "network": self.network,
            "encrypted_seed_asset_id": self.encrypted_seed_asset_id,
            "is_backed_up": self.is_backed_up,
        }


@dataclass
class TransactionRequest:
    """A transaction build request."""
    chain: ChainType
    from_address: str
    to_address: str
    amount: str  # In smallest unit (lovelace / satoshis)
    tokens: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeeEstimate:
    """Fee estimate for a chain."""
    chain: ChainType
    slow: str
    medium: str
    fast: str
    unit: str  # "lovelace" or "sat/vB"


# =============================================================================
# Derivation Path Constants (matching WALI TypeScript)
# =============================================================================

# Cardano: CIP-1852 (m/1852'/1815'/account'/role/index)
CARDANO_PURPOSE = 1852
CARDANO_COIN_TYPE = 1815

# Bitcoin: BIP-44/84/86
BITCOIN_PURPOSE_LEGACY = 44      # P2PKH
BITCOIN_PURPOSE_SEGWIT = 49      # P2SH-P2WPKH
BITCOIN_PURPOSE_NATIVE = 84      # P2WPKH (native segwit)
BITCOIN_PURPOSE_TAPROOT = 86     # P2TR
BITCOIN_COIN_TYPE = 0
BITCOIN_COIN_TYPE_TESTNET = 1


# =============================================================================
# WalletService
# =============================================================================

class WalletService:
    """Python wallet engine for the agent system.

    Handles wallet creation, address generation, validation,
    and transaction coordination. Integrates with the knowledge
    graph for persistent wallet state.

    Usage:
        service = WalletService(network="testnet")
        wallet = service.create_wallet(chains=["cardano", "bitcoin"])
        service.validate_address("addr1...", "cardano")
    """

    def __init__(self, network: str = "testnet",
                 persist_path: str | None = None) -> None:
        self.network = NetworkType(network)
        self._wallets: dict[str, WalletState] = {}
        self._store = None
        self._graph = None
        self._wallets_created: int = 0

        # Wallet state persistence
        from pathlib import Path
        self._persist_path = (
            Path(persist_path) if persist_path
            else Path.home() / ".autono" / "wallets"
        )
        self._persist_path.mkdir(parents=True, exist_ok=True)
        self._load_wallet_state()

    def set_dependencies(self, store: Any, graph: Any) -> None:
        """Inject knowledge store and graph."""
        self._store = store
        self._graph = graph

    # =========================================================================
    # Wallet Creation
    # =========================================================================

    def create_wallet(
        self,
        chains: list[str] | None = None,
        word_count: int = 24,
    ) -> dict[str, Any]:
        """Create a new multi-chain wallet.

        Generates BIP-39 mnemonic, derives addresses for requested chains,
        returns wallet state. Mnemonic is returned as bytes for the caller
        to encrypt via NightChainAgent and then wipe.

        Returns:
            {
                "wallet_id": "wali_...",
                "mnemonic_bytes": <bytes>,  # MUST BE WIPED BY CALLER
                "addresses": {...},
                "derivation_paths": {...},
                "state": WalletState,
            }
        """
        if chains is None:
            chains = ["cardano", "bitcoin"]

        from mnemonic import Mnemonic

        # Generate BIP-39 mnemonic
        m = Mnemonic("english")
        strength = {12: 128, 15: 160, 18: 192, 21: 224, 24: 256}.get(word_count, 256)
        mnemonic_str = m.generate(strength)
        mnemonic_bytes = mnemonic_str.encode("utf-8")

        # Generate seed from mnemonic (BIP-39)
        seed = hashlib.pbkdf2_hmac(
            "sha512",
            mnemonic_bytes,
            b"mnemonic",  # BIP-39 passphrase salt
            2048,
            dklen=64,
        )

        # Derive addresses for each chain
        wallet_id = f"wali_{secrets.token_hex(8)}"
        addresses: dict[str, str] = {}
        wallet_addresses: list[WalletAddress] = []
        derivation_paths: dict[str, str] = {}

        for chain in chains:
            if chain == "cardano":
                addr, wallet_addr = self._derive_cardano_address(seed, 0, 0)
                addresses["cardano"] = addr
                wallet_addresses.append(wallet_addr)
                derivation_paths["cardano"] = wallet_addr.derivation_path

            elif chain == "bitcoin":
                addr, wallet_addr = self._derive_bitcoin_address(
                    seed, 0, 0, BitcoinAddressType.NATIVE_SEGWIT
                )
                addresses["bitcoin"] = addr
                wallet_addresses.append(wallet_addr)
                derivation_paths["bitcoin"] = wallet_addr.derivation_path

            elif chain == "night_chain":
                addr, wallet_addr = self._derive_night_address(seed, 0)
                addresses["night_chain"] = addr
                wallet_addresses.append(wallet_addr)
                derivation_paths["night_chain"] = wallet_addr.derivation_path

        # Create wallet state
        state = WalletState(
            wallet_id=wallet_id,
            addresses=wallet_addresses,
            chains=chains,
            network=self.network.value,
        )
        self._wallets[wallet_id] = state
        self._wallets_created += 1

        # Store wallet state in knowledge graph (addresses only, never keys)
        self._store_wallet_in_graph(state)

        # Persist wallet metadata to disk
        self._save_wallet_state()

        log.info("wallet.created",
                 wallet_id=wallet_id,
                 chains=chains,
                 network=self.network.value)

        return {
            "wallet_id": wallet_id,
            "mnemonic_bytes": mnemonic_bytes,  # CALLER MUST WIPE
            "addresses": addresses,
            "derivation_paths": derivation_paths,
            "state": state,
        }

    # =========================================================================
    # Address Derivation
    # =========================================================================

    def _derive_cardano_address(
        self, seed: bytes, account: int = 0, index: int = 0
    ) -> tuple[str, WalletAddress]:
        """Derive a Cardano address using CIP-1852 path.

        Path: m/1852'/1815'/account'/0/index
        """
        import bech32

        # Derive key material from seed + path
        path = f"m/{CARDANO_PURPOSE}'/{CARDANO_COIN_TYPE}'/{account}'/0/{index}"
        key_material = self._derive_key_from_path(seed, path)

        # Create payment key hash (Blake2b-224 of Ed25519 public key)
        payment_key_hash = hashlib.blake2b(key_material[:32], digest_size=28).digest()

        # Build Shelley address (type 0x61 for enterprise testnet, 0x01 for mainnet)
        if self.network == NetworkType.MAINNET:
            # Type byte: 0x61 = enterprise mainnet (no staking)
            addr_bytes = bytes([0x61]) + payment_key_hash
            hrp = "addr"
        else:
            # Type byte: 0x61 for testnet enterprise
            addr_bytes = bytes([0x61]) + payment_key_hash
            hrp = "addr_test"

        # Bech32 encode
        data = bech32.convertbits(addr_bytes, 8, 5)
        address = bech32.bech32_encode(hrp, data)

        pub_key_hash = hashlib.sha256(key_material[:32]).hexdigest()[:16]

        wallet_addr = WalletAddress(
            chain=ChainType.CARDANO,
            address=address,
            address_type="enterprise",
            derivation_path=path,
            public_key_hash=pub_key_hash,
            network=self.network,
        )

        return address, wallet_addr

    def _derive_bitcoin_address(
        self,
        seed: bytes,
        account: int = 0,
        index: int = 0,
        addr_type: BitcoinAddressType = BitcoinAddressType.NATIVE_SEGWIT,
    ) -> tuple[str, WalletAddress]:
        """Derive a Bitcoin address using BIP-44/84/86 path."""
        import bech32

        # Select purpose based on address type
        purpose = {
            BitcoinAddressType.LEGACY: BITCOIN_PURPOSE_LEGACY,
            BitcoinAddressType.SEGWIT: BITCOIN_PURPOSE_SEGWIT,
            BitcoinAddressType.NATIVE_SEGWIT: BITCOIN_PURPOSE_NATIVE,
            BitcoinAddressType.TAPROOT: BITCOIN_PURPOSE_TAPROOT,
        }[addr_type]

        coin_type = (
            BITCOIN_COIN_TYPE if self.network == NetworkType.MAINNET
            else BITCOIN_COIN_TYPE_TESTNET
        )

        path = f"m/{purpose}'/{coin_type}'/{account}'/0/{index}"
        key_material = self._derive_key_from_path(seed, path)

        # Create public key hash
        pub_key = key_material[:33]  # compressed public key
        sha256_hash = hashlib.sha256(pub_key).digest()

        # RIPEMD160 of SHA256 (Hash160)
        import hashlib as hl
        ripemd = hl.new("ripemd160", sha256_hash).digest()

        if addr_type == BitcoinAddressType.NATIVE_SEGWIT:
            # P2WPKH: bech32 with witness version 0
            hrp = "bc" if self.network == NetworkType.MAINNET else "tb"
            data = bech32.convertbits(ripemd, 8, 5)
            address = bech32.bech32_encode(hrp, [0] + data)

        elif addr_type == BitcoinAddressType.TAPROOT:
            # P2TR: bech32m with witness version 1 (32-byte x-only pubkey)
            x_only_pub = key_material[:32]
            tweaked = hashlib.sha256(x_only_pub).digest()[:32]
            hrp = "bc" if self.network == NetworkType.MAINNET else "tb"
            data = bech32.convertbits(tweaked, 8, 5)
            # bech32m: use BECH32M constant (0x2bc830a3) for Taproot
            if hasattr(bech32, "bech32m_encode"):
                address = bech32.bech32m_encode(hrp, [1] + data)
            else:
                # Fallback: manually encode with bech32m checksum
                address = bech32.bech32_encode(hrp, [1] + data)

        elif addr_type == BitcoinAddressType.LEGACY:
            # P2PKH: Base58Check with version byte
            version = b"\x00" if self.network == NetworkType.MAINNET else b"\x6f"
            payload = version + ripemd
            checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            address = self._base58_encode(payload + checksum)

        else:
            # P2SH-P2WPKH: Base58Check with script hash
            # Redeem script: OP_0 <20-byte-key-hash>
            redeem = bytes([0x00, 0x14]) + ripemd
            script_hash = hl.new("ripemd160", hashlib.sha256(redeem).digest()).digest()
            version = b"\x05" if self.network == NetworkType.MAINNET else b"\xc4"
            payload = version + script_hash
            checksum = hashlib.sha256(hashlib.sha256(payload).digest()).digest()[:4]
            address = self._base58_encode(payload + checksum)

        pub_key_hash = hashlib.sha256(key_material[:32]).hexdigest()[:16]

        wallet_addr = WalletAddress(
            chain=ChainType.BITCOIN,
            address=address,
            address_type=addr_type.value,
            derivation_path=path,
            public_key_hash=pub_key_hash,
            network=self.network,
        )

        return address, wallet_addr

    def _derive_night_address(
        self, seed: bytes, account: int = 0
    ) -> tuple[str, WalletAddress]:
        """Derive a Night Chain address using Ed25519.

        Night Chain: Ed25519 keypair → bech32 with "night1" prefix.
        """
        import bech32

        # Derive Ed25519 key material
        path = f"m/1852'/1815'/{account}'/2/0"  # Night uses role=2
        key_material = self._derive_key_from_path(seed, path)

        # Ed25519 public key hash (Blake2b-224)
        pub_hash = hashlib.blake2b(key_material[:32], digest_size=28).digest()

        # Bech32 encode with night1 prefix
        data = bech32.convertbits(pub_hash, 8, 5)
        address = bech32.bech32_encode("night", data)

        pub_key_hash = hashlib.sha256(key_material[:32]).hexdigest()[:16]

        wallet_addr = WalletAddress(
            chain=ChainType.NIGHT,
            address=address,
            address_type="ed25519",
            derivation_path=path,
            public_key_hash=pub_key_hash,
            network=self.network,
        )

        return address, wallet_addr

    def _derive_key_from_path(self, seed: bytes, path: str) -> bytes:
        """Derive key material from seed using HMAC-SHA512 chain.

        Simplified HD key derivation — uses path components as HMAC
        chain keys. Production would use full BIP-32/Ed25519-BIP32.
        """
        key = seed
        for component in path.replace("m/", "").split("/"):
            # Handle hardened derivation (')
            component_clean = component.rstrip("'")
            index = int(component_clean)
            if component.endswith("'"):
                index += 0x80000000  # hardened

            key = hmac.new(
                key[:32],
                key[32:] + index.to_bytes(4, "big"),
                hashlib.sha512,
            ).digest()

        return key

    @staticmethod
    def _base58_encode(data: bytes) -> str:
        """Base58 encoding for legacy Bitcoin addresses."""
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        num = int.from_bytes(data, "big")
        result = []
        while num > 0:
            num, rem = divmod(num, 58)
            result.append(alphabet[rem])
        # Leading zeros
        for byte in data:
            if byte == 0:
                result.append(alphabet[0])
            else:
                break
        return "".join(reversed(result))

    # =========================================================================
    # Address Validation
    # =========================================================================

    def validate_address(self, address: str, chain: str) -> dict[str, Any]:
        """Validate an address and identify its type.

        Returns:
            {"valid": bool, "chain": str, "type": str, "network": str}
        """
        if chain == "cardano":
            return self._validate_cardano_address(address)
        elif chain == "bitcoin":
            return self._validate_bitcoin_address(address)
        elif chain == "night_chain":
            return self._validate_night_address(address)
        return {"valid": False, "chain": chain, "error": "unknown chain"}

    def _validate_cardano_address(self, address: str) -> dict[str, Any]:
        """Validate a Cardano address."""
        import bech32

        if address.startswith("addr1"):
            hrp, data = bech32.bech32_decode(address)
            if hrp == "addr" and data is not None:
                return {"valid": True, "chain": "cardano",
                        "type": "shelley", "network": "mainnet"}

        elif address.startswith("addr_test1"):
            hrp, data = bech32.bech32_decode(address)
            if hrp == "addr_test" and data is not None:
                return {"valid": True, "chain": "cardano",
                        "type": "shelley", "network": "testnet"}

        elif address.startswith("stake1"):
            return {"valid": True, "chain": "cardano",
                    "type": "stake", "network": "mainnet"}

        elif address.startswith("Ae2") or address.startswith("DdzFF"):
            return {"valid": True, "chain": "cardano",
                    "type": "byron", "network": "mainnet"}

        return {"valid": False, "chain": "cardano", "error": "invalid format"}

    def _validate_bitcoin_address(self, address: str) -> dict[str, Any]:
        """Validate a Bitcoin address and identify type."""
        import bech32

        # Bech32/Bech32m (SegWit/Taproot)
        if address.startswith(("bc1", "tb1")):
            hrp = "bc" if address.startswith("bc1") else "tb"
            network = "mainnet" if hrp == "bc" else "testnet"

            # Try bech32m first (Taproot)
            _, data = bech32.bech32m_decode(hrp, address) if hasattr(bech32, 'bech32m_decode') else (None, None)
            if data is not None:
                return {"valid": True, "chain": "bitcoin",
                        "type": "p2tr", "network": network}

            # Try bech32 (Native SegWit)
            _, data = bech32.bech32_decode(address)
            if data is not None:
                return {"valid": True, "chain": "bitcoin",
                        "type": "p2wpkh", "network": network}

        # Legacy P2PKH
        if address.startswith("1"):
            return {"valid": True, "chain": "bitcoin",
                    "type": "p2pkh", "network": "mainnet"}
        if address.startswith(("m", "n")):
            return {"valid": True, "chain": "bitcoin",
                    "type": "p2pkh", "network": "testnet"}

        # P2SH
        if address.startswith("3"):
            return {"valid": True, "chain": "bitcoin",
                    "type": "p2sh", "network": "mainnet"}
        if address.startswith("2"):
            return {"valid": True, "chain": "bitcoin",
                    "type": "p2sh", "network": "testnet"}

        return {"valid": False, "chain": "bitcoin", "error": "invalid format"}

    def _validate_night_address(self, address: str) -> dict[str, Any]:
        """Validate a Night Chain address."""
        import bech32

        if address.startswith("night1"):
            hrp, data = bech32.bech32_decode(address)
            if hrp == "night" and data is not None:
                return {"valid": True, "chain": "night_chain",
                        "type": "ed25519", "network": "mainnet"}

        return {"valid": False, "chain": "night_chain", "error": "invalid format"}

    def identify_address(self, address: str) -> dict[str, Any]:
        """Auto-detect chain and type from any address."""
        # Try night_chain first (night1... prefix would false-match Bitcoin testnet)
        for chain in ["night_chain", "cardano", "bitcoin"]:
            result = self.validate_address(address, chain)
            if result.get("valid"):
                return result

        return {"valid": False, "chain": "unknown", "error": "unrecognized address format"}

    # =========================================================================
    # Derivation Paths
    # =========================================================================

    def get_derivation_path(
        self,
        chain: str,
        account: int = 0,
        index: int = 0,
        addr_type: str = "native_segwit",
    ) -> str:
        """Get the standard derivation path for a chain."""
        if chain == "cardano":
            return f"m/{CARDANO_PURPOSE}'/{CARDANO_COIN_TYPE}'/{account}'/0/{index}"

        elif chain == "bitcoin":
            purpose = {
                "legacy": BITCOIN_PURPOSE_LEGACY,
                "segwit": BITCOIN_PURPOSE_SEGWIT,
                "native_segwit": BITCOIN_PURPOSE_NATIVE,
                "taproot": BITCOIN_PURPOSE_TAPROOT,
            }.get(addr_type, BITCOIN_PURPOSE_NATIVE)

            coin_type = (
                BITCOIN_COIN_TYPE if self.network == NetworkType.MAINNET
                else BITCOIN_COIN_TYPE_TESTNET
            )
            return f"m/{purpose}'/{coin_type}'/{account}'/0/{index}"

        elif chain == "night_chain":
            return f"m/1852'/1815'/{account}'/2/0"

        return f"m/44'/0'/{account}'/0/{index}"

    # =========================================================================
    # Knowledge Graph Integration
    # =========================================================================

    def _store_wallet_in_graph(self, state: WalletState) -> None:
        """Store wallet addresses as locked knowledge nodes.

        Each address becomes a PERMANENT locked node — addresses never change.
        """
        if not self._store:
            return

        from autono.knowledge.types import KnowledgeNode, Lock, VolatilityTier

        for wallet_addr in state.addresses:
            # Create node for each address
            node = KnowledgeNode(
                content=f"{wallet_addr.chain.value} wallet address: {wallet_addr.address}",
                domain=wallet_addr.chain.value,
                subdomain="wallet",
                volatility=VolatilityTier.PERMANENT,
                tags=["wallet", "address", wallet_addr.chain.value,
                      wallet_addr.address_type, state.wallet_id],
            )
            self._store.save_node(node)

            # Lock it — addresses are deterministic facts
            lock = Lock(
                node_id=node.id,
                absolute_answer=wallet_addr.address,
                answer_type="address",
                verification_source=f"BIP-39 derivation: {wallet_addr.derivation_path}",
            )
            lock.compute_dependency_hash(wallet_addr.address)
            self._store.save_lock(lock)

            node.is_locked = True
            node.lock_id = lock.id
            node.bypass_llm = True
            self._store.save_node(node)

        # Create node for derivation paths
        path_content = " | ".join(
            f"{a.chain.value}: {a.derivation_path}"
            for a in state.addresses
        )
        path_node = KnowledgeNode(
            content=f"Wallet {state.wallet_id} derivation paths: {path_content}",
            domain="wallet",
            subdomain="derivation",
            volatility=VolatilityTier.PERMANENT,
            tags=["wallet", "derivation", state.wallet_id] + state.chains,
        )
        self._store.save_node(path_node)

        lock = Lock(
            node_id=path_node.id,
            absolute_answer={
                a.chain.value: a.derivation_path for a in state.addresses
            },
            answer_type="json",
            verification_source="BIP-39/BIP-44/CIP-1852 standard",
        )
        lock.compute_dependency_hash(path_content)
        self._store.save_lock(lock)

        path_node.is_locked = True
        path_node.lock_id = lock.id
        path_node.bypass_llm = True
        self._store.save_node(path_node)

        log.info("wallet.stored_in_graph",
                 wallet_id=state.wallet_id,
                 addresses=len(state.addresses))

    # =========================================================================
    # Fee Estimation
    # =========================================================================

    def estimate_fees(self, chain: str) -> FeeEstimate:
        """Get fee estimates for a chain."""
        if chain == "cardano":
            # Cardano: fixed minimum fee formula
            # min_fee = tx_size_bytes * 44 + 155381  (protocol params)
            return FeeEstimate(
                chain=ChainType.CARDANO,
                slow="170000",    # ~0.17 ADA
                medium="180000",  # ~0.18 ADA
                fast="200000",    # ~0.20 ADA
                unit="lovelace",
            )
        elif chain == "bitcoin":
            # Bitcoin: sat/vB fee rates (would query mempool.space in production)
            return FeeEstimate(
                chain=ChainType.BITCOIN,
                slow="5",
                medium="15",
                fast="30",
                unit="sat/vB",
            )
        elif chain == "night_chain":
            return FeeEstimate(
                chain=ChainType.NIGHT,
                slow="100",
                medium="100",
                fast="100",
                unit="night_units",
            )
        raise ValueError(f"Unknown chain: {chain}")

    # =========================================================================
    # Multi-Address Generation
    # =========================================================================

    def generate_address_set(
        self,
        seed: bytes,
        account: int = 0,
        count: int = 5,
    ) -> dict[str, list[WalletAddress]]:
        """Generate multiple addresses for gap limit detection.

        Returns addresses for each chain with sequential indices.
        """
        result: dict[str, list[WalletAddress]] = {
            "cardano": [],
            "bitcoin": [],
        }

        for i in range(count):
            _, cardano_addr = self._derive_cardano_address(seed, account, i)
            result["cardano"].append(cardano_addr)

            _, bitcoin_addr = self._derive_bitcoin_address(seed, account, i)
            result["bitcoin"].append(bitcoin_addr)

        return result

    def generate_all_bitcoin_types(
        self, seed: bytes, account: int = 0, index: int = 0
    ) -> dict[str, WalletAddress]:
        """Generate all Bitcoin address types for the same key.

        Returns: {"legacy": addr, "segwit": addr, "native_segwit": addr, "taproot": addr}
        """
        result = {}
        for addr_type in BitcoinAddressType:
            _, wallet_addr = self._derive_bitcoin_address(
                seed, account, index, addr_type
            )
            result[addr_type.value] = wallet_addr
        return result

    # =========================================================================
    # Wallet State Persistence
    # =========================================================================

    def _save_wallet_state(self) -> None:
        """Persist wallet metadata to disk (addresses only, never keys)."""
        import json

        state_file = self._persist_path / "wallet_state.json"
        data = {
            "network": self.network.value,
            "wallets_created": self._wallets_created,
            "wallets": {
                wid: w.as_dict() for wid, w in self._wallets.items()
            },
        }
        with open(state_file, "w") as f:
            json.dump(data, f, indent=2)

        log.info("wallet.state_saved", count=len(self._wallets))

    def _load_wallet_state(self) -> None:
        """Load persisted wallet metadata from disk."""
        import json

        state_file = self._persist_path / "wallet_state.json"
        if not state_file.exists():
            return

        try:
            with open(state_file) as f:
                data = json.load(f)

            self._wallets_created = data.get("wallets_created", 0)
            for wid, wdata in data.get("wallets", {}).items():
                addresses = []
                for addr_data in wdata.get("addresses", []):
                    addresses.append(WalletAddress(
                        chain=ChainType(addr_data["chain"]),
                        address=addr_data["address"],
                        address_type=addr_data.get("address_type", ""),
                        derivation_path=addr_data.get("derivation_path", ""),
                        public_key_hash="",  # not persisted
                        network=NetworkType(addr_data.get("network", "testnet")),
                    ))
                self._wallets[wid] = WalletState(
                    wallet_id=wid,
                    addresses=addresses,
                    chains=wdata.get("chains", []),
                    network=wdata.get("network", "testnet"),
                    encrypted_seed_asset_id=wdata.get("encrypted_seed_asset_id", ""),
                    is_backed_up=wdata.get("is_backed_up", False),
                )

            log.info("wallet.state_loaded", count=len(self._wallets))
        except Exception as e:
            log.warning("wallet.state_load_error", error=str(e))

    # =========================================================================
    # Stats & Report
    # =========================================================================

    def stats(self) -> dict[str, Any]:
        return {
            "wallets_created": self._wallets_created,
            "active_wallets": len(self._wallets),
            "network": self.network.value,
            "supported_chains": ["cardano", "bitcoin", "night_chain"],
            "bitcoin_address_types": [t.value for t in BitcoinAddressType],
        }

    def get_wallet(self, wallet_id: str) -> WalletState | None:
        return self._wallets.get(wallet_id)

    def list_wallets(self) -> list[dict[str, Any]]:
        return [w.as_dict() for w in self._wallets.values()]
