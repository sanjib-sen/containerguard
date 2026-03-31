from __future__ import annotations

import logging
from datetime import datetime, timezone
from types import TracebackType
from uuid import UUID

import socket

import httpx

from ..collectors.filesystem import FilesystemEvent
from ..collectors.network import NetworkConnection
from ..collectors.ports import OpenPort
from ..collectors.processes import ProcessInfo
from ..collectors.resources import ResourceSnapshot
from ..config import Settings


def _get_local_ip() -> str | None:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return None

logger = logging.getLogger(__name__)


class AgentClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> AgentClient:
        self._client = httpx.AsyncClient(
            base_url=self._settings.server_url,
            timeout=httpx.Timeout(self._settings.http_timeout_seconds),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError("AgentClient must be used as an async context manager")
        return self._client

    async def register(self) -> UUID:
        ip = _get_local_ip()
        r = await self._http.post(
            "/api/v1/agents/register",
            json={
                "container_id": self._settings.container_id,
                "hostname": self._settings.hostname,
                "image": self._settings.image,
                "ip": ip,
            },
        )
        r.raise_for_status()
        return UUID(r.json()["id"])

    async def heartbeat(self, agent_id: UUID) -> None:
        r = await self._http.post(
            "/api/v1/agents/heartbeat",
            json={"agent_id": str(agent_id)},
        )
        r.raise_for_status()

    async def push_telemetry(
        self,
        agent_id: UUID,
        *,
        resources: ResourceSnapshot | None = None,
        network: list[NetworkConnection] | None = None,
        ports: list[OpenPort] | None = None,
        filesystem: list[FilesystemEvent] | None = None,
        processes: list[ProcessInfo] | None = None,
    ) -> None:
        now = datetime.now(timezone.utc).isoformat()

        network_payload = None
        if network:
            network_payload = {
                "connections": [
                    {
                        "direction": c.direction,
                        "src_ip": c.src_ip,
                        "dst_ip": c.dst_ip,
                        "dst_port": c.dst_port,
                        "protocol": c.protocol,
                        "bytes": c.bytes_transferred,
                    }
                    for c in network
                ],
                "dns_queries": [],
            }

        fs_payload = None
        if filesystem:
            fs_payload = {
                "events": [
                    {
                        "type": e.type,
                        "path": e.path,
                        "pid": e.pid,
                        "process": e.process,
                        "timestamp": e.timestamp.isoformat(),
                    }
                    for e in filesystem
                ],
            }

        resources_payload = None
        if resources:
            resources_payload = {
                "cpu_percent": resources.cpu_percent,
                "memory_mb": resources.memory_mb,
                "memory_limit_mb": resources.memory_limit_mb,
                "net_bytes_sent": resources.net_bytes_sent,
                "net_bytes_recv": resources.net_bytes_recv,
                "disk_read_bytes": resources.disk_read_bytes,
                "disk_write_bytes": resources.disk_write_bytes,
            }

        ports_payload = [
            {
                "port": p.port,
                "protocol": p.protocol,
                "pid": p.pid,
                "process": p.process,
            }
            for p in (ports or [])
        ]

        processes_payload = [
            {
                "pid": p.pid,
                "command": p.command,
                "user": p.user,
                "started": p.started.isoformat(),
            }
            for p in (processes or [])
        ]

        r = await self._http.post(
            "/api/v1/telemetry",
            json={
                "agent_id": str(agent_id),
                "timestamp": now,
                "resources": resources_payload,
                "network": network_payload,
                "ports": ports_payload,
                "filesystem": fs_payload,
                "processes": processes_payload,
            },
        )
        r.raise_for_status()
