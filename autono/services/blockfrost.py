"""Blockfrost client — Cardano chain data for all agents.

Async HTTP client for the Blockfrost API. Provides:
- Protocol parameters (epoch, fees, costs)
- Address queries (UTXOs, balances, transactions)
- Asset/token lookups (policy, metadata, minting history)
- Transaction submission and status
- Block and epoch queries
- Pool and stake information

Security:
    API key loaded from environment ONLY — never hardcoded, never logged.
    All requests go through a single rate-limited client instance.

Usage:
    client = BlockfrostClient()              # reads BLOCKFROST_API_KEY from env
    params = await client.protocol_params()
    utxos = await client.address_utxos("addr1...")
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

log = structlog.get_logger()

# Blockfrost API base URLs
_BASE_URLS = {
    "mainnet": "https://cardano-mainnet.blockfrost.io/api/v0",
    "testnet": "https://cardano-testnet.blockfrost.io/api/v0",
    "preview": "https://cardano-preview.blockfrost.io/api/v0",
    "preprod": "https://cardano-preprod.blockfrost.io/api/v0",
}


@dataclass
class RateLimitState:
    """Tracks Blockfrost rate limiting."""
    requests_made: int = 0
    requests_remaining: int = 500  # Blockfrost burst limit
    window_reset: float = 0.0
    total_calls: int = 0
    errors: int = 0
    last_call: float = 0.0


class BlockfrostError(Exception):
    """Blockfrost API error with status code and message."""

    def __init__(self, status: int, message: str, endpoint: str = "") -> None:
        self.status = status
        self.endpoint = endpoint
        super().__init__(f"Blockfrost {status} on {endpoint}: {message}")


class BlockfrostClient:
    """Async Blockfrost API client for Cardano chain data.

    Reads API key from BLOCKFROST_API_KEY environment variable.
    Never logs, prints, or exposes the key.
    """

    def __init__(self, network: str | None = None) -> None:
        # Load from environment ONLY
        self._api_key = os.environ.get("BLOCKFROST_API_KEY", "")
        if not self._api_key:
            log.warning("blockfrost.no_api_key",
                        hint="Set BLOCKFROST_API_KEY in .env")

        # Detect network from key prefix or env
        if network:
            self._network = network
        elif self._api_key.startswith("mainnet"):
            self._network = "mainnet"
        elif self._api_key.startswith("testnet"):
            self._network = "testnet"
        elif self._api_key.startswith("preview"):
            self._network = "preview"
        elif self._api_key.startswith("preprod"):
            self._network = "preprod"
        else:
            self._network = os.environ.get("BLOCKFROST_NETWORK", "mainnet")

        self._base_url = _BASE_URLS.get(self._network, _BASE_URLS["mainnet"])
        self._rate = RateLimitState()
        self._client: httpx.AsyncClient | None = None

        log.info("blockfrost.initialized",
                 network=self._network,
                 has_key=bool(self._api_key))

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    @property
    def network(self) -> str:
        return self._network

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazy-init the async HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "project_id": self._api_key,
                    "User-Agent": "autono/1.0",
                },
                timeout=30.0,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Core HTTP
    # =========================================================================

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        json_body: Any = None,
    ) -> Any:
        """Make a rate-limited request to Blockfrost."""
        if not self._api_key:
            raise BlockfrostError(401, "No API key configured", endpoint)

        # Simple rate limiting: don't exceed 10 req/s
        now = time.monotonic()
        elapsed = now - self._rate.last_call
        if elapsed < 0.1:  # 10 req/s max
            import asyncio
            await asyncio.sleep(0.1 - elapsed)

        client = await self._get_client()
        self._rate.last_call = time.monotonic()
        self._rate.total_calls += 1

        try:
            if method == "GET":
                resp = await client.get(endpoint, params=params)
            elif method == "POST":
                resp = await client.post(
                    endpoint,
                    content=json_body if isinstance(json_body, bytes) else None,
                    json=json_body if not isinstance(json_body, bytes) else None,
                )
            else:
                raise ValueError(f"Unsupported method: {method}")

            # Update rate limit tracking from headers
            remaining = resp.headers.get("x-ratelimit-remaining")
            if remaining is not None:
                self._rate.requests_remaining = int(remaining)

            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                return None  # Not found is valid (empty address, etc.)
            elif resp.status_code == 402:
                self._rate.errors += 1
                raise BlockfrostError(402, "Usage limit reached", endpoint)
            elif resp.status_code == 429:
                self._rate.errors += 1
                raise BlockfrostError(429, "Rate limited", endpoint)
            elif resp.status_code == 418:
                self._rate.errors += 1
                raise BlockfrostError(418, "IP banned — back off", endpoint)
            else:
                self._rate.errors += 1
                body = resp.text[:200]
                raise BlockfrostError(resp.status_code, body, endpoint)

        except httpx.HTTPError as e:
            self._rate.errors += 1
            raise BlockfrostError(0, str(e), endpoint) from e

    async def _get(self, endpoint: str, **params: Any) -> Any:
        """GET request shorthand."""
        clean = {k: v for k, v in params.items() if v is not None}
        return await self._request("GET", endpoint, params=clean or None)

    async def _get_all_pages(
        self, endpoint: str, max_pages: int = 10, **params: Any
    ) -> list[Any]:
        """Paginate through all results (Blockfrost uses page/count)."""
        all_results: list[Any] = []
        for page in range(1, max_pages + 1):
            result = await self._get(endpoint, page=page, count=100, **params)
            if not result:
                break
            if isinstance(result, list):
                all_results.extend(result)
                if len(result) < 100:
                    break
            else:
                all_results.append(result)
                break
        return all_results

    # =========================================================================
    # Health & Network
    # =========================================================================

    async def health(self) -> dict[str, Any]:
        """Check Blockfrost API health."""
        result = await self._get("/health")
        return result or {"is_healthy": False}

    async def health_clock(self) -> dict[str, Any]:
        """Get server time."""
        return await self._get("/health/clock") or {}

    # =========================================================================
    # Protocol Parameters
    # =========================================================================

    async def latest_epoch(self) -> dict[str, Any]:
        """Get the latest epoch information."""
        return await self._get("/epochs/latest") or {}

    async def protocol_params(self) -> dict[str, Any]:
        """Get current protocol parameters.

        Returns min fees, max tx size, cost models, collateral %, etc.
        Essential for transaction building.
        """
        return await self._get("/epochs/latest/parameters") or {}

    async def epoch_info(self, epoch: int) -> dict[str, Any]:
        """Get info for a specific epoch."""
        return await self._get(f"/epochs/{epoch}") or {}

    # =========================================================================
    # Blocks
    # =========================================================================

    async def latest_block(self) -> dict[str, Any]:
        """Get the latest block."""
        return await self._get("/blocks/latest") or {}

    async def block(self, hash_or_number: str | int) -> dict[str, Any]:
        """Get a specific block by hash or number."""
        return await self._get(f"/blocks/{hash_or_number}") or {}

    async def block_txs(self, hash_or_number: str | int) -> list[str]:
        """Get transaction hashes in a block."""
        result = await self._get(f"/blocks/{hash_or_number}/txs")
        return result or []

    # =========================================================================
    # Addresses
    # =========================================================================

    async def address_info(self, address: str) -> dict[str, Any] | None:
        """Get address summary (balance, stake, type)."""
        return await self._get(f"/addresses/{address}")

    async def address_details(self, address: str) -> dict[str, Any] | None:
        """Get detailed address info including script hash."""
        return await self._get(f"/addresses/{address}/total")

    async def address_utxos(
        self, address: str, asset: str | None = None
    ) -> list[dict[str, Any]]:
        """Get UTXOs at an address.

        This is THE critical method for transaction building.
        Optionally filter by asset (policy_id + hex_name).
        """
        if asset:
            endpoint = f"/addresses/{address}/utxos/{asset}"
        else:
            endpoint = f"/addresses/{address}/utxos"
        return await self._get_all_pages(endpoint)

    async def address_txs(
        self, address: str, from_block: str | None = None,
        to_block: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get transactions for an address."""
        return await self._get_all_pages(
            f"/addresses/{address}/transactions",
            **{"from": from_block, "to": to_block},
        )

    # =========================================================================
    # Transactions
    # =========================================================================

    async def tx(self, tx_hash: str) -> dict[str, Any] | None:
        """Get transaction details."""
        return await self._get(f"/txs/{tx_hash}")

    async def tx_utxos(self, tx_hash: str) -> dict[str, Any] | None:
        """Get transaction UTXOs (inputs and outputs)."""
        return await self._get(f"/txs/{tx_hash}/utxos")

    async def tx_metadata(self, tx_hash: str) -> list[dict[str, Any]]:
        """Get transaction metadata (CIP-25 NFTs, etc.)."""
        result = await self._get(f"/txs/{tx_hash}/metadata")
        return result or []

    async def tx_submit(self, tx_cbor: bytes) -> str:
        """Submit a signed transaction (CBOR bytes).

        Returns the transaction hash on success.
        """
        result = await self._request(
            "POST", "/tx/submit", json_body=tx_cbor
        )
        return result  # tx hash string

    # =========================================================================
    # Assets / Tokens
    # =========================================================================

    async def asset(self, asset_id: str) -> dict[str, Any] | None:
        """Get asset info by policy_id + hex_name."""
        return await self._get(f"/assets/{asset_id}")

    async def asset_history(self, asset_id: str) -> list[dict[str, Any]]:
        """Get minting/burning history for an asset."""
        return await self._get_all_pages(f"/assets/{asset_id}/history")

    async def asset_addresses(self, asset_id: str) -> list[dict[str, Any]]:
        """Get all addresses holding an asset."""
        return await self._get_all_pages(f"/assets/{asset_id}/addresses")

    async def policy_assets(self, policy_id: str) -> list[dict[str, Any]]:
        """Get all assets under a policy ID."""
        return await self._get_all_pages(f"/assets/policy/{policy_id}")

    # =========================================================================
    # Scripts (Plutus / Native)
    # =========================================================================

    async def script(self, script_hash: str) -> dict[str, Any] | None:
        """Get script information."""
        return await self._get(f"/scripts/{script_hash}")

    async def script_cbor(self, script_hash: str) -> dict[str, Any] | None:
        """Get script CBOR."""
        return await self._get(f"/scripts/{script_hash}/cbor")

    async def script_datum(self, datum_hash: str) -> dict[str, Any] | None:
        """Get datum by hash."""
        return await self._get(f"/scripts/datum/{datum_hash}")

    async def script_redeemers(
        self, script_hash: str
    ) -> list[dict[str, Any]]:
        """Get redeemers for a script."""
        return await self._get_all_pages(
            f"/scripts/{script_hash}/redeemers"
        )

    # =========================================================================
    # Stake / Pools
    # =========================================================================

    async def account(self, stake_address: str) -> dict[str, Any] | None:
        """Get stake account info (rewards, pool, etc.)."""
        return await self._get(f"/accounts/{stake_address}")

    async def account_rewards(
        self, stake_address: str
    ) -> list[dict[str, Any]]:
        """Get reward history for a stake address."""
        return await self._get_all_pages(
            f"/accounts/{stake_address}/rewards"
        )

    async def pool(self, pool_id: str) -> dict[str, Any] | None:
        """Get stake pool info."""
        return await self._get(f"/pools/{pool_id}")

    # =========================================================================
    # Metadata
    # =========================================================================

    async def metadata_label(self, label: int) -> list[dict[str, Any]]:
        """Get all transactions with a specific metadata label.

        Useful for CIP-25 (label 721), CIP-68, etc.
        """
        return await self._get_all_pages(f"/metadata/txs/labels/{label}")

    # =========================================================================
    # IPFS (Blockfrost provides IPFS gateway)
    # =========================================================================

    async def ipfs_pin(self, ipfs_hash: str) -> dict[str, Any] | None:
        """Get IPFS pin status."""
        return await self._get(f"/ipfs/pin/list/{ipfs_hash}")

    # =========================================================================
    # Convenience / High-Level
    # =========================================================================

    async def get_ada_balance(self, address: str) -> int:
        """Get ADA balance in lovelace for an address."""
        info = await self.address_info(address)
        if not info:
            return 0
        amounts = info.get("amount", [])
        for a in amounts:
            if a.get("unit") == "lovelace":
                return int(a["quantity"])
        return 0

    async def get_native_tokens(
        self, address: str
    ) -> list[dict[str, Any]]:
        """Get all native tokens at an address (excludes ADA)."""
        info = await self.address_info(address)
        if not info:
            return []
        return [
            a for a in info.get("amount", [])
            if a.get("unit") != "lovelace"
        ]

    async def tip(self) -> dict[str, Any]:
        """Get chain tip: latest block + slot + epoch."""
        block = await self.latest_block()
        if not block:
            return {}
        return {
            "block": block.get("height"),
            "slot": block.get("slot"),
            "epoch": block.get("epoch"),
            "hash": block.get("hash"),
            "time": block.get("time"),
        }

    async def is_address_used(self, address: str) -> bool:
        """Check if an address has ever received a transaction."""
        info = await self.address_info(address)
        return info is not None

    async def wait_for_tx(
        self, tx_hash: str, timeout: float = 120.0, poll: float = 5.0
    ) -> dict[str, Any] | None:
        """Wait for a transaction to land on-chain."""
        import asyncio

        start = time.monotonic()
        while time.monotonic() - start < timeout:
            result = await self.tx(tx_hash)
            if result:
                return result
            await asyncio.sleep(poll)
        return None

    # =========================================================================
    # Stats
    # =========================================================================

    def stats(self) -> dict[str, Any]:
        """Get client statistics (no secrets exposed)."""
        return {
            "network": self._network,
            "configured": self.is_configured,
            "total_calls": self._rate.total_calls,
            "errors": self._rate.errors,
            "requests_remaining": self._rate.requests_remaining,
        }
