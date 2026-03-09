"""Agent 8: SentinelGuard — Security auditor and threat response.

Responsibilities:
- Continuous smart contract auditing via Blockfrost chain data
- Network monitoring and anomaly detection (block rate, whale moves, script costs)
- Threat level management with auto-escalation/de-escalation
- Incident response lifecycle (DETECTED -> INVESTIGATING -> CONTAINED -> RESOLVED)
- Peer agent health monitoring
- Bug bounty program management
- Security best practices enforcement
- Can hire security researchers

Blockfrost dependency:
    All chain queries require BLOCKFROST_API_KEY in environment.
    If not configured, SentinelGuard logs a warning and skips chain queries,
    but continues operating for inter-agent message handling and health checks.
"""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from autono.core.agent_base import AgentCapability, AutonomousAgent, Message
from autono.services.blockfrost import BlockfrostClient, BlockfrostError


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Expected Cardano block time ~20s; alert if gap exceeds 2x
NORMAL_BLOCK_TIME_S = 20
BLOCK_TIME_ALERT_MULTIPLIER = 2

# Whale alert threshold: 1M ADA = 1_000_000_000_000 lovelace
WHALE_THRESHOLD_LOVELACE = 1_000_000_000_000

# Script execution cost thresholds (in ExUnits)
HIGH_REDEEMER_MEM_THRESHOLD = 10_000_000  # 10M memory units
HIGH_REDEEMER_STEPS_THRESHOLD = 5_000_000_000  # 5B CPU steps

# Expected minimum transactions per block (alert on sustained empty blocks)
MIN_EXPECTED_TXS_PER_BLOCK = 1

# Health check timeout for peer agents (seconds)
AGENT_HEALTH_TIMEOUT_S = 10.0

# Threat level auto-de-escalation: seconds without new findings before stepping down
DEESCALATION_COOLDOWN_S = 300  # 5 minutes

# Maximum number of recent blocks to sample per monitoring cycle
MONITOR_BLOCK_SAMPLE = 5

# Maximum audit findings kept in memory
MAX_AUDIT_HISTORY = 500

# Maximum incidents kept in memory
MAX_INCIDENT_HISTORY = 200


class ThreatLevel(str, Enum):
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    RED = "red"

    @property
    def severity_rank(self) -> int:
        return {"green": 0, "yellow": 1, "orange": 2, "red": 3}[self.value]


class IncidentPhase(str, Enum):
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    RESOLVED = "resolved"


# ---------------------------------------------------------------------------
# SentinelGuard
# ---------------------------------------------------------------------------

class SentinelGuard(AutonomousAgent):
    def __init__(self) -> None:
        super().__init__(
            name="SentinelGuard",
            role="Security sentinel — auditing, monitoring, threat response",
            capabilities=[
                AgentCapability.AUDIT,
                AgentCapability.RESEARCH,
                AgentCapability.HIRE,
                AgentCapability.BUILD_PRODUCT,
            ],
        )
        # ----- threat state -----
        self.threat_level = ThreatLevel.GREEN
        self._last_escalation_time: float = 0.0
        self._active_anomalies: list[dict[str, Any]] = []

        # ----- audit tracking -----
        self.audits_completed = 0
        self.vulnerabilities_found = 0
        self._audited_scripts: dict[str, dict[str, Any]] = {}  # hash -> findings
        self._audit_history: list[dict[str, Any]] = []

        # ----- network monitoring state -----
        self._last_block_height: int | None = None
        self._last_block_time: int | None = None
        self._recent_block_tx_counts: list[int] = []
        self._empty_block_streak: int = 0

        # ----- incident tracking -----
        self._incidents: dict[str, dict[str, Any]] = {}  # id -> incident

        # ----- agent health tracking -----
        self._peer_health: dict[str, dict[str, Any]] = {}
        # name -> {last_check, last_response, status, response_time_ms}
        self._health_check_cycle: int = 0

        # ----- bug bounty -----
        self.bug_bounty_pool = 0

        # ----- blockfrost -----
        self._bf: BlockfrostClient | None = None
        self._bf_available = False

        # ----- monitoring targets -----
        self.monitoring_targets = [
            "bridge_contracts",
            "dex_contracts",
            "lending_contracts",
            "governance_contracts",
            "validator_behavior",
            "network_traffic",
            "mempool_activity",
        ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    @property
    def work_interval(self) -> float:
        return 5.0  # security never sleeps

    async def _ensure_blockfrost(self) -> bool:
        """Lazy-init Blockfrost client.  Returns True if usable."""
        if self._bf is None:
            self._bf = BlockfrostClient()
        if not self._bf.is_configured:
            if self._bf_available:
                # Only warn once on transition
                self.log.warning("sentinel.blockfrost_not_configured",
                                 hint="Set BLOCKFROST_API_KEY — chain queries disabled")
            self._bf_available = False
            return False
        # Quick health probe on first use
        if not self._bf_available:
            try:
                health = await self._bf.health()
                self._bf_available = health.get("is_healthy", False)
                if self._bf_available:
                    self.log.info("sentinel.blockfrost_connected",
                                 network=self._bf.network)
                else:
                    self.log.warning("sentinel.blockfrost_unhealthy")
            except Exception as exc:
                self.log.warning("sentinel.blockfrost_probe_failed", error=str(exc))
                self._bf_available = False
        return self._bf_available

    # ------------------------------------------------------------------
    # Core work loop
    # ------------------------------------------------------------------

    async def do_work(self) -> None:
        chain_ok = await self._ensure_blockfrost()

        if chain_ok:
            await self._monitor_network()
            await self._audit_contracts()

        # Always run regardless of Blockfrost
        await self._evaluate_threat_level()
        await self._check_deescalation()
        await self._peer_health_check()
        await self._advance_incidents()

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request" and msg.payload.get("type") == "audit":
            result = await self._run_audit(msg.payload)
            await self.send(msg.sender, "response", {"type": "audit_result", **result})

        elif msg.kind == "alert":
            await self._handle_security_alert(msg)

        elif msg.kind == "response" and msg.payload.get("type") == "health_check_reply":
            self._record_health_response(msg)

        elif msg.kind == "alert" and msg.payload.get("source") == "RepoWatcher":
            await self._handle_upstream_alert(msg)

        elif msg.kind == "request" and msg.payload.get("type") == "threat_status":
            await self.send(msg.sender, "response", {
                "type": "threat_status",
                "threat_level": self.threat_level.value,
                "active_anomalies": len(self._active_anomalies),
                "open_incidents": sum(
                    1 for i in self._incidents.values()
                    if i["phase"] != IncidentPhase.RESOLVED
                ),
                "audits_completed": self.audits_completed,
                "vulnerabilities_found": self.vulnerabilities_found,
            })

    # ------------------------------------------------------------------
    # Learning
    # ------------------------------------------------------------------

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "security",
            "topics": [
                "latest_defi_exploits",
                "formal_verification_advances",
                "zero_day_patterns",
                "bridge_attack_vectors",
                "mev_sandwich_detection",
                "plutus_vulnerability_patterns",
                "cardano_hard_fork_security",
            ],
        })

        # Summarize recent audit findings for learning
        recent_audits = self._audit_history[-20:]
        vuln_types: dict[str, int] = {}
        for audit in recent_audits:
            for finding in audit.get("findings", []):
                vtype = finding.get("type", "unknown")
                vuln_types[vtype] = vuln_types.get(vtype, 0) + 1

        if vuln_types:
            self.memory.remember("learnings", {
                "type": "vulnerability_trends",
                "period_audits": len(recent_audits),
                "vulnerability_distribution": vuln_types,
            })

    # ------------------------------------------------------------------
    # Network monitoring
    # ------------------------------------------------------------------

    async def _monitor_network(self) -> None:
        """Monitor chain health via Blockfrost: block rate, tx volume, whale moves."""
        assert self._bf is not None

        try:
            latest = await self._bf.latest_block()
        except BlockfrostError as exc:
            self.log.error("sentinel.block_fetch_failed", error=str(exc))
            return

        if not latest:
            return

        current_height = latest.get("height", 0)
        current_time = latest.get("time", 0)
        block_tx_count = latest.get("tx_count", 0)
        block_hash = latest.get("hash", "")

        # --- Block production rate check ---
        if self._last_block_time is not None and current_time > self._last_block_time:
            gap = current_time - self._last_block_time
            if gap > NORMAL_BLOCK_TIME_S * BLOCK_TIME_ALERT_MULTIPLIER:
                self._register_anomaly(
                    anomaly_type="slow_block_production",
                    severity="medium",
                    detail=f"Block gap {gap}s (normal ~{NORMAL_BLOCK_TIME_S}s)",
                    data={"gap_seconds": gap, "block_height": current_height},
                )

        # --- Empty / low-tx block detection ---
        self._recent_block_tx_counts.append(block_tx_count)
        if len(self._recent_block_tx_counts) > 20:
            self._recent_block_tx_counts = self._recent_block_tx_counts[-20:]

        if block_tx_count < MIN_EXPECTED_TXS_PER_BLOCK:
            self._empty_block_streak += 1
            if self._empty_block_streak >= 3:
                self._register_anomaly(
                    anomaly_type="sustained_empty_blocks",
                    severity="medium",
                    detail=f"{self._empty_block_streak} consecutive low/empty blocks",
                    data={"streak": self._empty_block_streak, "block_height": current_height},
                )
        else:
            self._empty_block_streak = 0

        # --- Whale movement detection ---
        # Only scan if the block is new (avoid re-scanning same block)
        if self._last_block_height is not None and current_height > self._last_block_height:
            await self._scan_block_for_whales(block_hash, current_height)

        # --- Script execution cost monitoring ---
        if self._last_block_height is not None and current_height > self._last_block_height:
            await self._scan_block_for_expensive_scripts(block_hash, current_height)

        self._last_block_height = current_height
        self._last_block_time = current_time

        self.memory.remember("decisions", {
            "type": "network_monitor",
            "block_height": current_height,
            "tx_count": block_tx_count,
            "anomalies_active": len(self._active_anomalies),
            "threat_level": self.threat_level.value,
        })

    async def _scan_block_for_whales(self, block_hash: str, height: int) -> None:
        """Check transactions in a block for large ADA movements."""
        assert self._bf is not None
        try:
            tx_hashes = await self._bf.block_txs(block_hash)
        except BlockfrostError:
            return

        if not tx_hashes:
            return

        # Sample up to 20 transactions to stay within rate limits
        sample = tx_hashes[:20]
        for tx_hash in sample:
            try:
                tx_utxo_data = await self._bf.tx_utxos(tx_hash)
            except BlockfrostError:
                continue
            if not tx_utxo_data:
                continue

            # Sum ADA in outputs to detect large movements
            total_output_lovelace = 0
            outputs = tx_utxo_data.get("outputs", [])
            for output in outputs:
                for amount in output.get("amount", []):
                    if amount.get("unit") == "lovelace":
                        total_output_lovelace += int(amount.get("quantity", 0))

            if total_output_lovelace >= WHALE_THRESHOLD_LOVELACE:
                ada_amount = total_output_lovelace / 1_000_000
                self._register_anomaly(
                    anomaly_type="whale_movement",
                    severity="low",
                    detail=f"Large ADA movement: {ada_amount:,.0f} ADA in tx {tx_hash[:16]}...",
                    data={
                        "tx_hash": tx_hash,
                        "lovelace": total_output_lovelace,
                        "ada": ada_amount,
                        "block_height": height,
                    },
                )

    async def _scan_block_for_expensive_scripts(self, block_hash: str, height: int) -> None:
        """Detect unusually expensive script executions in a block."""
        assert self._bf is not None
        try:
            tx_hashes = await self._bf.block_txs(block_hash)
        except BlockfrostError:
            return

        if not tx_hashes:
            return

        sample = tx_hashes[:20]
        for tx_hash in sample:
            try:
                tx_data = await self._bf.tx(tx_hash)
            except BlockfrostError:
                continue
            if not tx_data:
                continue

            # Check redeemer execution costs if present
            # Blockfrost tx details contain 'valid_contract' and script size info
            # We'll check via tx_utxos for script ref usage
            script_size = tx_data.get("size", 0)
            fees = int(tx_data.get("fees", "0"))

            # High fees relative to typical suggest expensive script execution
            # Typical simple tx fee: ~0.17 ADA (170_000 lovelace)
            # Script txs with very high fees (>5 ADA) warrant attention
            if fees > 5_000_000:
                try:
                    utxo_data = await self._bf.tx_utxos(tx_hash)
                except BlockfrostError:
                    continue
                if not utxo_data:
                    continue

                # Check if any outputs have datum hashes (indicating script interaction)
                has_scripts = any(
                    o.get("data_hash") or o.get("inline_datum") or o.get("reference_script_hash")
                    for o in utxo_data.get("outputs", [])
                )
                if has_scripts:
                    self._register_anomaly(
                        anomaly_type="expensive_script_execution",
                        severity="low",
                        detail=f"High-cost script tx: {fees / 1_000_000:.2f} ADA fee, tx {tx_hash[:16]}...",
                        data={
                            "tx_hash": tx_hash,
                            "fees_lovelace": fees,
                            "fees_ada": fees / 1_000_000,
                            "size_bytes": script_size,
                            "block_height": height,
                        },
                    )

    # ------------------------------------------------------------------
    # Contract auditing
    # ------------------------------------------------------------------

    async def _audit_contracts(self) -> None:
        """Periodic contract audit — scan recent blocks for new scripts."""
        assert self._bf is not None

        try:
            latest = await self._bf.latest_block()
        except BlockfrostError as exc:
            self.log.error("sentinel.audit_block_fetch_failed", error=str(exc))
            return

        if not latest:
            return

        block_hash = latest.get("hash", "")
        if not block_hash:
            return

        try:
            tx_hashes = await self._bf.block_txs(block_hash)
        except BlockfrostError:
            return

        if not tx_hashes:
            return

        # Look for script-bearing transactions
        scripts_found: list[str] = []
        for tx_hash in tx_hashes[:15]:  # rate limit friendly
            try:
                utxo_data = await self._bf.tx_utxos(tx_hash)
            except BlockfrostError:
                continue
            if not utxo_data:
                continue

            for output in utxo_data.get("outputs", []):
                ref_script = output.get("reference_script_hash")
                if ref_script and ref_script not in self._audited_scripts:
                    scripts_found.append(ref_script)

                # Also check for scripts via data_hash (datum-locked UTXOs)
                data_hash = output.get("data_hash")
                if data_hash:
                    # The output address might be a script address
                    addr = output.get("address", "")
                    if addr and len(addr) > 60:
                        # Script addresses on Cardano are typically longer
                        # We track the data_hash as something to examine
                        pass

        # Audit each newly discovered script
        for script_hash in scripts_found:
            if script_hash not in self._audited_scripts:
                findings = await self._audit_single_script(script_hash)
                self._audited_scripts[script_hash] = {
                    "hash": script_hash,
                    "audited_at": datetime.now(timezone.utc).isoformat(),
                    "findings": findings,
                }
                audit_record = {
                    "script_hash": script_hash,
                    "findings": findings,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                self._audit_history.append(audit_record)
                if len(self._audit_history) > MAX_AUDIT_HISTORY:
                    self._audit_history = self._audit_history[-MAX_AUDIT_HISTORY:]

                self.audits_completed += 1

                if findings:
                    self.vulnerabilities_found += len(findings)
                    max_sev = max(f.get("severity_rank", 0) for f in findings)
                    severity = "high" if max_sev >= 3 else "medium" if max_sev >= 2 else "low"
                    self._register_anomaly(
                        anomaly_type="contract_vulnerability",
                        severity=severity,
                        detail=f"Script {script_hash[:16]}... has {len(findings)} finding(s)",
                        data={"script_hash": script_hash, "findings": findings},
                    )

    async def _audit_single_script(self, script_hash: str) -> list[dict[str, Any]]:
        """Run vulnerability pattern checks against a single script via Blockfrost."""
        assert self._bf is not None
        findings: list[dict[str, Any]] = []

        # Fetch script metadata
        try:
            script_info = await self._bf.script(script_hash)
        except BlockfrostError as exc:
            self.log.warning("sentinel.script_fetch_failed",
                             script=script_hash[:16], error=str(exc))
            return findings

        if not script_info:
            return findings

        script_type = script_info.get("type", "")
        serialised_size = script_info.get("serialised_size")

        # Fetch redeemers for execution pattern analysis
        try:
            redeemers = await self._bf.script_redeemers(script_hash)
        except BlockfrostError:
            redeemers = []

        # --- Check 1: Missing redeemer validation ---
        # If a Plutus script has been invoked but never with a 'spend' purpose,
        # or has very few distinct redeemer patterns, flag it
        if script_type.startswith("plutus") and redeemers:
            purposes = {r.get("purpose") for r in redeemers}
            if "spend" not in purposes and "mint" not in purposes:
                findings.append({
                    "type": "missing_redeemer_validation",
                    "severity": "medium",
                    "severity_rank": 2,
                    "detail": (
                        f"Plutus script invoked but no spend/mint redeemers observed. "
                        f"Purposes seen: {purposes}. May indicate incomplete validation logic."
                    ),
                })

        # --- Check 2: Unbounded datum sizes (DoS vector) ---
        # Fetch CBOR to estimate size; very large scripts may accept unbounded input
        if script_type.startswith("plutus"):
            try:
                cbor_data = await self._bf.script_cbor(script_hash)
            except BlockfrostError:
                cbor_data = None

            if cbor_data:
                cbor_hex = cbor_data.get("cbor", "")
                cbor_bytes = len(cbor_hex) // 2 if cbor_hex else 0
                # Scripts over 16KB are suspicious — may not constrain datum size
                if cbor_bytes > 16_384:
                    findings.append({
                        "type": "potential_unbounded_datum",
                        "severity": "medium",
                        "severity_rank": 2,
                        "detail": (
                            f"Large script ({cbor_bytes:,} bytes). "
                            f"May accept unbounded datum sizes — DoS vector if datum "
                            f"validation doesn't enforce size limits."
                        ),
                        "data": {"cbor_size_bytes": cbor_bytes},
                    })

        # --- Check 3: No time-lock constraints ---
        # Check if script redeemers ever reference validity intervals
        # Scripts with many executions but no validity range patterns may lack time guards
        if script_type.startswith("plutus") and redeemers:
            # If we have a decent sample of redeemers and can check tx details
            if len(redeemers) >= 3:
                sample_redeemers = redeemers[:5]
                has_timelock = False
                for r in sample_redeemers:
                    tx_hash = r.get("tx_hash")
                    if tx_hash:
                        try:
                            tx_data = await self._bf.tx(tx_hash)
                        except BlockfrostError:
                            continue
                        if tx_data:
                            # Check if the transaction has a validity interval set
                            invalid_before = tx_data.get("invalid_before")
                            invalid_hereafter = tx_data.get("invalid_hereafter")
                            if invalid_before or invalid_hereafter:
                                has_timelock = True
                                break

                if not has_timelock:
                    findings.append({
                        "type": "no_timelock_constraints",
                        "severity": "low",
                        "severity_rank": 1,
                        "detail": (
                            f"Script has {len(redeemers)} executions but none use validity "
                            f"intervals. Missing time-lock constraints could allow replay or "
                            f"indefinite execution windows."
                        ),
                    })

        # --- Check 4: Excessive collateral requirements ---
        if script_type.startswith("plutus") and redeemers:
            for r in redeemers[:5]:
                tx_hash = r.get("tx_hash")
                if tx_hash:
                    try:
                        tx_data = await self._bf.tx(tx_hash)
                    except BlockfrostError:
                        continue
                    if not tx_data:
                        continue

                    fees = int(tx_data.get("fees", "0"))
                    # Cardano protocol: collateral = 150% of fee by default
                    # If a script consistently requires very high fees, the collateral
                    # burden on users is excessive — bad for cost mission
                    if fees > 3_000_000:  # > 3 ADA fee
                        findings.append({
                            "type": "excessive_collateral",
                            "severity": "low",
                            "severity_rank": 1,
                            "detail": (
                                f"Script execution requires {fees / 1_000_000:.2f} ADA fee "
                                f"(collateral ~{fees * 1.5 / 1_000_000:.2f} ADA). "
                                f"High cost undermines autono's mission of cheaper transactions."
                            ),
                            "data": {"fees_lovelace": fees, "tx_hash": tx_hash},
                        })
                        break  # One finding is enough

        # --- Check 5: High redeemer execution units ---
        for r in redeemers[:10]:
            unit_mem = r.get("unit_mem", 0)
            unit_steps = r.get("unit_steps", 0)
            if isinstance(unit_mem, str):
                unit_mem = int(unit_mem)
            if isinstance(unit_steps, str):
                unit_steps = int(unit_steps)

            if unit_mem > HIGH_REDEEMER_MEM_THRESHOLD or unit_steps > HIGH_REDEEMER_STEPS_THRESHOLD:
                findings.append({
                    "type": "high_execution_cost",
                    "severity": "medium",
                    "severity_rank": 2,
                    "detail": (
                        f"Redeemer uses {unit_mem:,} mem / {unit_steps:,} steps. "
                        f"Thresholds: {HIGH_REDEEMER_MEM_THRESHOLD:,} mem / "
                        f"{HIGH_REDEEMER_STEPS_THRESHOLD:,} steps."
                    ),
                    "data": {"unit_mem": unit_mem, "unit_steps": unit_steps},
                })
                break  # One finding is enough

        return findings

    async def _run_audit(self, spec: dict[str, Any]) -> dict[str, Any]:
        """Handle an explicit audit request from another agent."""
        script_hash = spec.get("script_hash")
        if not self.mission_gate(f"audit: {script_hash or 'unknown'}"):
            return {"status": "rejected", "reason": "mission_violation"}

        if not script_hash:
            return {
                "status": "error",
                "error": "No script_hash provided in audit request",
                "audit_id": f"audit_{self.audits_completed + 1}",
            }

        chain_ok = await self._ensure_blockfrost()
        if not chain_ok:
            return {
                "status": "error",
                "error": "Blockfrost not configured — cannot perform on-chain audit",
                "audit_id": f"audit_{self.audits_completed + 1}",
            }

        # Check cache first
        if script_hash in self._audited_scripts:
            cached = self._audited_scripts[script_hash]
            return {
                "status": "completed",
                "source": "cache",
                "findings": cached["findings"],
                "finding_count": len(cached["findings"]),
                "severity": self._max_severity(cached["findings"]),
                "audit_id": f"audit_{self.audits_completed}",
                "audited_at": cached["audited_at"],
            }

        # Run fresh audit
        findings = await self._audit_single_script(script_hash)
        self.audits_completed += 1

        self._audited_scripts[script_hash] = {
            "hash": script_hash,
            "audited_at": datetime.now(timezone.utc).isoformat(),
            "findings": findings,
        }
        audit_record = {
            "script_hash": script_hash,
            "findings": findings,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "requested_by": spec.get("_sender", "unknown"),
        }
        self._audit_history.append(audit_record)
        if len(self._audit_history) > MAX_AUDIT_HISTORY:
            self._audit_history = self._audit_history[-MAX_AUDIT_HISTORY:]

        if findings:
            self.vulnerabilities_found += len(findings)

        return {
            "status": "completed",
            "source": "fresh",
            "findings": findings,
            "finding_count": len(findings),
            "severity": self._max_severity(findings),
            "audit_id": f"audit_{self.audits_completed}",
        }

    @staticmethod
    def _max_severity(findings: list[dict[str, Any]]) -> str:
        if not findings:
            return "none"
        max_rank = max(f.get("severity_rank", 0) for f in findings)
        return {0: "info", 1: "low", 2: "medium", 3: "high", 4: "critical"}.get(max_rank, "unknown")

    # ------------------------------------------------------------------
    # Threat level management
    # ------------------------------------------------------------------

    def _register_anomaly(
        self,
        anomaly_type: str,
        severity: str,
        detail: str,
        data: dict[str, Any] | None = None,
    ) -> None:
        """Record an anomaly and potentially escalate threat level."""
        anomaly = {
            "id": uuid.uuid4().hex[:8],
            "type": anomaly_type,
            "severity": severity,
            "detail": detail,
            "data": data or {},
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "monotonic": time.monotonic(),
        }
        self._active_anomalies.append(anomaly)
        self._last_escalation_time = time.monotonic()

        self.log.warning("sentinel.anomaly_detected",
                         anomaly_type=anomaly_type,
                         severity=severity,
                         detail=detail)

        self.memory.remember("decisions", {
            "type": "anomaly_detected",
            "anomaly": anomaly,
        })

    async def _evaluate_threat_level(self) -> None:
        """Compute threat level from active anomalies and update accordingly."""
        # Expire old anomalies (>15 minutes without reinforcement)
        now = time.monotonic()
        self._active_anomalies = [
            a for a in self._active_anomalies
            if now - a["monotonic"] < 900  # 15 minutes
        ]

        anomaly_count = len(self._active_anomalies)
        high_severity_count = sum(
            1 for a in self._active_anomalies
            if a["severity"] in ("high", "critical")
        )
        medium_count = sum(
            1 for a in self._active_anomalies
            if a["severity"] == "medium"
        )

        # Determine appropriate level
        if high_severity_count >= 2 or anomaly_count >= 5:
            new_level = ThreatLevel.RED
        elif high_severity_count >= 1 or (medium_count >= 2 and anomaly_count >= 3):
            new_level = ThreatLevel.ORANGE
        elif anomaly_count >= 1:
            new_level = ThreatLevel.YELLOW
        else:
            new_level = ThreatLevel.GREEN

        old_level = self.threat_level

        # Only escalate, never skip-level de-escalate (that's handled by cooldown)
        if new_level.severity_rank > old_level.severity_rank:
            self.threat_level = new_level
            self.log.warning("sentinel.threat_escalated",
                             old=old_level.value, new=new_level.value,
                             anomaly_count=anomaly_count)

            # Broadcast on ORANGE or RED
            if new_level in (ThreatLevel.ORANGE, ThreatLevel.RED):
                await self.broadcast("alert", {
                    "type": "threat_level_change",
                    "from": old_level.value,
                    "to": new_level.value,
                    "anomaly_count": anomaly_count,
                    "anomalies": [
                        {"type": a["type"], "severity": a["severity"], "detail": a["detail"]}
                        for a in self._active_anomalies[-5:]
                    ],
                }, priority=3)

            # On RED: create incident and notify HumanCouncil
            if new_level == ThreatLevel.RED:
                incident_id = self._create_incident(
                    title="RED threat level — active security incident",
                    severity="critical",
                    affected_systems=[a["type"] for a in self._active_anomalies],
                    detail=f"{anomaly_count} active anomalies, {high_severity_count} high-severity",
                )
                await self.send("HumanCouncil", "alert", {
                    "type": "red_incident",
                    "incident_id": incident_id,
                    "threat_level": "red",
                    "anomaly_count": anomaly_count,
                    "summary": [
                        {"type": a["type"], "severity": a["severity"], "detail": a["detail"]}
                        for a in self._active_anomalies
                    ],
                }, priority=3)

    async def _check_deescalation(self) -> None:
        """Step threat level down if anomalies have cleared and cooldown elapsed."""
        if self.threat_level == ThreatLevel.GREEN:
            return

        now = time.monotonic()
        time_since_last = now - self._last_escalation_time

        if time_since_last < DEESCALATION_COOLDOWN_S:
            return

        if not self._active_anomalies:
            old = self.threat_level
            # Step down one level at a time
            if self.threat_level == ThreatLevel.RED:
                self.threat_level = ThreatLevel.ORANGE
            elif self.threat_level == ThreatLevel.ORANGE:
                self.threat_level = ThreatLevel.YELLOW
            elif self.threat_level == ThreatLevel.YELLOW:
                self.threat_level = ThreatLevel.GREEN

            self.log.info("sentinel.threat_deescalated",
                          old=old.value, new=self.threat_level.value)
            self._last_escalation_time = now  # reset cooldown for next step

    # ------------------------------------------------------------------
    # Incident lifecycle
    # ------------------------------------------------------------------

    def _create_incident(
        self,
        title: str,
        severity: str,
        affected_systems: list[str],
        detail: str,
    ) -> str:
        """Create a new incident and return its ID."""
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        now_iso = datetime.now(timezone.utc).isoformat()

        incident = {
            "id": incident_id,
            "title": title,
            "severity": severity,
            "phase": IncidentPhase.DETECTED,
            "affected_systems": list(set(affected_systems)),
            "detail": detail,
            "created_at": now_iso,
            "updated_at": now_iso,
            "timeline": [
                {"phase": IncidentPhase.DETECTED.value, "at": now_iso, "note": "Auto-created by SentinelGuard"},
            ],
            "resolution": None,
        }
        self._incidents[incident_id] = incident

        # Prune old resolved incidents
        if len(self._incidents) > MAX_INCIDENT_HISTORY:
            resolved = [
                iid for iid, inc in self._incidents.items()
                if inc["phase"] == IncidentPhase.RESOLVED
            ]
            for iid in resolved[:len(self._incidents) - MAX_INCIDENT_HISTORY]:
                del self._incidents[iid]

        self.log.warning("sentinel.incident_created",
                         incident_id=incident_id, severity=severity, title=title)

        self.memory.remember("decisions", {
            "type": "incident_created",
            "incident_id": incident_id,
            "severity": severity,
            "title": title,
        })

        return incident_id

    def _advance_incident(self, incident_id: str, new_phase: IncidentPhase, note: str = "") -> None:
        """Move an incident to the next phase."""
        incident = self._incidents.get(incident_id)
        if not incident:
            return

        now_iso = datetime.now(timezone.utc).isoformat()
        incident["phase"] = new_phase
        incident["updated_at"] = now_iso
        incident["timeline"].append({
            "phase": new_phase.value,
            "at": now_iso,
            "note": note,
        })

        if new_phase == IncidentPhase.RESOLVED:
            incident["resolution"] = note

        self.log.info("sentinel.incident_advanced",
                      incident_id=incident_id, phase=new_phase.value)

    async def _advance_incidents(self) -> None:
        """Auto-advance incidents based on current state."""
        for iid, incident in self._incidents.items():
            phase = incident["phase"]

            if phase == IncidentPhase.DETECTED:
                # Auto-move to investigating
                self._advance_incident(iid, IncidentPhase.INVESTIGATING,
                                       "Auto-investigating — analyzing anomalies")

            elif phase == IncidentPhase.INVESTIGATING:
                # Check if the anomalies that caused this incident are still active
                affected = set(incident["affected_systems"])
                still_active = any(
                    a["type"] in affected for a in self._active_anomalies
                )
                if not still_active:
                    self._advance_incident(iid, IncidentPhase.CONTAINED,
                                           "Triggering anomalies no longer active")

            elif phase == IncidentPhase.CONTAINED:
                # If threat level is back to green, resolve
                if self.threat_level == ThreatLevel.GREEN:
                    self._advance_incident(iid, IncidentPhase.RESOLVED,
                                           "Threat level returned to GREEN — resolved")

    # ------------------------------------------------------------------
    # Alert handling
    # ------------------------------------------------------------------

    async def _handle_security_alert(self, msg: Message) -> None:
        """Evaluate incoming security alert from another agent."""
        severity = msg.payload.get("severity", "medium")
        alert_type = msg.payload.get("type", "unknown")
        detail = msg.payload.get("detail", str(msg.payload))
        if not self.mission_gate(f"security_response: {alert_type} severity={severity}"):
            return

        self.log.warning("sentinel.alert_received",
                         sender=msg.sender, severity=severity, alert_type=alert_type)

        # Map incoming severity to our anomaly system
        self._register_anomaly(
            anomaly_type=f"external_alert_{alert_type}",
            severity=severity,
            detail=f"Alert from {msg.sender}: {detail}",
            data={"source_agent": msg.sender, "original_payload": msg.payload},
        )

        # Acknowledge
        await self.send(msg.sender, "response", {
            "type": "alert_ack",
            "received": True,
            "current_threat_level": self.threat_level.value,
        })

    async def _handle_upstream_alert(self, msg: Message) -> None:
        """Handle security advisory from RepoWatcher."""
        advisory = msg.payload
        severity = advisory.get("severity", "medium")
        repo = advisory.get("repo", "unknown")
        title = advisory.get("title", "Security advisory")

        self.log.warning("sentinel.upstream_advisory",
                         repo=repo, severity=severity, title=title)

        # Evaluate impact — security advisories from upstream repos are always significant
        if severity in ("high", "critical"):
            effective_severity = "high"
        elif severity == "medium":
            effective_severity = "medium"
        else:
            effective_severity = "low"

        self._register_anomaly(
            anomaly_type="upstream_security_advisory",
            severity=effective_severity,
            detail=f"Security advisory from {repo}: {title}",
            data={
                "repo": repo,
                "advisory": advisory,
                "source": "RepoWatcher",
            },
        )

        # If high/critical, create an incident
        if effective_severity == "high":
            self._create_incident(
                title=f"Upstream security advisory: {title}",
                severity=effective_severity,
                affected_systems=[repo, "upstream_dependency"],
                detail=f"RepoWatcher flagged advisory from {repo}",
            )

        # Broadcast to all agents so they can check their own dependencies
        await self.broadcast("alert", {
            "type": "upstream_security_advisory",
            "source": "SentinelGuard",
            "repo": repo,
            "severity": effective_severity,
            "title": title,
            "action_required": effective_severity in ("high", "critical"),
        }, priority=2 if effective_severity == "medium" else 3)

    # ------------------------------------------------------------------
    # Peer agent health monitoring
    # ------------------------------------------------------------------

    async def _peer_health_check(self) -> None:
        """Periodically send health checks to peer agents and track responses."""
        self._health_check_cycle += 1

        # Only run health checks every 6th work cycle (~30s at 5s interval)
        if self._health_check_cycle % 6 != 0:
            # But still check for timed-out agents every cycle
            self._check_health_timeouts()
            return

        # Send health_check to all known peers
        for peer_name in list(self._peers.keys()):
            check_time = time.monotonic()
            self._peer_health.setdefault(peer_name, {
                "last_check": 0,
                "last_response": 0,
                "status": "unknown",
                "response_time_ms": None,
            })
            self._peer_health[peer_name]["last_check"] = check_time
            self._peer_health[peer_name]["status"] = "checking"

            await self.send(peer_name, "request", {
                "type": "health_check",
                "check_time": check_time,
            })

    def _check_health_timeouts(self) -> None:
        """Flag agents that haven't responded within timeout."""
        now = time.monotonic()
        for peer_name, health in self._peer_health.items():
            if health["status"] == "checking":
                elapsed = now - health["last_check"]
                if elapsed > AGENT_HEALTH_TIMEOUT_S:
                    health["status"] = "unresponsive"
                    self.log.warning("sentinel.agent_unresponsive",
                                     agent=peer_name,
                                     timeout_s=elapsed)

    def _record_health_response(self, msg: Message) -> None:
        """Record a health check response from a peer agent."""
        peer_name = msg.sender
        now = time.monotonic()

        if peer_name not in self._peer_health:
            self._peer_health[peer_name] = {
                "last_check": now,
                "last_response": now,
                "status": "healthy",
                "response_time_ms": None,
            }
            return

        health = self._peer_health[peer_name]
        response_time = (now - health["last_check"]) * 1000  # to ms
        health["last_response"] = now
        health["status"] = "healthy"
        health["response_time_ms"] = round(response_time, 1)

        self.log.debug("sentinel.health_response",
                       agent=peer_name,
                       response_time_ms=health["response_time_ms"])

    # ------------------------------------------------------------------
    # Reporting (human council)
    # ------------------------------------------------------------------

    def report(self) -> dict[str, Any]:
        """Generate comprehensive security status report."""
        base = super().report()

        open_incidents = {
            iid: {
                "title": inc["title"],
                "severity": inc["severity"],
                "phase": inc["phase"].value if isinstance(inc["phase"], IncidentPhase) else inc["phase"],
                "created_at": inc["created_at"],
            }
            for iid, inc in self._incidents.items()
            if inc["phase"] != IncidentPhase.RESOLVED
        }

        peer_summary = {
            name: {"status": h["status"], "response_time_ms": h["response_time_ms"]}
            for name, h in self._peer_health.items()
        }

        base.update({
            "threat_level": self.threat_level.value,
            "active_anomalies": len(self._active_anomalies),
            "anomaly_details": [
                {"type": a["type"], "severity": a["severity"], "detail": a["detail"]}
                for a in self._active_anomalies[-10:]
            ],
            "audits_completed": self.audits_completed,
            "scripts_tracked": len(self._audited_scripts),
            "vulnerabilities_found": self.vulnerabilities_found,
            "open_incidents": open_incidents,
            "peer_health": peer_summary,
            "bug_bounty_pool": self.bug_bounty_pool,
            "blockfrost_available": self._bf_available,
        })
        return base
