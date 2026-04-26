from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.agents import router as agents_router
from .api.alerts import router as alerts_router
from .api.compliance import router as compliance_router
from .api.logs import router as logs_router
from .api.scans import router as scans_router
from .api.telemetry import router as telemetry_router
from .api.websocket import router as websocket_router
from .db import dispose_engine
from .engines.alerts import alert_engine
from .engines.anomaly import anomaly_engine
from .metrics.exporter import build_metrics_app
from .realtime import broker


@asynccontextmanager
async def lifespan(_: FastAPI):
    await broker.start()
    await alert_engine.start()
    await anomaly_engine.start()
    yield
    await anomaly_engine.stop()
    await alert_engine.stop()
    await broker.stop()
    await dispose_engine()


app = FastAPI(lifespan=lifespan)

metrics_app = build_metrics_app()
app.mount("/metrics", metrics_app)

api_v1_prefix = "/api/v1"

app.include_router(agents_router, prefix=api_v1_prefix)
app.include_router(alerts_router, prefix=api_v1_prefix)
app.include_router(compliance_router, prefix=api_v1_prefix)
app.include_router(logs_router, prefix=api_v1_prefix)
app.include_router(scans_router, prefix=api_v1_prefix)
app.include_router(telemetry_router, prefix=api_v1_prefix)

app.include_router(websocket_router, prefix="") # /ws/...


@app.get("/")
async def root():
    return {"message": "Hello World"}
