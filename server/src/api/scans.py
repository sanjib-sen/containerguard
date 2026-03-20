from fastapi import APIRouter

router = APIRouter(
    prefix="/scans",
    tags=["scans"],
    responses={404: {"description": "Not found"}},
)


@router.post("/")
async def postScans():
    pass

@router.get("/")
async def getScans():
    pass

@router.get("/{id}")
async def getScanDetails():
    pass






