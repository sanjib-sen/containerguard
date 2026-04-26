from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from .repository.agentsRepo import AgentsRepository
from .repository.alertsRepo import AlertsRepository
from .repository.complianceRepo import ComplianceRepository
from .repository.scansRepo import ScansRepository
from .repository.telemetryRepo import TelemetryRepository
from .session import get_db


class DataAccessLayer:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.agents = AgentsRepository(session)
        self.telemetry = TelemetryRepository(session)
        self.alerts = AlertsRepository(session)
        self.compliance = ComplianceRepository(session)
        self.scans = ScansRepository(session)


def create_data_access_layer(session: AsyncSession) -> DataAccessLayer:
    return DataAccessLayer(session)


async def get_dal() -> AsyncIterator[DataAccessLayer]:
    async for session in get_db():
        yield create_data_access_layer(session)
