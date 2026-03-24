from __future__ import annotations

from datetime import datetime
from ipaddress import IPv4Address, IPv6Address
from uuid import UUID

from pydantic import BaseModel, ConfigDict


IPAddress = IPv4Address | IPv6Address


class AgentRegisterRequest(BaseModel):
    container_id: str
    hostname: str
    image: str
    ip: IPAddress | None = None


class AgentHeartbeatRequest(BaseModel):
    agent_id: UUID


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    container_id: str
    hostname: str
    image: str
    ip: IPAddress | None
    status: str
    registered_at: datetime
    last_heartbeat: datetime


class AgentHeartbeatResponse(BaseModel):
    agent_id: UUID
    status: str
    last_heartbeat: datetime
