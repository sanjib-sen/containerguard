import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.agents import router as agents_router
from .api.alerts import router as alerts_router
from .api.compliance import router as compliance_router
from .api.scans import router as scans_router
from .api.telemetry import router as telemetry_router
from .api.websocket import router as websocket_router
from .db import create_data_access_layer, dispose_engine, get_session_factory, initialize_database
from .metrics.exporter import build_metrics_app, set_agent_counts
from .workers import run_heartbeat_monitor


@asynccontextmanager
async def lifespan(_: FastAPI):
    # start up
    await initialize_database()
    async with get_session_factory()() as session:
        dal = create_data_access_layer(session)
        total_agents = await dal.agents.count_all()
        online_agents = await dal.agents.count_by_status("online")
        set_agent_counts(total=total_agents, online=online_agents)
    heartbeat_monitor_task = asyncio.create_task(run_heartbeat_monitor())
    yield
    # shutdown
    heartbeat_monitor_task.cancel()
    try:
        await heartbeat_monitor_task
    except asyncio.CancelledError:
        pass
    await dispose_engine()


app = FastAPI(lifespan=lifespan)

metrics_app = build_metrics_app()
app.mount("/metrics", metrics_app)

api_v1_prefix = "/api/v1"

app.include_router(agents_router, prefix=api_v1_prefix)
app.include_router(alerts_router, prefix=api_v1_prefix)
app.include_router(compliance_router, prefix=api_v1_prefix)
app.include_router(scans_router, prefix=api_v1_prefix)
app.include_router(telemetry_router, prefix=api_v1_prefix)

app.include_router(websocket_router, prefix="") # /ws/...


@app.get("/")
async def root():
    return {"message": "Hello World"}
