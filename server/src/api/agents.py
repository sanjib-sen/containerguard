from fastapi import APIRouter, Depends, HTTPException, status

from ..db import DataAccessLayer, get_dal
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
    return AgentResponse.model_validate(agent)


@router.post("/heartbeat", response_model=AgentHeartbeatResponse)
async def postHeartbeat(payload: AgentHeartbeatRequest, dal: DataAccessLayer = Depends(get_dal)):
    agent = await dal.agents.record_heartbeat(agent_id=payload.agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return AgentHeartbeatResponse(
        agent_id=agent.id,
        status=agent.status,
        last_heartbeat=agent.last_heartbeat,
    )

@router.get("/")
async def getAgents():
    pass

@router.get("/{id}")
async def getAgent(id):
    pass

@router.get("/{id}/config")
async def getAgentId():
    pass

@router.delete("/{id}")
async def deleteAgent():
    pass
