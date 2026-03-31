from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from ..db import DataAccessLayer, get_dal
from ..metrics.exporter import (
    record_agent_heartbeat,
    record_agent_register,
)
from ..schemas import (
    AgentHeartbeatRequest,
    AgentHeartbeatResponse,
    AgentRegisterRequest,
    AgentResponse,
)

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)


@router.post("/register", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def postRegister(payload: AgentRegisterRequest, dal: DataAccessLayer = Depends(get_dal)):
    """registers an agent into the DB
    """
    agent = await dal.agents.register_agent(
        container_id=payload.container_id,
        hostname=payload.hostname,
        image=payload.image,
        ip=str(payload.ip) if payload.ip is not None else None,
    )
    record_agent_register()
    return AgentResponse.model_validate(agent)


@router.post("/heartbeat", response_model=AgentHeartbeatResponse)
async def postHeartbeat(payload: AgentHeartbeatRequest, dal: DataAccessLayer = Depends(get_dal)):
    agent = await dal.agents.record_heartbeat(agent_id=payload.agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    record_agent_heartbeat()
    return AgentHeartbeatResponse(
        agent_id=agent.id,
        status=agent.status,
        last_heartbeat=agent.last_heartbeat,
    )

@router.get("/", response_model=list[AgentResponse])
async def getAgents(dal: DataAccessLayer = Depends(get_dal)):
    agents = await dal.agents.list_all()
    return [AgentResponse.model_validate(a) for a in agents]

@router.get("/{agent_id}", response_model=AgentResponse)
async def getAgent(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal)):
    agent = await dal.agents.get_by_id(agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return AgentResponse.model_validate(agent)

@router.get("/{agent_id}/config")
async def getAgentConfig(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal)):
    agent = await dal.agents.get_by_id(agent_id)
    if agent is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return {"agent_id": str(agent.id), "collection_interval_seconds": 15}

@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deleteAgent(agent_id: UUID, dal: DataAccessLayer = Depends(get_dal)):
    deleted = await dal.agents.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
