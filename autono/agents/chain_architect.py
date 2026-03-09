"""Agent 1: ChainArchitect -- Core sidechain protocol designer and maintainer.

Responsibilities:
- Monitor real Cardano chain health via Blockfrost
- Track block production, block times, throughput, empty blocks
- Analyze protocol parameter changes across epochs
- Enforce cost targets -- alert if fees exceed thresholds
- Detect hard fork combinator events and protocol upgrades
- Report chain state and cost metrics to TreasuryVault and all agents
"""

from __future__ import annotations

import time
from collections import deque
from datetime import datetime, timezone
from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message
from autono.core.autonomy import COST_TARGETS
from autono.services.blockfrost import BlockfrostClient


# Expected block time on Cardano mainnet in seconds
EXPECTED_BLOCK_TIME_S = 20.0
# Deviation threshold before alerting (50%)
BLOCK_TIME_DEVIATION_THRESHOLD = 0.5
# Number of recent blocks to keep for rolling analysis
ROLLING_BLOCK_WINDOW = 50
# Number of txs to sample per block for fee analysis
TX_SAMPLE_PER_BLOCK = 5
# Number of blocks to sample for fee calculation
FEE_SAMPLE_BLOCKS = 10


class ChainArchitect(AutonomousAgent):
    def __init__(self) -> None:
        super().__init__(
            name="ChainArchitect",
            role="Core sidechain protocol architect -- consensus, blocks, finality",
            capabilities=[
                AgentCapability.DEPLOY_CONTRACT,
                AgentCapability.RUN_VALIDATOR,
                AgentCapability.RESEARCH,
                AgentCapability.BUILD_PRODUCT,
            ],
        )
        self.target_tps = 1000
        self.target_finality_ms = 800
        self.consensus_type = "ouroboros-turbo"
        self.block_time_ms = 500
        self.epoch_length = 21600

        # Blockfrost client -- initialized lazily
        self._bf: BlockfrostClient | None = None
        self._bf_available: bool | None = None  # None = not checked yet

        # Rolling block data: list of dicts with height, time, tx_count, hash
        self._recent_blocks: deque[dict[str, Any]] = deque(maxlen=ROLLING_BLOCK_WINDOW)

        # Health score computed each cycle
        self._health_score: float = 0.0
        self._avg_block_time: float = 0.0
        self._avg_tx_count: float = 0.0
        self._empty_block_ratio: float = 0.0

        # Protocol parameter tracking across epochs
        self._prev_epoch_params: dict[str, Any] = {}
        self._prev_epoch_number: int | None = None
        self._param_change_history: list[dict[str, Any]] = []

        # Fee tracking
        self._avg_tx_fee_lovelace: float = 0.0
        self._fee_history: deque[dict[str, Any]] = deque(maxlen=100)

        # Current chain tip info
        self._current_epoch: int | None = None
        self._current_slot: int | None = None
        self._current_block_height: int | None = None

        # Protocol version tracking for hard fork detection
        self._protocol_major: int | None = None
        self._protocol_minor: int | None = None

    @property
    def work_interval(self) -> float:
        return 10.0  # critical path -- runs frequently

    # -- Blockfrost initialization -------------------------------------------

    def _get_blockfrost(self) -> BlockfrostClient | None:
        """Lazy-init Blockfrost client. Returns None if not configured."""
        if self._bf_available is False:
            return None
        if self._bf is None:
            self._bf = BlockfrostClient()
            if not self._bf.is_configured:
                self.log.warning("chain.blockfrost_not_configured",
                                 hint="Set BLOCKFROST_API_KEY to enable real chain monitoring")
                self._bf_available = False
                return None
            self._bf_available = True
        return self._bf

    # -- main work loop ------------------------------------------------------

    async def do_work(self) -> None:
        """Continuously monitor and optimize the chain."""
        bf = self._get_blockfrost()
        if bf is None:
            self.log.debug("chain.no_blockfrost", status="skipping_real_monitoring")
            return

        await self._check_block_production(bf)
        await self._tune_consensus(bf)
        await self._track_cost_efficiency(bf)
        await self._evaluate_upgrades(bf)

    # -- block production health ---------------------------------------------

    async def _check_block_production(self, bf: BlockfrostClient) -> None:
        """Fetch recent blocks, compute rolling stats, derive health score."""
        try:
            latest = await bf.latest_block()
        except Exception as exc:
            self.log.error("chain.block_fetch_failed", error=str(exc))
            return

        if not latest:
            self.log.warning("chain.no_latest_block")
            return

        height = latest.get("height", 0)
        block_time = latest.get("time", 0)
        block_hash = latest.get("hash", "")
        block_epoch = latest.get("epoch", 0)
        block_slot = latest.get("slot", 0)
        tx_count = latest.get("tx_count", 0)

        self._current_epoch = block_epoch
        self._current_slot = block_slot
        self._current_block_height = height

        # Avoid re-processing the same block
        if self._recent_blocks and self._recent_blocks[-1].get("height") == height:
            return

        # Fetch a few previous blocks if our deque is sparse
        if len(self._recent_blocks) < 5:
            await self._backfill_blocks(bf, height)

        # Add current block
        self._recent_blocks.append({
            "height": height,
            "time": block_time,
            "tx_count": tx_count,
            "hash": block_hash,
            "epoch": block_epoch,
            "slot": block_slot,
        })

        # Compute rolling stats
        self._compute_block_stats()

        # Check for anomalies
        alerts = []
        if self._avg_block_time > 0:
            deviation = abs(self._avg_block_time - EXPECTED_BLOCK_TIME_S) / EXPECTED_BLOCK_TIME_S
            if deviation > BLOCK_TIME_DEVIATION_THRESHOLD:
                alert_msg = (
                    f"Block time deviation {deviation:.0%}: "
                    f"avg={self._avg_block_time:.1f}s vs expected={EXPECTED_BLOCK_TIME_S}s"
                )
                alerts.append(alert_msg)
                self.log.warning("chain.block_time_anomaly",
                                 avg_block_time=self._avg_block_time,
                                 expected=EXPECTED_BLOCK_TIME_S,
                                 deviation_pct=round(deviation * 100, 1))

        if self._empty_block_ratio > 0.3:
            alert_msg = f"High empty block ratio: {self._empty_block_ratio:.0%}"
            alerts.append(alert_msg)
            self.log.warning("chain.empty_blocks_high",
                             empty_ratio=round(self._empty_block_ratio, 3))

        self.memory.remember("decisions", {
            "type": "block_health_check",
            "health_score": round(self._health_score, 1),
            "avg_block_time_s": round(self._avg_block_time, 2),
            "avg_tx_count": round(self._avg_tx_count, 2),
            "empty_block_ratio": round(self._empty_block_ratio, 3),
            "block_height": height,
            "epoch": block_epoch,
            "slot": block_slot,
            "alerts": alerts,
            "status": "degraded" if alerts else "healthy",
        })

        if alerts:
            await self.broadcast("alert", {
                "type": "chain_health_warning",
                "source": "ChainArchitect",
                "health_score": round(self._health_score, 1),
                "alerts": alerts,
                "block_height": height,
                "epoch": block_epoch,
            }, priority=2)

        self.log.info("chain.health",
                      score=round(self._health_score, 1),
                      avg_block_time=round(self._avg_block_time, 2),
                      avg_tx=round(self._avg_tx_count, 1),
                      empty_ratio=round(self._empty_block_ratio, 3),
                      height=height)

    async def _backfill_blocks(self, bf: BlockfrostClient, current_height: int) -> None:
        """Fetch a handful of previous blocks to seed rolling stats."""
        count = min(ROLLING_BLOCK_WINDOW, 10)  # don't hammer API on startup
        for offset in range(count, 0, -1):
            target_height = current_height - offset
            if target_height < 1:
                continue
            try:
                blk = await bf.block(target_height)
                if blk:
                    self._recent_blocks.append({
                        "height": blk.get("height", target_height),
                        "time": blk.get("time", 0),
                        "tx_count": blk.get("tx_count", 0),
                        "hash": blk.get("hash", ""),
                        "epoch": blk.get("epoch", 0),
                        "slot": blk.get("slot", 0),
                    })
            except Exception:
                continue  # best-effort backfill

    def _compute_block_stats(self) -> None:
        """Compute rolling averages from recent block data."""
        blocks = list(self._recent_blocks)
        if len(blocks) < 2:
            self._health_score = 50.0  # insufficient data
            return

        # Block time deltas
        time_deltas: list[float] = []
        for i in range(1, len(blocks)):
            t_prev = blocks[i - 1].get("time", 0)
            t_curr = blocks[i].get("time", 0)
            if t_prev > 0 and t_curr > 0:
                delta = t_curr - t_prev
                if 0 < delta < 600:  # sanity: ignore deltas > 10min (likely gap)
                    time_deltas.append(delta)

        if time_deltas:
            self._avg_block_time = sum(time_deltas) / len(time_deltas)
        else:
            self._avg_block_time = 0.0

        # Tx counts
        tx_counts = [b.get("tx_count", 0) for b in blocks]
        self._avg_tx_count = sum(tx_counts) / len(tx_counts) if tx_counts else 0.0
        empty_count = sum(1 for tc in tx_counts if tc == 0)
        self._empty_block_ratio = empty_count / len(tx_counts) if tx_counts else 0.0

        # Health score 0-100
        # Components:
        #   1. Block time consistency (40 points): how close avg is to expected
        #   2. Throughput (30 points): based on avg tx count (0 txs = 0, 50+ = full)
        #   3. Empty block ratio (30 points): fewer empty = better

        # Block time score
        if self._avg_block_time > 0:
            bt_deviation = abs(self._avg_block_time - EXPECTED_BLOCK_TIME_S) / EXPECTED_BLOCK_TIME_S
            bt_score = max(0.0, 40.0 * (1.0 - bt_deviation))
        else:
            bt_score = 0.0

        # Throughput score (avg tx count, 50 txs/block = full marks)
        tp_score = min(30.0, (self._avg_tx_count / 50.0) * 30.0)

        # Empty block penalty
        eb_score = 30.0 * (1.0 - self._empty_block_ratio)

        self._health_score = max(0.0, min(100.0, bt_score + tp_score + eb_score))

    # -- consensus parameter analysis ----------------------------------------

    async def _tune_consensus(self, bf: BlockfrostClient) -> None:
        """Fetch protocol params, detect changes across epochs, analyze fees."""
        try:
            params = await bf.protocol_params()
        except Exception as exc:
            self.log.error("chain.params_fetch_failed", error=str(exc))
            return

        if not params:
            return

        current_epoch = params.get("epoch", self._current_epoch)
        if current_epoch is None:
            return

        # Track protocol version for hard fork detection
        p_major = params.get("protocol_major_ver", params.get("protocol_major", 0))
        p_minor = params.get("protocol_minor_ver", params.get("protocol_minor", 0))

        if self._protocol_major is not None:
            if p_major != self._protocol_major or p_minor != self._protocol_minor:
                self.log.warning("chain.protocol_version_change",
                                 old_major=self._protocol_major, old_minor=self._protocol_minor,
                                 new_major=p_major, new_minor=p_minor)
                await self.broadcast("alert", {
                    "type": "hard_fork_detected",
                    "source": "ChainArchitect",
                    "old_version": f"{self._protocol_major}.{self._protocol_minor}",
                    "new_version": f"{p_major}.{p_minor}",
                    "epoch": current_epoch,
                }, priority=3)

        self._protocol_major = p_major
        self._protocol_minor = p_minor

        # Compare against previous epoch params
        if self._prev_epoch_number is not None and current_epoch != self._prev_epoch_number:
            changes = self._diff_params(self._prev_epoch_params, params)
            if changes:
                cost_increase = self._detect_cost_increase(changes, params)
                change_record = {
                    "from_epoch": self._prev_epoch_number,
                    "to_epoch": current_epoch,
                    "changes": changes,
                    "cost_increase": cost_increase,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._param_change_history.append(change_record)
                self.memory.remember("decisions", {
                    "type": "param_change_detected",
                    **change_record,
                })
                self.log.warning("chain.params_changed",
                                 epoch=current_epoch,
                                 num_changes=len(changes),
                                 cost_increase=cost_increase)

                if cost_increase:
                    await self.broadcast("alert", {
                        "type": "cost_increase_detected",
                        "source": "ChainArchitect",
                        "epoch": current_epoch,
                        "changes": changes,
                        "message": "Protocol parameter change INCREASES transaction costs",
                    }, priority=2)

        # Store current params for next comparison
        self._prev_epoch_params = params
        self._prev_epoch_number = current_epoch

        self.memory.remember("decisions", {
            "type": "consensus_tuning",
            "consensus": self.consensus_type,
            "epoch": current_epoch,
            "min_fee_a": params.get("min_fee_a"),
            "min_fee_b": params.get("min_fee_b"),
            "price_mem": params.get("price_mem"),
            "price_step": params.get("price_step"),
            "protocol_version": f"{p_major}.{p_minor}",
            "action": "parameters_tracked",
        })

    def _diff_params(self, old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
        """Compare two sets of protocol params, return list of changes."""
        # Keys we care about for cost and consensus
        watched_keys = [
            "min_fee_a", "min_fee_b", "max_tx_size", "max_val_size",
            "key_deposit", "pool_deposit", "min_pool_cost",
            "price_mem", "price_step", "max_tx_ex_mem", "max_tx_ex_steps",
            "max_block_ex_mem", "max_block_ex_steps",
            "collateral_percent", "max_collateral_inputs",
            "coins_per_utxo_size", "coins_per_utxo_word",
            "cost_models", "protocol_major_ver", "protocol_minor_ver",
            "protocol_major", "protocol_minor",
            "max_block_size", "max_block_header_size",
        ]
        changes = []
        for key in watched_keys:
            old_val = old.get(key)
            new_val = new.get(key)
            if old_val is not None and new_val is not None and old_val != new_val:
                # Skip deep-diffing cost_models (too large), just note it changed
                if key == "cost_models":
                    changes.append({"param": key, "old": "<cost_model>", "new": "<cost_model_updated>"})
                else:
                    changes.append({"param": key, "old": old_val, "new": new_val})
        return changes

    def _detect_cost_increase(self, changes: list[dict[str, Any]],
                              current_params: dict[str, Any]) -> bool:
        """Check if any parameter change would increase transaction costs."""
        cost_increasing_patterns = {
            "min_fee_a": lambda o, n: _safe_num(n) > _safe_num(o),
            "min_fee_b": lambda o, n: _safe_num(n) > _safe_num(o),
            "price_mem": lambda o, n: _safe_float(n) > _safe_float(o),
            "price_step": lambda o, n: _safe_float(n) > _safe_float(o),
            "collateral_percent": lambda o, n: _safe_num(n) > _safe_num(o),
            "coins_per_utxo_size": lambda o, n: _safe_num(n) > _safe_num(o),
            "coins_per_utxo_word": lambda o, n: _safe_num(n) > _safe_num(o),
        }
        for change in changes:
            param = change["param"]
            checker = cost_increasing_patterns.get(param)
            if checker and checker(change["old"], change["new"]):
                return True
        return False

    # -- cost efficiency tracking --------------------------------------------

    async def _track_cost_efficiency(self, bf: BlockfrostClient) -> None:
        """Sample recent transactions to compute average fees, compare to targets."""
        blocks = list(self._recent_blocks)
        if len(blocks) < 2:
            return

        # Sample txs from recent blocks
        sample_blocks = blocks[-FEE_SAMPLE_BLOCKS:]
        fees: list[int] = []

        for blk in sample_blocks:
            blk_hash = blk.get("hash", "")
            if not blk_hash or blk.get("tx_count", 0) == 0:
                continue

            try:
                tx_hashes = await bf.block_txs(blk_hash)
            except Exception:
                continue

            if not tx_hashes:
                continue

            # Sample a subset of txs to avoid excessive API calls
            sample = tx_hashes[:TX_SAMPLE_PER_BLOCK]
            for tx_hash in sample:
                try:
                    tx_data = await bf.tx(tx_hash)
                    if tx_data:
                        fee = tx_data.get("fees")
                        if fee is not None:
                            fees.append(int(fee))
                except Exception:
                    continue

        if not fees:
            return

        avg_fee = sum(fees) / len(fees)
        min_fee = min(fees)
        max_fee = max(fees)
        self._avg_tx_fee_lovelace = avg_fee

        now_iso = datetime.now(timezone.utc).isoformat()
        self._fee_history.append({
            "timestamp": now_iso,
            "avg_fee": round(avg_fee),
            "min_fee": min_fee,
            "max_fee": max_fee,
            "sample_size": len(fees),
        })

        # Compare against cost targets (L1 — this monitors Cardano mainchain)
        cost_alerts = []
        for op_name, target in COST_TARGETS.items():
            l1_target = target.get("l1_target_lovelace")
            wallet_fee = target.get("current_wallet_fee_lovelace")
            if l1_target is None:
                continue

            if avg_fee > l1_target:
                cost_alerts.append({
                    "operation": op_name,
                    "avg_fee": round(avg_fee),
                    "l1_target": l1_target,
                    "sidechain_target": target.get("sidechain_target_lovelace"),
                    "wallet_fee": wallet_fee,
                    "exceeds_target_by": round(avg_fee - l1_target),
                    "still_beats_wallet": avg_fee < wallet_fee if wallet_fee else None,
                })

        if cost_alerts:
            self.log.warning("chain.cost_target_exceeded",
                             num_operations=len(cost_alerts),
                             avg_fee=round(avg_fee))
            await self.broadcast("alert", {
                "type": "cost_target_exceeded",
                "source": "ChainArchitect",
                "avg_tx_fee_lovelace": round(avg_fee),
                "violations": cost_alerts,
                "epoch": self._current_epoch,
            }, priority=2)

        # Send cost report to TreasuryVault
        await self.send("TreasuryVault", "report", {
            "type": "cost_efficiency_report",
            "avg_tx_fee_lovelace": round(avg_fee),
            "min_fee": min_fee,
            "max_fee": max_fee,
            "sample_size": len(fees),
            "cost_target_violations": len(cost_alerts),
            "epoch": self._current_epoch,
            "block_height": self._current_block_height,
        })

        self.memory.remember("decisions", {
            "type": "cost_tracking",
            "avg_fee": round(avg_fee),
            "min_fee": min_fee,
            "max_fee": max_fee,
            "sample_size": len(fees),
            "violations": len(cost_alerts),
        })

        self.log.info("chain.cost_tracking",
                      avg_fee=round(avg_fee),
                      sample=len(fees),
                      violations=len(cost_alerts))

    # -- upgrade evaluation --------------------------------------------------

    async def _evaluate_upgrades(self, bf: BlockfrostClient) -> None:
        """Detect protocol upgrades by comparing params and version changes."""
        if not self._prev_epoch_params:
            return

        params = self._prev_epoch_params  # already fetched in _tune_consensus
        p_major = params.get("protocol_major_ver", params.get("protocol_major", 0))
        p_minor = params.get("protocol_minor_ver", params.get("protocol_minor", 0))

        # Check for recent param changes that constitute an upgrade
        recent_changes = [
            ch for ch in self._param_change_history[-5:]
            if ch.get("to_epoch") == self._current_epoch
        ]

        if not recent_changes:
            self.memory.remember("decisions", {
                "type": "upgrade_evaluation",
                "epoch": self._current_epoch,
                "protocol_version": f"{p_major}.{p_minor}",
                "result": "no_upgrade_needed",
            })
            return

        # Generate upgrade impact report
        all_changes: list[dict[str, Any]] = []
        has_cost_increase = False
        for record in recent_changes:
            all_changes.extend(record.get("changes", []))
            if record.get("cost_increase"):
                has_cost_increase = True

        impact_report = {
            "type": "upgrade_impact_report",
            "epoch": self._current_epoch,
            "protocol_version": f"{p_major}.{p_minor}",
            "num_param_changes": len(all_changes),
            "changes": all_changes,
            "cost_increase": has_cost_increase,
            "recommendation": (
                "REVIEW REQUIRED: Parameter changes increase costs -- "
                "evaluate sidechain fee adjustments"
                if has_cost_increase
                else "Parameter changes detected -- no cost increase, monitor for stability"
            ),
        }

        self.memory.remember("decisions", {
            "type": "upgrade_evaluation",
            **impact_report,
        })

        self.log.info("chain.upgrade_evaluated",
                      epoch=self._current_epoch,
                      changes=len(all_changes),
                      cost_impact="increase" if has_cost_increase else "neutral")

        # Broadcast upgrade report to all agents
        await self.broadcast("report", {
            "type": "protocol_upgrade_report",
            "source": "ChainArchitect",
            **impact_report,
        }, priority=2 if has_cost_increase else 1)

    # -- message handling ----------------------------------------------------

    async def handle_message(self, msg: Message) -> None:
        bf = self._get_blockfrost()

        if msg.kind == "request" and msg.payload.get("type") == "protocol_change":
            await self._handle_protocol_change(msg, bf)

        elif msg.kind == "request" and msg.payload.get("type") == "chain_health":
            await self._handle_chain_health_query(msg)

        elif msg.kind == "request" and msg.payload.get("type") == "cost_check":
            await self._handle_cost_check(msg)

        elif msg.kind == "alert" and msg.payload.get("severity") == "critical":
            self.log.warning("chain.emergency", detail=msg.payload)
            await self._emergency_response(msg.payload, bf)

        elif msg.kind == "alert" and msg.payload.get("type") == "upstream_alert":
            await self._handle_upstream_alert(msg, bf)

        else:
            self.log.debug("chain.unhandled_message", kind=msg.kind, sender=msg.sender)

    async def _handle_protocol_change(self, msg: Message, bf: BlockfrostClient | None) -> None:
        """Evaluate a protocol change request using real param data."""
        self.memory.remember("decisions", {
            "type": "protocol_change_request",
            "from": msg.sender,
            "detail": msg.payload,
            "decision": "evaluating",
        })

        cost_impact = "unknown"
        current_fees = {}

        if bf is not None:
            try:
                params = await bf.protocol_params()
                if params:
                    current_fees = {
                        "min_fee_a": params.get("min_fee_a"),
                        "min_fee_b": params.get("min_fee_b"),
                        "price_mem": params.get("price_mem"),
                        "price_step": params.get("price_step"),
                    }

                    # Evaluate if the proposed change would increase costs
                    proposed = msg.payload.get("proposed_params", {})
                    if proposed:
                        increases = []
                        for key in ("min_fee_a", "min_fee_b", "price_mem", "price_step"):
                            old_val = params.get(key)
                            new_val = proposed.get(key)
                            if old_val is not None and new_val is not None:
                                if _safe_float(new_val) > _safe_float(old_val):
                                    increases.append(key)
                        cost_impact = "increase" if increases else "neutral_or_decrease"
                    else:
                        cost_impact = "no_proposed_params"
            except Exception as exc:
                self.log.error("chain.param_check_failed", error=str(exc))

        await self.send(msg.sender, "response", {
            "type": "protocol_change_ack",
            "status": "evaluated",
            "cost_impact": cost_impact,
            "current_fees": current_fees,
            "avg_tx_fee_lovelace": round(self._avg_tx_fee_lovelace) if self._avg_tx_fee_lovelace else None,
            "health_score": round(self._health_score, 1),
            "recommendation": (
                "REJECT: Change increases costs -- violates core mission"
                if cost_impact == "increase"
                else "ACCEPTABLE: No cost increase detected"
            ),
        })

    async def _handle_chain_health_query(self, msg: Message) -> None:
        """Return computed health score with full metrics."""
        blocks = list(self._recent_blocks)
        tx_counts = [b.get("tx_count", 0) for b in blocks] if blocks else []

        await self.send(msg.sender, "response", {
            "type": "chain_health_report",
            "health_score": round(self._health_score, 1),
            "avg_block_time_s": round(self._avg_block_time, 2),
            "expected_block_time_s": EXPECTED_BLOCK_TIME_S,
            "avg_tx_per_block": round(self._avg_tx_count, 2),
            "min_tx_per_block": min(tx_counts) if tx_counts else 0,
            "max_tx_per_block": max(tx_counts) if tx_counts else 0,
            "empty_block_ratio": round(self._empty_block_ratio, 3),
            "blocks_tracked": len(blocks),
            "epoch": self._current_epoch,
            "slot": self._current_slot,
            "block_height": self._current_block_height,
            "protocol_version": (
                f"{self._protocol_major}.{self._protocol_minor}"
                if self._protocol_major is not None else None
            ),
        })

    async def _handle_cost_check(self, msg: Message) -> None:
        """Compare a fee against cost targets and respond."""
        operation = msg.payload.get("operation", "")
        estimated_fee = msg.payload.get("fee_lovelace", 0)

        target = COST_TARGETS.get(operation)
        if not target:
            await self.send(msg.sender, "response", {
                "type": "cost_check_result",
                "operation": operation,
                "has_target": False,
                "avg_network_fee": round(self._avg_tx_fee_lovelace) if self._avg_tx_fee_lovelace else None,
            })
            return

        chain = msg.payload.get("chain", "sidechain")
        wallet_fee = target.get("current_wallet_fee_lovelace", 0)
        if chain == "sidechain":
            our_target = target.get("sidechain_target_lovelace",
                                    target.get("l1_target_lovelace", 0))
        else:
            our_target = target.get("l1_target_lovelace", 0)

        await self.send(msg.sender, "response", {
            "type": "cost_check_result",
            "operation": operation,
            "chain": chain,
            "has_target": True,
            "estimated_fee": estimated_fee,
            "our_target": our_target,
            "l1_target": target.get("l1_target_lovelace"),
            "sidechain_target": target.get("sidechain_target_lovelace"),
            "current_wallet_fee": wallet_fee,
            "beats_wallets": estimated_fee < wallet_fee if wallet_fee else None,
            "meets_target": estimated_fee <= our_target if our_target else None,
            "user_chooses": target.get("user_chooses", False),
            "avg_network_fee": round(self._avg_tx_fee_lovelace) if self._avg_tx_fee_lovelace else None,
            "strategy": target.get("strategy", ""),
        })

    async def _handle_upstream_alert(self, msg: Message, bf: BlockfrostClient | None) -> None:
        """Evaluate upstream cardano-node/ledger changes."""
        detail = msg.payload

        # Snapshot current state for context
        chain_state = {
            "health_score": round(self._health_score, 1),
            "avg_block_time_s": round(self._avg_block_time, 2),
            "avg_tx_fee": round(self._avg_tx_fee_lovelace) if self._avg_tx_fee_lovelace else None,
            "epoch": self._current_epoch,
            "block_height": self._current_block_height,
            "protocol_version": (
                f"{self._protocol_major}.{self._protocol_minor}"
                if self._protocol_major is not None else None
            ),
        }

        self.memory.remember("tech_updates", {
            "type": "upstream_alert",
            "from": msg.sender,
            "detail": detail,
            "chain_state_at_alert": chain_state,
        })

        self.log.info("chain.upstream_alert",
                      source=msg.sender,
                      alert_type=detail.get("alert_type", "unknown"))

        await self.send(msg.sender, "response", {
            "type": "upstream_alert_ack",
            "status": "evaluated",
            "chain_state": chain_state,
            "recommendation": "monitoring_for_impact",
        })

    async def _emergency_response(self, detail: dict, bf: BlockfrostClient | None) -> None:
        """Emergency response with real chain state snapshot."""
        chain_snapshot: dict[str, Any] = {
            "health_score": round(self._health_score, 1),
            "avg_block_time_s": round(self._avg_block_time, 2),
            "avg_tx_fee_lovelace": round(self._avg_tx_fee_lovelace) if self._avg_tx_fee_lovelace else None,
            "empty_block_ratio": round(self._empty_block_ratio, 3),
            "epoch": self._current_epoch,
            "slot": self._current_slot,
            "block_height": self._current_block_height,
            "blocks_tracked": len(self._recent_blocks),
            "protocol_version": (
                f"{self._protocol_major}.{self._protocol_minor}"
                if self._protocol_major is not None else None
            ),
        }

        # Try to get live tip if Blockfrost available
        if bf is not None:
            try:
                tip = await bf.tip()
                if tip:
                    chain_snapshot["live_tip"] = tip
            except Exception:
                chain_snapshot["live_tip"] = "fetch_failed"

        # Recent fee data
        if self._fee_history:
            chain_snapshot["recent_fees"] = list(self._fee_history)[-5:]

        await self.broadcast("alert", {
            "type": "chain_emergency",
            "detail": detail,
            "chain_snapshot": chain_snapshot,
            "action": "investigating",
        }, priority=3)

    # -- learning ------------------------------------------------------------

    async def learn(self) -> None:
        """Study latest consensus research, L2 innovations, Cardano CIPs."""
        # Record what we're tracking
        topics = [
            "ouroboros_leios_progress",
            "parallel_block_validation",
            "zk_rollup_integration_potential",
            "input_endorsers_cardano",
            "plutus_v3_cost_model_updates",
        ]

        # Analyze our own performance trends
        learnings: dict[str, Any] = {
            "area": "consensus",
            "topics": topics,
        }

        if self._fee_history:
            fees = [entry["avg_fee"] for entry in self._fee_history]
            if len(fees) >= 2:
                fee_trend = fees[-1] - fees[0]
                learnings["fee_trend"] = "increasing" if fee_trend > 0 else "decreasing"
                learnings["fee_trend_amount"] = round(fee_trend)

        if self._param_change_history:
            learnings["param_changes_observed"] = len(self._param_change_history)
            cost_increases = sum(1 for ch in self._param_change_history if ch.get("cost_increase"))
            learnings["cost_increasing_changes"] = cost_increases

        self.memory.remember("tech_updates", learnings)
        self.log.info("learning.consensus",
                      topics="ouroboros, zk-rollups, parallel validation, plutus-v3")

    # -- reporting -----------------------------------------------------------

    def report(self) -> dict[str, Any]:
        """Generate full status report for human council."""
        base = super().report()

        blocks = list(self._recent_blocks)
        tx_counts = [b.get("tx_count", 0) for b in blocks] if blocks else []

        # Cost target comparison
        cost_status: dict[str, Any] = {}
        for op_name, target in COST_TARGETS.items():
            l1_target = target.get("l1_target_lovelace")
            sc_target = target.get("sidechain_target_lovelace")
            wallet_fee = target.get("current_wallet_fee_lovelace")
            if l1_target is not None:
                cost_status[op_name] = {
                    "l1_target": l1_target,
                    "sidechain_target": sc_target,
                    "wallet_fee": wallet_fee,
                    "user_chooses": target.get("user_chooses", False),
                    "avg_network_fee": round(self._avg_tx_fee_lovelace) if self._avg_tx_fee_lovelace else None,
                    "l1_target_met": (
                        self._avg_tx_fee_lovelace <= l1_target
                        if self._avg_tx_fee_lovelace else None
                    ),
                    "beats_wallet": (
                        self._avg_tx_fee_lovelace < wallet_fee
                        if self._avg_tx_fee_lovelace and wallet_fee else None
                    ),
                }

        base.update({
            "chain_health": {
                "health_score": round(self._health_score, 1),
                "avg_block_time_s": round(self._avg_block_time, 2),
                "expected_block_time_s": EXPECTED_BLOCK_TIME_S,
                "avg_tx_per_block": round(self._avg_tx_count, 2),
                "min_tx_per_block": min(tx_counts) if tx_counts else 0,
                "max_tx_per_block": max(tx_counts) if tx_counts else 0,
                "empty_block_ratio": round(self._empty_block_ratio, 3),
                "blocks_tracked": len(blocks),
            },
            "chain_tip": {
                "epoch": self._current_epoch,
                "slot": self._current_slot,
                "block_height": self._current_block_height,
                "protocol_version": (
                    f"{self._protocol_major}.{self._protocol_minor}"
                    if self._protocol_major is not None else None
                ),
            },
            "cost_efficiency": {
                "avg_tx_fee_lovelace": round(self._avg_tx_fee_lovelace) if self._avg_tx_fee_lovelace else None,
                "fee_samples": len(self._fee_history),
                "cost_targets": cost_status,
            },
            "protocol_changes": {
                "total_detected": len(self._param_change_history),
                "recent": self._param_change_history[-3:] if self._param_change_history else [],
            },
            "blockfrost_configured": self._bf_available is True,
        })
        return base


# -- utility helpers ---------------------------------------------------------

def _safe_num(val: Any) -> int:
    """Convert a value to int safely for comparison."""
    try:
        return int(val)
    except (TypeError, ValueError):
        return 0


def _safe_float(val: Any) -> float:
    """Convert a value to float safely for comparison."""
    try:
        return float(val)
    except (TypeError, ValueError):
        return 0.0
