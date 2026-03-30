from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ..db import DataAccessLayer, get_dal
from ..metrics.exporter import record_telemetry_ingest, set_latest_resource_metrics
from ..schemas import TelemetryIngestRequest, TelemetryIngestResponse

router = APIRouter(
    prefix="/telemetry",
    tags=["telemetry"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=TelemetryIngestResponse, status_code=status.HTTP_201_CREATED)
async def postTelemetry(payload: TelemetryIngestRequest, dal: DataAccessLayer = Depends(get_dal)):
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

@router.get("/network")
async def getNetwork(dal: DataAccessLayer = Depends(get_dal)):
    """get network events for all online agents in the last 24 hours
    """
    agent_ids = await dal.agents.list_online_agents()
    if not agent_ids:
        return []
    network_events = await dal.telemetry.getNetworkEvents(agent_ids)
    return network_events

@router.get("/filesystem")
async def getFilesystem(dal: DataAccessLayer = Depends(get_dal)):
    agent_ids = await dal.agents.list_online_agents()
    if not agent_ids:
        return []
    filesystem_events = await dal.telemetry.getFilesystemEvents(agent_ids)
    return filesystem_events

@router.get("/resources")
async def getResources(dal: DataAccessLayer = Depends(get_dal)):
    agent_ids = await dal.agents.list_online_agents()
    if not agent_ids:
        return []
    resource_snapshots = await dal.telemetry.getResourceSnapshots(agent_ids)
    return resource_snapshots

@router.get("/{agent_id}")
async def getTelemetry(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal)):
    agent = [agent_id]
    telemetry_events = await dal.telemetry.getAll(agent)
    return telemetry_events