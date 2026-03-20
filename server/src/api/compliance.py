from fastapi import APIRouter

router = APIRouter(
    prefix="/compliance",
    tags=["compliance"],
    responses={404: {"description": "Not found"}},
)


@router.get("/rules")
async def getrules():
    pass

@router.post("/rules")
async def postRule():
    pass

@router.get("/status")
async def getStatus():
    pass

@router.post("/evaluate")
async def postEvaluate():
    pass





