from fastapi import APIRouter

router = APIRouter(
    prefix="/ws",
    tags=["ws"],
    responses={404: {"description": "Not found"}},
)


@router.websocket("/dashboard")
async def wsDashboard():
    pass

@router.websocket("/alerts")
async def wsAlerts():
    pass




