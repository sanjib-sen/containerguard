from fastapi import APIRouter

router = APIRouter(
    prefix="/telemetry",
    tags=["telemetry"],
    responses={404: {"description": "Not found"}},
)


@router.post("/")
async def postTelemetry():
    pass

@router.get("/{agent_id}")
async def getTelemetry(agent_id):
    pass

@router.get("/network")
async def getNetwork():
    pass

@router.get("/filesystem")
async def getFilesystem():
    pass

@router.get("/resources")
async def getResources():
    pass

