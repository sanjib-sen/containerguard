from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status

from ..db import DataAccessLayer, get_dal
from ..engines.scanner import scanner
from ..schemas import ScanRequest, ScanResultResponse

router = APIRouter(
    prefix="/scans",
    tags=["scans"],
    responses={404: {"description": "Not found"}},
)


def _split_image(image: str) -> tuple[str, str | None]:
    """Split 'redis:7' -> ('redis', '7'). Default to 'latest' if no tag."""
    if "@" in image:
        # digest — keep whole thing as name
        return image, None
    if ":" in image:
        name, tag = image.rsplit(":", 1)
        return name, tag
    return image, "latest"


@router.post("/", response_model=ScanResultResponse, status_code=status.HTTP_201_CREATED)
async def createScan(
    payload: ScanRequest,
    background_tasks: BackgroundTasks,
    dal: DataAccessLayer = Depends(get_dal),
):
    image_name, image_tag = _split_image(payload.image)
    scan = await dal.scans.create_scan(
        image_name=image_name,
        image_tag=image_tag,
        agent_id=payload.agent_id,
    )
    # Run trivy in background — we kick it off as an asyncio task so the request returns fast
    asyncio.create_task(scanner.run_scan(scan.id, payload.image))
    return ScanResultResponse.model_validate(scan)


@router.get("/", response_model=list[ScanResultResponse])
async def listScans(
    dal: DataAccessLayer = Depends(get_dal),
    limit: int = Query(default=100, ge=1, le=1000),
):
    scans = await dal.scans.list_scans(limit=limit)
    return [ScanResultResponse.model_validate(s) for s in scans]


@router.get("/{scan_id}", response_model=ScanResultResponse)
async def getScan(scan_id: UUID, dal: DataAccessLayer = Depends(get_dal)):
    scan = await dal.scans.get_scan(scan_id)
    if scan is None:
        raise HTTPException(status_code=404, detail="Scan not found")
    return ScanResultResponse.model_validate(scan)
