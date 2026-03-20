from fastapi import APIRouter

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
    responses={404: {"description": "Not found"}},
)


@router.post("/register")
async def postRegister():
    pass

@router.post("/heartbeat")
async def postHeartbeat():
    pass

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
