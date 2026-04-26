from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import ScanResults


class ScansRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_scan(
        self,
        *,
        image_name: str,
        image_tag: str | None,
        agent_id: UUID | None = None,
    ) -> ScanResults:
        scan = ScanResults(
            image_name=image_name,
            image_tag=image_tag,
            agent_id=agent_id,
            status="pending",
            vulnerabilities_json=[],
            started_at=datetime.now(timezone.utc),
        )
        self.session.add(scan)
        await self.session.commit()
        await self.session.refresh(scan)
        return scan

    async def get_scan(self, scan_id: UUID) -> ScanResults | None:
        return await self.session.get(ScanResults, scan_id)

    async def list_scans(self, *, limit: int = 100) -> list[ScanResults]:
        statement = (
            select(ScanResults)
            .order_by(ScanResults.scanned_at.desc())
            .limit(limit)
        )
        result = await self.session.scalars(statement)
        return list(result)

    async def update_scan_completed(
        self,
        scan_id: UUID,
        *,
        vulnerabilities: Any,
        status: str = "completed",
    ) -> ScanResults | None:
        scan = await self.get_scan(scan_id)
        if scan is None:
            return None
        scan.status = status
        scan.vulnerabilities_json = vulnerabilities
        scan.completed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(scan)
        return scan

    async def update_scan_failed(self, scan_id: UUID, *, error_message: str) -> ScanResults | None:
        scan = await self.get_scan(scan_id)
        if scan is None:
            return None
        scan.status = "failed"
        scan.error_message = error_message
        scan.completed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(scan)
        return scan
