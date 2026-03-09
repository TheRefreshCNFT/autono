"""SpellCaster — Cross-chain spell coordination agent.

The spell is the universal cross-chain instruction format. Instead of
chain-specific bridge logic, every cross-chain operation is a spell:

  Lock ADA, mint charm on BTC    -> spell
  Burn charm on BTC, unlock ADA  -> spell
  Private transfer via Night     -> spell with ZK proof

Spell lifecycle:
  1. DRAFT    — spell structure defined, inputs/outputs specified
  2. PROVEN   — ZK proof generated (Groth16)
  3. SIGNED   — all required chain-side signatures collected
  4. CAST     — spell transaction submitted to Bitcoin
  5. LANDED   — cross-chain materialization confirmed on target chain
  6. FAILED   — spell rejected or timed out

On-chain format:
  OP_RETURN OP_PUSH 'spell' OP_PUSH CBOR(NormalizedSpell, Groth16Proof)
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any

import structlog

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message

log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Spell data structures
# ---------------------------------------------------------------------------

class SpellStatus(str, Enum):
    DRAFT = "draft"
    PROVEN = "proven"
    SIGNED = "signed"
    CAST = "cast"
    LANDED = "landed"
    FAILED = "failed"


class SpellType(str, Enum):
    MINT_TOKEN = "mint_token"
    MINT_NFT = "mint_nft"
    TRANSFER = "transfer"
    BURN = "burn"
    BRIDGE_LOCK = "bridge_lock"
    BRIDGE_MINT = "bridge_mint"
    BRIDGE_REDEEM = "bridge_redeem"
    CROSS_CHAIN = "cross_chain"


@dataclass
class CharmOutput:
    """A single charm in a spell output."""
    app_tag: str            # 'n' for NFT, 't' for token
    app_identity: str       # 32-byte hex app identifier
    data: dict[str, Any] = field(default_factory=dict)
    amount: int = 0         # For fungible tokens


@dataclass
class SpellInput:
    """A UTXO being consumed by the spell."""
    txid: str
    vout: int
    chain: str = "bitcoin"
    charms: list[CharmOutput] = field(default_factory=list)


@dataclass
class SpellOutput:
    """A UTXO being created by the spell."""
    address: str = ""
    satoshis: int = 0
    chain: str = "bitcoin"
    charms: list[CharmOutput] = field(default_factory=list)


@dataclass
class NormalizedSpell:
    """The spell structure that gets CBOR-encoded and attached to a tx.

    Matches the Charms protocol NormalizedSpell format:
    - app_public_inputs: maps apps to (tag, identity, VK) tuples
    - tx.ins: consumed UTXOs with their charms
    - tx.outs: output charm assignments
    - tx.coins: satoshi outputs
    """
    id: str = field(default_factory=lambda: f"spell_{uuid.uuid4().hex[:12]}")
    spell_type: SpellType = SpellType.TRANSFER
    status: SpellStatus = SpellStatus.DRAFT

    app_public_inputs: list[dict[str, Any]] = field(default_factory=list)
    inputs: list[SpellInput] = field(default_factory=list)
    outputs: list[SpellOutput] = field(default_factory=list)

    source_chain: str = "bitcoin"
    target_chain: str = ""

    proof_type: str = "groth16"
    proof_data: bytes = b""
    verification_key: str = ""

    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    cast_at: str = ""
    landed_at: str = ""
    cast_txid: str = ""
    error: str = ""

    def content_hash(self) -> str:
        parts = [self.spell_type.value, self.source_chain, self.target_chain]
        for inp in self.inputs:
            parts.append(f"{inp.txid}:{inp.vout}")
        for out in self.outputs:
            parts.append(f"{out.address}:{out.satoshis}")
        return hashlib.sha256("|".join(parts).encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "spell_type": self.spell_type.value,
            "status": self.status.value,
            "app_public_inputs": self.app_public_inputs,
            "inputs": [
                {"txid": i.txid, "vout": i.vout, "chain": i.chain,
                 "charms": [{"tag": c.app_tag, "identity": c.app_identity,
                             "data": c.data, "amount": c.amount}
                            for c in i.charms]}
                for i in self.inputs
            ],
            "outputs": [
                {"address": o.address, "satoshis": o.satoshis, "chain": o.chain,
                 "charms": [{"tag": c.app_tag, "identity": c.app_identity,
                             "data": c.data, "amount": c.amount}
                            for c in o.charms]}
                for o in self.outputs
            ],
            "source_chain": self.source_chain,
            "target_chain": self.target_chain,
            "proof_type": self.proof_type,
            "verification_key": self.verification_key,
            "created_at": self.created_at,
            "cast_at": self.cast_at,
            "landed_at": self.landed_at,
            "cast_txid": self.cast_txid,
            "content_hash": self.content_hash(),
            "error": self.error,
        }

    def to_cbor_payload(self) -> dict[str, Any]:
        """Build CBOR-encodable payload for OP_RETURN embedding."""
        return {
            "app_public_inputs": self.app_public_inputs,
            "tx": {
                "ins": [
                    {
                        "txid": inp.txid, "vout": inp.vout,
                        "charms": {
                            c.app_identity: {"tag": c.app_tag, **c.data}
                            for c in inp.charms
                        } if inp.charms else {},
                    }
                    for inp in self.inputs
                ],
                "outs": [
                    {
                        "charms": {
                            c.app_identity: {
                                "tag": c.app_tag, "amount": c.amount, **c.data,
                            }
                            for c in out.charms
                        } if out.charms else {},
                    }
                    for out in self.outputs
                ],
                "coins": [o.satoshis for o in self.outputs if o.satoshis > 0],
            },
        }


# ---------------------------------------------------------------------------
# Spell templates for common operations
# ---------------------------------------------------------------------------

SPELL_TEMPLATES: dict[str, dict[str, Any]] = {
    "mint_token": {
        "spell_type": "mint_token",
        "source_chain": "bitcoin",
        "outputs": [{"chain": "bitcoin",
                      "charms": [{"tag": "t", "identity": "", "amount": 0}]}],
    },
    "mint_nft": {
        "spell_type": "mint_nft",
        "source_chain": "bitcoin",
        "outputs": [{"chain": "bitcoin",
                      "charms": [{"tag": "n", "identity": "", "data": {}}]}],
    },
    "btc_to_ada": {
        "spell_type": "cross_chain",
        "source_chain": "bitcoin",
        "target_chain": "cardano",
        "outputs": [
            {"chain": "bitcoin", "satoshis": 0},
            {"chain": "cardano"},
        ],
    },
    "ada_to_btc": {
        "spell_type": "cross_chain",
        "source_chain": "cardano",
        "target_chain": "bitcoin",
        "outputs": [{"chain": "bitcoin"}],
    },
    "grail_lock": {
        "spell_type": "bridge_lock",
        "source_chain": "bitcoin",
        "target_chain": "bitcoinos",
        "outputs": [{"chain": "bitcoin", "satoshis": 0}],
    },
    "night_transfer": {
        "spell_type": "cross_chain",
        "source_chain": "bitcoin",
        "target_chain": "night_chain",
        "outputs": [{"chain": "night_chain"}],
    },
    "transfer": {
        "spell_type": "transfer",
        "source_chain": "bitcoin",
    },
    "burn": {
        "spell_type": "burn",
        "source_chain": "bitcoin",
    },
}

# Map domains to their specialist agent names
_CHAIN_AGENT_MAP: dict[str, str] = {
    "cardano": "CardanoChainAgent",
    "bitcoin": "BitcoinChainAgent",
    "night_chain": "NightChainAgent",
    "bitcoinos": "BitcoinChainAgent",
}


# ---------------------------------------------------------------------------
# SpellCaster Agent
# ---------------------------------------------------------------------------

class SpellCasterAgent(AutonomousAgent):
    """Cross-chain spell coordination agent.

    Constructs NormalizedSpell objects, coordinates with chain agents
    for execution, and tracks spell lifecycle.

    Does NOT submit transactions directly. Delegates to:
    - BitcoinChainAgent for OP_RETURN embedding and BTC tx submission
    - CardanoChainAgent for CIP-25 minting on Cardano side
    - NightChainAgent for encrypted/private state operations
    - CharmsAgent for ZK proof verification and bridge routing
    """

    def __init__(self) -> None:
        super().__init__(
            name="SpellCasterAgent",
            role="Cross-chain spell coordination — construct, prove, cast, track",
            capabilities=[
                AgentCapability.BRIDGE_ASSETS,
                AgentCapability.CREATE_TOKEN,
                AgentCapability.MINT_NFT,
                AgentCapability.TRADE,
            ],
        )
        self._graph = None
        self._store = None
        self._active_spells: dict[str, NormalizedSpell] = {}
        self._spell_history: list[dict[str, Any]] = []

    @property
    def work_interval(self) -> float:
        return 10.0

    def set_dependencies(self, store: Any, graph: Any) -> None:
        self._store = store
        self._graph = graph

    async def do_work(self) -> None:
        """Advance active spells through their lifecycle."""
        for spell_id, spell in list(self._active_spells.items()):
            if spell.status == SpellStatus.CAST:
                await self._check_confirmation(spell)
            elif spell.status in (SpellStatus.LANDED, SpellStatus.FAILED):
                self._spell_history.append(spell.to_dict())
                if len(self._spell_history) > 100:
                    self._spell_history = self._spell_history[-100:]
                del self._active_spells[spell_id]

    async def handle_message(self, msg: Message) -> None:
        if msg.kind != "request":
            return

        req_type = msg.payload.get("type", "")
        handler = {
            "create_spell": self._on_create_spell,
            "cast_spell": self._on_cast_spell,
            "proof_ready": self._on_proof_ready,
            "spell_landed": self._on_spell_landed,
            "get_spell_status": self._on_get_status,
            "list_templates": self._on_list_templates,
            "spell_from_template": self._on_template_spell,
        }.get(req_type)

        if handler:
            result = await handler(msg.payload)
            await self.send(msg.sender, "response", {
                "type": f"{req_type}_result", **result,
            })

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "cross_chain_spells",
            "topics": [
                "charms_spell_format_updates",
                "groth16_proof_optimization",
                "cross_chain_atomic_operations",
            ],
        })

    # -- Spell creation -------------------------------------------------------

    async def _on_create_spell(self, payload: dict) -> dict[str, Any]:
        """Create a new spell from explicit parameters."""
        spell_type_str = payload.get("spell_type", "transfer")
        try:
            spell_type = SpellType(spell_type_str)
        except ValueError:
            return {"ok": False, "error": f"Unknown spell type: {spell_type_str}"}

        spell = NormalizedSpell(spell_type=spell_type)
        spell.source_chain = payload.get("source_chain", "bitcoin")
        spell.target_chain = payload.get("target_chain", "")

        # Parse inputs
        for inp_data in payload.get("inputs", []):
            si = SpellInput(
                txid=inp_data.get("txid", ""),
                vout=inp_data.get("vout", 0),
                chain=inp_data.get("chain", "bitcoin"),
            )
            for cd in inp_data.get("charms", []):
                si.charms.append(CharmOutput(
                    app_tag=cd.get("tag", "t"),
                    app_identity=cd.get("identity", "0" * 64),
                    data=cd.get("data", {}),
                    amount=cd.get("amount", 0),
                ))
            spell.inputs.append(si)

        # Parse outputs
        for out_data in payload.get("outputs", []):
            so = SpellOutput(
                address=out_data.get("address", ""),
                satoshis=out_data.get("satoshis", 0),
                chain=out_data.get("chain", spell.source_chain),
            )
            for cd in out_data.get("charms", []):
                so.charms.append(CharmOutput(
                    app_tag=cd.get("tag", "t"),
                    app_identity=cd.get("identity", "0" * 64),
                    data=cd.get("data", {}),
                    amount=cd.get("amount", 0),
                ))
            spell.outputs.append(so)

        # Collect app public inputs from all charms
        seen: dict[str, dict[str, Any]] = {}
        for container in (*spell.inputs, *spell.outputs):
            for charm in container.charms:
                if charm.app_identity not in seen:
                    seen[charm.app_identity] = {
                        "tag": charm.app_tag,
                        "identity": charm.app_identity,
                        "vk": payload.get("verification_key", ""),
                    }
        spell.app_public_inputs = list(seen.values())

        self._active_spells[spell.id] = spell

        self.memory.remember("decisions", {
            "type": "spell_created",
            "spell_id": spell.id,
            "spell_type": spell_type.value,
            "source": spell.source_chain,
            "target": spell.target_chain,
        })

        self.log.info("spell.created",
                      spell_id=spell.id, type=spell_type.value,
                      source=spell.source_chain, target=spell.target_chain)

        # Cross-chain: notify CharmsAgent for bridge coordination
        if spell.target_chain and spell.target_chain != spell.source_chain:
            await self.send("CharmsAgent", "request", {
                "type": "bridge_transfer",
                "from_chain": spell.source_chain,
                "to_chain": spell.target_chain,
                "spell_id": spell.id,
                "spell": spell.to_dict(),
            })

        # Request proof generation
        await self.send("CharmsAgent", "request", {
            "type": "verify_spell",
            "spell_id": spell.id,
            "spell": spell.to_cbor_payload(),
        })

        return {"ok": True, "spell_id": spell.id, "status": spell.status.value,
                "spell": spell.to_dict()}

    async def _on_cast_spell(self, payload: dict) -> dict[str, Any]:
        """Submit a proven spell to the network."""
        spell_id = payload.get("spell_id", "")
        spell = self._active_spells.get(spell_id)
        if not spell:
            return {"ok": False, "error": "spell_not_found"}
        if spell.status not in (SpellStatus.PROVEN, SpellStatus.SIGNED):
            return {"ok": False, "error": f"not ready: {spell.status.value}"}

        spell.status = SpellStatus.CAST
        spell.cast_at = datetime.now(timezone.utc).isoformat()

        # Delegate to BitcoinChainAgent for OP_RETURN tx
        await self.send("BitcoinChainAgent", "request", {
            "type": "build_psbt",
            "spell_id": spell.id,
            "op_return_data": {
                "prefix": "spell",
                "payload": spell.to_cbor_payload(),
            },
            "outputs": [
                {"address": o.address, "satoshis": o.satoshis}
                for o in spell.outputs
                if o.chain == "bitcoin" and o.satoshis > 0
            ],
        })

        self.log.info("spell.cast", spell_id=spell.id)
        return {"ok": True, "spell_id": spell.id, "status": "cast"}

    async def _on_proof_ready(self, payload: dict) -> dict[str, Any]:
        """Accept ZK proof for a spell."""
        spell_id = payload.get("spell_id", "")
        spell = self._active_spells.get(spell_id)
        if not spell:
            return {"ok": False, "error": "spell_not_found"}

        spell.status = SpellStatus.PROVEN
        spell.verification_key = payload.get("verification_key", "")
        self.log.info("spell.proven", spell_id=spell.id)
        return {"ok": True, "spell_id": spell.id, "status": "proven"}

    async def _on_spell_landed(self, payload: dict) -> dict[str, Any]:
        """Confirm cross-chain materialization."""
        spell_id = payload.get("spell_id", "")
        spell = self._active_spells.get(spell_id)
        if not spell:
            return {"ok": False, "error": "spell_not_found"}

        spell.status = SpellStatus.LANDED
        spell.landed_at = datetime.now(timezone.utc).isoformat()
        spell.cast_txid = payload.get("txid", "")

        self.log.info("spell.landed", spell_id=spell.id, txid=spell.cast_txid)

        # Notify target chain agent
        target_agent = _CHAIN_AGENT_MAP.get(spell.target_chain, "")
        if target_agent:
            await self.send(target_agent, "request", {
                "type": "spell_materialized",
                "spell_id": spell.id,
                "spell": spell.to_dict(),
                "txid": spell.cast_txid,
            })

        return {"ok": True, "spell_id": spell.id, "status": "landed"}

    async def _on_get_status(self, payload: dict) -> dict[str, Any]:
        spell_id = payload.get("spell_id", "")
        spell = self._active_spells.get(spell_id)
        if spell:
            return {"ok": True, **spell.to_dict()}
        return {"ok": False, "error": "spell_not_found"}

    async def _on_list_templates(self, _payload: dict) -> dict[str, Any]:
        return {"ok": True, "templates": list(SPELL_TEMPLATES.keys())}

    async def _on_template_spell(self, payload: dict) -> dict[str, Any]:
        """Create spell from a predefined template."""
        template_name = payload.get("template", "")
        template = SPELL_TEMPLATES.get(template_name)
        if not template:
            return {"ok": False, "error": f"Unknown template: {template_name}",
                    "available": list(SPELL_TEMPLATES.keys())}
        merged = {**template, **payload}
        merged.pop("template", None)
        return await self._on_create_spell(merged)

    async def _check_confirmation(self, spell: NormalizedSpell) -> None:
        """Check if a cast spell has confirmed on-chain."""
        if not spell.cast_at:
            return
        cast_time = datetime.fromisoformat(spell.cast_at)
        elapsed = (datetime.now(timezone.utc) - cast_time).total_seconds()

        if elapsed > 60 and not spell.cast_txid:
            await self.send("BitcoinChainAgent", "request", {
                "type": "bitcoin_query",
                "query": f"spell_tx_status:{spell.id}",
                "spell_id": spell.id,
            })

        if elapsed > 3600:
            spell.status = SpellStatus.FAILED
            spell.error = "timeout: no confirmation after 1 hour"
            self.log.warning("spell.timeout", spell_id=spell.id)

    def report(self) -> dict[str, Any]:
        base = super().report()
        active = {
            sid: {"type": s.spell_type.value, "status": s.status.value,
                  "source": s.source_chain, "target": s.target_chain}
            for sid, s in self._active_spells.items()
        }
        base.update({
            "active_spells": active,
            "active_count": len(self._active_spells),
            "history_count": len(self._spell_history),
            "templates": list(SPELL_TEMPLATES.keys()),
        })
        return base
