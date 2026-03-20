from fastapi import APIRouter

router = APIRouter(
    prefix="/alerts",
    tags=["alerts"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
async def getAlerts():
    pass

@router.patch("/{id}")
async def patchAlert():
    pass

@router.get("/rules")
async def getRules():
    pass

@router.post("/rules")
async def postRule():
    pass





