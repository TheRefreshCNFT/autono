"""ThrottleManager — watches SYSTEM resources, not the program's consumption.

It monitors the environment where the program is installed. If the system
hits 85% CPU/memory, ThrottleManager blocks all new agent spawning until
existing agents finish their work. This keeps it usable on ALL systems.

All managers and agents MUST ask ThrottleManager for permission before
spawning sub-agents. No exceptions.
"""

from __future__ import annotations

import asyncio
import os
from collections import deque
from datetime import datetime, timezone
from typing import Any

from autono.core.agent_base import AgentCapability, AgentStatus, AutonomousAgent, Message

# Try to import psutil for real system monitoring, fall back to /proc
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False


class SpawnRequest:
    """A request from a manager/agent to spawn a sub-agent."""
    def __init__(self, requester: str, agent_type: str, priority: int = 1,
                 department: str = "general") -> None:
        self.requester = requester
        self.agent_type = agent_type
        self.priority = priority          # 1=normal, 2=high, 3=critical
        self.department = department       # which manager's domain
        self.approved = False
        self.denied_reason = ""
        self.requested_at = datetime.now(timezone.utc).isoformat()


class ThrottleManager(AutonomousAgent):
    """System resource gatekeeper.

    Watches CPU, memory, and disk usage of the HOST SYSTEM.
    Controls agent spawning to prevent resource exhaustion.
    Maintains a priority queue for spawn requests.
    """

    # Hard boundaries — inner freedom, outer limits
    CPU_THRESHOLD = 85.0        # percent
    MEMORY_THRESHOLD = 85.0     # percent
    DISK_THRESHOLD = 90.0       # percent
    MAX_ACTIVE_SPAWNS = 20      # absolute ceiling on concurrent sub-agents

    def __init__(self) -> None:
        super().__init__(
            name="ThrottleManager",
            role="System resource gatekeeper — controls agent spawning based on host capacity",
            capabilities=[AgentCapability.AUDIT],
        )
        self._active_spawns: int = 0
        self._spawn_history: deque[dict] = deque(maxlen=1000)
        self._denied_history: deque[dict] = deque(maxlen=500)
        self._system_state: dict[str, float] = {}
        self._throttled = False
        self._priority_queue: list[SpawnRequest] = []

    @property
    def work_interval(self) -> float:
        return 5.0  # check resources frequently

    async def do_work(self) -> None:
        """Monitor system resources and process spawn queue."""
        self._system_state = self._read_system_resources()

        # Check thresholds
        cpu = self._system_state.get("cpu_percent", 0)
        mem = self._system_state.get("memory_percent", 0)
        disk = self._system_state.get("disk_percent", 0)

        was_throttled = self._throttled
        self._throttled = (
            cpu > self.CPU_THRESHOLD or
            mem > self.MEMORY_THRESHOLD or
            disk > self.DISK_THRESHOLD
        )

        if self._throttled and not was_throttled:
            self.log.warning("throttle.engaged",
                             cpu=cpu, mem=mem, disk=disk)
            await self.broadcast("alert", {
                "type": "throttle_engaged",
                "cpu": cpu, "memory": mem, "disk": disk,
                "message": "System resources high. No new spawns until recovery.",
            }, priority=3)
        elif not self._throttled and was_throttled:
            self.log.info("throttle.released", cpu=cpu, mem=mem)
            await self.broadcast("alert", {
                "type": "throttle_released",
                "message": "System resources recovered. Spawning allowed.",
            })

        # Process priority queue if not throttled
        if not self._throttled:
            await self._process_spawn_queue()

        self.memory.remember("decisions", {
            "type": "resource_check",
            "system": self._system_state,
            "throttled": self._throttled,
            "active_spawns": self._active_spawns,
            "queue_size": len(self._priority_queue),
        })

    async def handle_message(self, msg: Message) -> None:
        if msg.kind == "request" and msg.payload.get("type") == "spawn_request":
            request = SpawnRequest(
                requester=msg.sender,
                agent_type=msg.payload.get("agent_type", "unknown"),
                priority=msg.payload.get("priority", 1),
                department=msg.payload.get("department", "general"),
            )
            result = self.evaluate_spawn(request)
            await self.send(msg.sender, "response", {
                "type": "spawn_response",
                "approved": result.approved,
                "denied_reason": result.denied_reason,
                "system_state": self._system_state,
            })

        elif msg.kind == "report" and msg.payload.get("type") == "spawn_complete":
            self._active_spawns = max(0, self._active_spawns - 1)
            self.log.debug("throttle.spawn_complete",
                           requester=msg.sender,
                           active=self._active_spawns)

    async def learn(self) -> None:
        self.memory.remember("tech_updates", {
            "area": "resource_management",
            "topics": [
                "adaptive_throttle_thresholds",
                "predictive_resource_usage",
                "spawn_scheduling_optimization",
            ],
        })

    # -- Spawn control (synchronous check for direct calls) ---------------

    def evaluate_spawn(self, request: SpawnRequest) -> SpawnRequest:
        """Evaluate whether a spawn should be approved.

        Priority 3 (critical) can bypass throttle if under MAX_ACTIVE_SPAWNS.
        This prevents main agent tasks from being starved by background work.
        """
        # Critical requests get priority pass (unless at absolute ceiling)
        if request.priority >= 3 and self._active_spawns < self.MAX_ACTIVE_SPAWNS:
            request.approved = True
            self._active_spawns += 1
            self._spawn_history.append({
                "requester": request.requester,
                "type": request.agent_type,
                "priority": request.priority,
                "time": request.requested_at,
            })
            self.log.info("throttle.critical_spawn_approved",
                          requester=request.requester)
            return request

        # Throttled — queue it
        if self._throttled:
            request.denied_reason = "system_throttled"
            self._priority_queue.append(request)
            self._denied_history.append({
                "requester": request.requester,
                "reason": "throttled",
                "system": self._system_state.copy(),
            })
            self.log.info("throttle.spawn_queued",
                          requester=request.requester,
                          queue_pos=len(self._priority_queue))
            return request

        # Max spawns reached
        if self._active_spawns >= self.MAX_ACTIVE_SPAWNS:
            request.denied_reason = "max_spawns_reached"
            self._priority_queue.append(request)
            return request

        # Approved
        request.approved = True
        self._active_spawns += 1
        self._spawn_history.append({
            "requester": request.requester,
            "type": request.agent_type,
            "priority": request.priority,
            "time": request.requested_at,
        })
        return request

    def notify_spawn_complete(self) -> None:
        """Called when a spawned agent finishes its work."""
        self._active_spawns = max(0, self._active_spawns - 1)

    async def _process_spawn_queue(self) -> None:
        """Process queued spawn requests by priority."""
        if not self._priority_queue:
            return

        # Sort by priority (highest first)
        self._priority_queue.sort(key=lambda r: -r.priority)

        processed = []
        for request in self._priority_queue:
            if self._active_spawns >= self.MAX_ACTIVE_SPAWNS:
                break
            if self._throttled:
                break
            request.approved = True
            self._active_spawns += 1
            processed.append(request)
            self.log.info("throttle.queued_spawn_approved",
                          requester=request.requester)

        for req in processed:
            self._priority_queue.remove(req)

    # -- System resource reading ------------------------------------------

    def _read_system_resources(self) -> dict[str, float]:
        """Read actual host system resources."""
        if HAS_PSUTIL:
            return {
                "cpu_percent": psutil.cpu_percent(interval=0.1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage("/").percent,
                "cpu_count": psutil.cpu_count() or 1,
                "memory_total_gb": round(
                    psutil.virtual_memory().total / (1024 ** 3), 2
                ),
            }

        # Fallback: read from /proc (Linux)
        result: dict[str, float] = {}
        try:
            with open("/proc/loadavg") as f:
                load = float(f.read().split()[0])
                cpu_count = os.cpu_count() or 1
                result["cpu_percent"] = min(100.0, (load / cpu_count) * 100)
                result["cpu_count"] = float(cpu_count)
        except (FileNotFoundError, ValueError):
            result["cpu_percent"] = 0.0

        try:
            with open("/proc/meminfo") as f:
                lines = f.readlines()
                mem_total = int(lines[0].split()[1])
                mem_available = int(lines[2].split()[1])
                result["memory_percent"] = (
                    (1 - mem_available / mem_total) * 100 if mem_total else 0
                )
                result["memory_total_gb"] = round(mem_total / (1024 ** 2), 2)
        except (FileNotFoundError, ValueError, IndexError):
            result["memory_percent"] = 0.0

        try:
            stat = os.statvfs("/")
            total = stat.f_blocks * stat.f_frsize
            free = stat.f_bfree * stat.f_frsize
            result["disk_percent"] = ((total - free) / total * 100) if total else 0
        except OSError:
            result["disk_percent"] = 0.0

        return result

    @property
    def is_throttled(self) -> bool:
        return self._throttled

    @property
    def active_spawns(self) -> int:
        return self._active_spawns

    def report(self) -> dict[str, Any]:
        base = super().report()
        base.update({
            "throttled": self._throttled,
            "system_state": self._system_state,
            "active_spawns": self._active_spawns,
            "queue_size": len(self._priority_queue),
            "total_spawns_approved": len(self._spawn_history),
            "total_spawns_denied": len(self._denied_history),
        })
        return base
