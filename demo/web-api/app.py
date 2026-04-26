"""
Demo Web API — simulates a microservice handling HTTP requests.
Generates realistic CPU, memory, network, and filesystem activity
so the ContainerGuard agent has interesting telemetry to collect.
"""

import asyncio
import json
import logging
import math
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx
from fastapi import FastAPI

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("web-api")

app = FastAPI(title="Demo Web API")

TEMP_DIR = Path("/tmp/web-api-data")
TEMP_DIR.mkdir(exist_ok=True)

REQUEST_COUNT = 0


@app.get("/")
async def root():
    global REQUEST_COUNT
    REQUEST_COUNT += 1
    logger.info("GET / — request #%d", REQUEST_COUNT)
    return {"service": "web-api", "status": "ok", "requests_served": REQUEST_COUNT}


@app.get("/health")
async def health():
    logger.info("health check passed")
    return {"healthy": True, "uptime_seconds": time.monotonic()}


@app.get("/compute")
async def compute():
    """Simulate CPU work."""
    start = time.monotonic()
    total = sum(math.sqrt(i) for i in range(100_000))
    elapsed = time.monotonic() - start
    logger.info("compute task completed in %.3fs, result=%.2f", elapsed, total)
    return {"elapsed_ms": round(elapsed * 1000, 1), "result": round(total, 2)}


@app.get("/data")
async def write_data():
    """Simulate filesystem write."""
    filename = f"record_{int(time.time())}.json"
    filepath = TEMP_DIR / filename
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "values": [random.random() for _ in range(50)],
        "source": "web-api",
    }
    filepath.write_text(json.dumps(data))
    logger.info("wrote data file: %s (%d bytes)", filename, filepath.stat().st_size)
    return {"file": filename, "size_bytes": filepath.stat().st_size}


async def background_tasks():
    """Run periodic background work to generate telemetry."""
    logger.info("background task scheduler started")
    while True:
        await asyncio.sleep(random.uniform(10, 30))

        # Simulate outbound API call
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                target = random.choice([
                    "https://httpbin.org/get",
                    "https://api.github.com",
                    "https://jsonplaceholder.typicode.com/posts/1",
                ])
                resp = await client.get(target)
                logger.info("outbound call: %s -> %d (%dB)", target, resp.status_code, len(resp.content))
        except Exception as exc:
            logger.warning("outbound call failed: %s", exc)

        # Simulate file writes
        filepath = TEMP_DIR / f"log_{int(time.time())}.txt"
        filepath.write_text(f"background task ran at {datetime.now(timezone.utc).isoformat()}\n" * 20)
        logger.info("background: wrote log file %s", filepath.name)

        # Simulate compute burst
        _ = sum(math.sqrt(i) for i in range(50_000))
        logger.info("background: compute burst complete")

        # Cleanup old files (keep last 20)
        files = sorted(TEMP_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
        for old in files[20:]:
            old.unlink()
            logger.info("background: cleaned up old file %s", old.name)


@app.on_event("startup")
async def startup():
    logger.info("Demo Web API starting on port 8080")
    asyncio.create_task(background_tasks())
