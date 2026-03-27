from fastapi import APIRouter, Depends, HTTPException, status

from ..db import DataAccessLayer, get_dal
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
async def getNetwork():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Network telemetry query is not implemented yet")


@router.get("/filesystem")
async def getFilesystem():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Filesystem telemetry query is not implemented yet")


@router.get("/resources")
async def getResources():
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Resources telemetry query is not implemented yet")


@router.get("/{agent_id}")
async def getTelemetry(agent_id):
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Telemetry query is not implemented yet")
