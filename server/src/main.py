from contextlib import asynccontextmanager

from fastapi import FastAPI

from .api.agents import router as agents_router
from .api.alerts import router as alerts_router
from .api.compliance import router as compliance_router
from .api.scans import router as scans_router
from .api.telemetry import router as telemetry_router
from .api.websocket import router as websocket_router
from .db import dispose_engine, initialize_database


@asynccontextmanager
async def lifespan(_: FastAPI):
    await initialize_database()
    yield
    await dispose_engine()


app = FastAPI(lifespan=lifespan)
api_v1_prefix = "/api/v1"

app.include_router(agents_router, prefix=api_v1_prefix)
app.include_router(alerts_router, prefix=api_v1_prefix)
app.include_router(compliance_router, prefix=api_v1_prefix)
app.include_router(scans_router, prefix=api_v1_prefix)
app.include_router(telemetry_router, prefix=api_v1_prefix)
app.include_router(websocket_router, prefix=api_v1_prefix)


@app.get("/")
async def root():
    return {"message": "Hello World"}
