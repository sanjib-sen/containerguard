from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from ..db import DataAccessLayer, get_dal
from ..metrics.exporter import record_telemetry_ingest, set_latest_resource_metrics
from ..realtime import broker
from ..schemas import TelemetryIngestRequest, TelemetryIngestResponse

router = APIRouter(
    prefix="/telemetry",
    tags=["telemetry"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=TelemetryIngestResponse, status_code=status.HTTP_201_CREATED)
async def postTelemetry(payload: TelemetryIngestRequest, background_tasks: BackgroundTasks, dal: DataAccessLayer = Depends(get_dal)):
    agent = await dal.agents.get_by_id(payload.agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    write_result = await dal.telemetry.ingest(agent=agent, payload=payload)
    record_telemetry_ingest(
        stored_network_connections=write_result.stored_network_connections,
        stored_filesystem_events=write_result.stored_filesystem_events,
        stored_processes=write_result.stored_processes,
        stored_ports=write_result.stored_ports,
        stored_resources=write_result.resource_snapshot is not None,
    )
    if payload.resources is not None:
        set_latest_resource_metrics(
            agent_id=str(agent.id),
            container_id=agent.container_id,
            hostname=agent.hostname,
            cpu_percent=payload.resources.cpu_percent,
            memory_mb=payload.resources.memory_mb,
            memory_limit_mb=payload.resources.memory_limit_mb,
            net_bytes_sent=payload.resources.net_bytes_sent,
            net_bytes_recv=payload.resources.net_bytes_recv,
            disk_read_bytes=payload.resources.disk_read_bytes,
            disk_write_bytes=payload.resources.disk_write_bytes,
        )

    background_tasks.add_task(
        broker.publish_dashboard,
        {
            "type": "telemetry",
            "agent_id": str(agent.id),
            "container_id": agent.container_id,
            "hostname": agent.hostname,
            "timestamp": payload.timestamp.isoformat(),
            "resources": payload.resources.model_dump() if payload.resources else None,
            "network_connections": write_result.stored_network_connections,
            "filesystem_events": write_result.stored_filesystem_events,
            "processes": write_result.stored_processes,
            "ports": write_result.stored_ports,
        },
    )

    return TelemetryIngestResponse(
        event_id=write_result.event.id,
        agent_id=write_result.event.agent_id,
        ingested_at=write_result.event.created_at,
        resource_snapshot_id=(
            write_result.resource_snapshot.id
            if write_result.resource_snapshot is not None
            else None
        ),
        stored_resources=write_result.resource_snapshot is not None,
        stored_network_connections=write_result.stored_network_connections,
        stored_filesystem_events=write_result.stored_filesystem_events,
        stored_processes=write_result.stored_processes,
        stored_ports=write_result.stored_ports,
        raw_payload=write_result.event.payload_json,
    )

# ── Global queries ──

@router.get("/latest-resources")
async def getLatestResources(dal: DataAccessLayer = Depends(get_dal)):
    """Latest resource snapshot per agent (for overview)."""
    return await dal.telemetry.getLatestResourcePerAgent()

@router.get("/network")
async def getNetwork(dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=24, ge=1, le=168), limit: int = Query(default=500, ge=1, le=5000)):
    agent_ids = await dal.agents.list_online_agents()
    if not agent_ids:
        return []
    return await dal.telemetry.getNetworkEvents(agent_ids, hours=hours, limit=limit)

@router.get("/filesystem")
async def getFilesystem(dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=24, ge=1, le=168), limit: int = Query(default=500, ge=1, le=5000)):
    agent_ids = await dal.agents.list_online_agents()
    if not agent_ids:
        return []
    return await dal.telemetry.getFilesystemEvents(agent_ids, hours=hours, limit=limit)

@router.get("/resources")
async def getResources(dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=24, ge=1, le=168), limit: int = Query(default=500, ge=1, le=5000)):
    agent_ids = await dal.agents.list_online_agents()
    if not agent_ids:
        return []
    return await dal.telemetry.getResourceSnapshots(agent_ids, hours=hours, limit=limit)

# ── Per-agent queries ──

@router.get("/{agent_id}")
async def getTelemetry(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=24, ge=1, le=168), limit: int = Query(default=500, ge=1, le=5000)):
    return await dal.telemetry.getAll([agent_id], hours=hours, limit=limit)

@router.get("/{agent_id}/resources")
async def getAgentResources(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=1, ge=1, le=168), limit: int = Query(default=200, ge=1, le=5000)):
    return await dal.telemetry.getAgentResources(agent_id, hours=hours, limit=limit)

@router.get("/{agent_id}/network")
async def getAgentNetwork(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=24, ge=1, le=168), limit: int = Query(default=500, ge=1, le=5000)):
    return await dal.telemetry.getAgentNetwork(agent_id, hours=hours, limit=limit)

@router.get("/{agent_id}/filesystem")
async def getAgentFilesystem(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=24, ge=1, le=168), limit: int = Query(default=500, ge=1, le=5000)):
    return await dal.telemetry.getAgentFilesystem(agent_id, hours=hours, limit=limit)

@router.get("/{agent_id}/processes")
async def getAgentProcesses(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=1, ge=1, le=24), limit: int = Query(default=200, ge=1, le=2000)):
    return await dal.telemetry.getAgentProcesses(agent_id, hours=hours, limit=limit)

@router.get("/{agent_id}/ports")
async def getAgentPorts(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal), hours: int = Query(default=1, ge=1, le=24), limit: int = Query(default=200, ge=1, le=2000)):
    return await dal.telemetry.getAgentPorts(agent_id, hours=hours, limit=limit)
