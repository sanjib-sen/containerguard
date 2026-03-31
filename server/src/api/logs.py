from __future__ import annotations

import httpx
from fastapi import APIRouter, HTTPException, Query

from ..config import get_settings

router = APIRouter(
    prefix="/logs",
    tags=["logs"],
)


def _loki_url() -> str:
    url = get_settings().loki_url
    if not url:
        raise HTTPException(status_code=503, detail="Loki is not configured")
    return url


@router.get("/query")
async def queryLogs(
    query: str = Query(description="LogQL query, e.g. {service=\"agent\"}"),
    limit: int = Query(default=200, ge=1, le=5000),
    start: str | None = Query(default=None, description="RFC3339 or Unix nanoseconds"),
    end: str | None = Query(default=None, description="RFC3339 or Unix nanoseconds"),
    direction: str = Query(default="backward", regex="^(forward|backward)$"),
):
    """Proxy log queries to Loki's query_range endpoint."""
    base = _loki_url()
    params: dict[str, str | int] = {
        "query": query,
        "limit": limit,
        "direction": direction,
    }
    if start:
        params["start"] = start
    if end:
        params["end"] = end

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(f"{base}/loki/api/v1/query_range", params=params)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()


@router.get("/labels")
async def getLabels():
    """Get available log label names from Loki."""
    base = _loki_url()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base}/loki/api/v1/labels")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()


@router.get("/labels/{label}/values")
async def getLabelValues(label: str):
    """Get values for a specific log label from Loki."""
    base = _loki_url()
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{base}/loki/api/v1/label/{label}/values")
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)
    return resp.json()
