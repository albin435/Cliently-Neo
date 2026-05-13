"""
Neo v2 — OpenClaw Runtime Integration Engine

OpenClaw is the execution runtime layer between Neo (supervisor) and
Antigravity (implementation). It provides:
- Shell execution
- Filesystem access
- Automation / tooling
- Sandboxed runtime environment

OpenClaw is MANUALLY installed and managed by Albin.
Neo connects to it, validates health, dispatches tasks, and monitors execution.
Neo NEVER installs or configures OpenClaw automatically.
"""

import os
import json
import asyncio
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field

logger = logging.getLogger("neo.openclaw")

# --- Configuration ---

OPENCLAW_HOST = os.environ.get("OPENCLAW_HOST", "http://localhost:9090")
OPENCLAW_PORT = os.environ.get("OPENCLAW_PORT", "9090")

# Ensure host starts with http and includes the port if not already present
if not OPENCLAW_HOST.startswith("http"):
    OPENCLAW_HOST = f"http://{OPENCLAW_HOST}"
if ":" not in OPENCLAW_HOST.replace("://", ""):
    OPENCLAW_HOST = f"{OPENCLAW_HOST}:{OPENCLAW_PORT}"
OPENCLAW_TIMEOUT = int(os.environ.get("OPENCLAW_TIMEOUT", "30"))


class RuntimeStatus(str, Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    CHECKING = "checking"
    ERROR = "error"


class TaskDispatchStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class RuntimeState:
    """Current state of the OpenClaw runtime."""
    status: RuntimeStatus = RuntimeStatus.DISCONNECTED
    host: str = OPENCLAW_HOST
    last_check: Optional[datetime] = None
    version: Optional[str] = None
    sandbox_active: bool = False
    active_tasks: int = 0
    error: Optional[str] = None


@dataclass
class DispatchResult:
    """Result of dispatching a task to OpenClaw."""
    success: bool
    task_ref: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None
    duration_ms: int = 0


# --- OpenClaw Client ---

class OpenClawClient:
    """
    Client for communicating with the OpenClaw runtime.
    Resilient — Neo works fine without OpenClaw connected.
    """

    def __init__(self, host: str = OPENCLAW_HOST):
        self.host = host
        self.state = RuntimeState(host=host)
        self._http = None

    async def _get_http(self):
        """Lazy-init httpx client."""
        if self._http is None:
            try:
                import httpx
                self._http = httpx.AsyncClient(
                    base_url=self.host,
                    timeout=OPENCLAW_TIMEOUT,
                )
            except ImportError:
                logger.warning("httpx not installed — OpenClaw HTTP disabled")
                return None
        return self._http

    async def check_health(self) -> RuntimeState:
        """
        Check if OpenClaw runtime is reachable and healthy.
        Returns current runtime state.
        """
        self.state.status = RuntimeStatus.CHECKING
        self.state.last_check = datetime.now(timezone.utc)

        http = await self._get_http()
        if not http:
            self.state.status = RuntimeStatus.DISCONNECTED
            self.state.error = "HTTP client unavailable"
            return self.state

        try:
            resp = await http.get("/health")
            if resp.status_code == 200:
                data = resp.json()
                self.state.status = RuntimeStatus.CONNECTED
                self.state.version = data.get("version", "unknown")
                self.state.sandbox_active = data.get("sandbox_active", False)
                self.state.active_tasks = data.get("active_tasks", 0)
                self.state.error = None
                logger.info(f"OpenClaw connected: v{self.state.version}")
            else:
                self.state.status = RuntimeStatus.ERROR
                self.state.error = f"HTTP {resp.status_code}"
        except Exception as e:
            self.state.status = RuntimeStatus.DISCONNECTED
            self.state.error = str(e)
            logger.debug(f"OpenClaw offline: {e}")

        return self.state

    async def dispatch_task(
        self,
        task_id: str,
        plan: str,
        context: str,
        prompt: str,
        agent_roles: list[str],
    ) -> DispatchResult:
        """
        Dispatch an execution task to OpenClaw runtime.
        OpenClaw will route to Antigravity for implementation.
        """
        http = await self._get_http()
        if not http or self.state.status != RuntimeStatus.CONNECTED:
            return DispatchResult(
                success=False,
                error="OpenClaw runtime not connected",
            )

        payload = {
            "task_id": task_id,
            "plan": plan,
            "context": context[:8000],
            "prompt": prompt,
            "agent_roles": agent_roles,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        try:
            resp = await http.post("/tasks/dispatch", json=payload)
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                return DispatchResult(
                    success=True,
                    task_ref=data.get("task_ref", task_id),
                    output=data.get("output"),
                )
            else:
                return DispatchResult(
                    success=False,
                    error=f"Dispatch failed: HTTP {resp.status_code}",
                )
        except Exception as e:
            return DispatchResult(success=False, error=str(e))

    async def get_task_status(self, task_ref: str) -> dict:
        """Poll task execution status from OpenClaw."""
        http = await self._get_http()
        if not http:
            return {"status": "unknown", "error": "HTTP unavailable"}

        try:
            resp = await http.get(f"/tasks/{task_ref}/status")
            if resp.status_code == 200:
                return resp.json()
            return {"status": "unknown", "error": f"HTTP {resp.status_code}"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def get_task_result(self, task_ref: str) -> Optional[str]:
        """Fetch completed task output from OpenClaw."""
        http = await self._get_http()
        if not http:
            return None

        try:
            resp = await http.get(f"/tasks/{task_ref}/result")
            if resp.status_code == 200:
                data = resp.json()
                return data.get("output", "")
            return None
        except Exception:
            return None

    async def execute_shell(self, command: str, cwd: str = None) -> DispatchResult:
        """
        Execute a shell command through OpenClaw's sandboxed terminal.
        This is gated by Neo's approval flow — never called directly.
        """
        http = await self._get_http()
        if not http or self.state.status != RuntimeStatus.CONNECTED:
            return DispatchResult(success=False, error="Runtime not connected")

        try:
            resp = await http.post("/shell/execute", json={
                "command": command,
                "cwd": cwd,
            })
            if resp.status_code == 200:
                data = resp.json()
                return DispatchResult(
                    success=True,
                    output=data.get("stdout", ""),
                    duration_ms=data.get("duration_ms", 0),
                )
            return DispatchResult(success=False, error=f"HTTP {resp.status_code}")
        except Exception as e:
            return DispatchResult(success=False, error=str(e))

    async def read_file(self, path: str) -> Optional[str]:
        """Read a file through OpenClaw's filesystem bridge."""
        http = await self._get_http()
        if not http or self.state.status != RuntimeStatus.CONNECTED:
            return None

        try:
            resp = await http.get("/fs/read", params={"path": path})
            if resp.status_code == 200:
                return resp.json().get("content")
            return None
        except Exception:
            return None

    def get_status_dict(self) -> dict:
        """Return serializable runtime status for API responses."""
        return {
            "status": self.state.status.value,
            "host": self.state.host,
            "last_check": self.state.last_check.isoformat() if self.state.last_check else None,
            "version": self.state.version,
            "sandbox_active": self.state.sandbox_active,
            "active_tasks": self.state.active_tasks,
            "error": self.state.error,
        }

    async def close(self):
        """Clean up HTTP client."""
        if self._http:
            await self._http.aclose()
            self._http = None


# --- Singleton ---

_client: Optional[OpenClawClient] = None


def get_openclaw() -> OpenClawClient:
    """Get the global OpenClaw client instance."""
    global _client
    if _client is None:
        _client = OpenClawClient()
    return _client
