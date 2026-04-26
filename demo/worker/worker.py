"""
Demo Background Worker — simulates a data processing pipeline.
Generates CPU spikes, heavy disk I/O, network calls, and filesystem events
so the ContainerGuard agent has diverse telemetry to collect.
"""

import hashlib
import json
import logging
import math
import os
import random
import socket
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("worker")

DATA_DIR = Path("/tmp/worker-data")
DATA_DIR.mkdir(exist_ok=True)

ENDPOINTS = [
    "https://httpbin.org/post",
    "https://jsonplaceholder.typicode.com/posts",
    "https://api.github.com/zen",
    "https://httpbin.org/delay/1",
    "https://pypi.org/simple/requests/",
]


def cpu_intensive_task():
    """Simulate heavy computation — hashing + math."""
    start = time.monotonic()
    data = os.urandom(1024 * 1024)  # 1MB random data
    for _ in range(10):
        data = hashlib.sha256(data).digest() * 32768
    total = sum(math.sin(i) * math.cos(i) for i in range(200_000))
    elapsed = time.monotonic() - start
    logger.info("CPU task: hashing + math completed in %.3fs (result=%.4f)", elapsed, total)
    return elapsed


def disk_io_task():
    """Simulate heavy disk writes and reads."""
    filename = f"batch_{int(time.time())}_{random.randint(1000,9999)}.dat"
    filepath = DATA_DIR / filename

    # Write a batch of data
    records = []
    for i in range(500):
        records.append({
            "id": i,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "value": random.gauss(100, 25),
            "hash": hashlib.md5(str(i).encode()).hexdigest(),
        })
    filepath.write_text(json.dumps(records, indent=2))
    size = filepath.stat().st_size
    logger.info("disk I/O: wrote %s (%d KB)", filename, size // 1024)

    # Read it back (simulate processing)
    data = json.loads(filepath.read_text())
    avg = sum(r["value"] for r in data) / len(data)
    logger.info("disk I/O: processed %d records, avg_value=%.2f", len(data), avg)

    # Cleanup — keep last 10 files
    files = sorted(DATA_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True)
    removed = 0
    for old in files[10:]:
        old.unlink()
        removed += 1
    if removed:
        logger.info("disk I/O: cleaned up %d old files", removed)

    return avg


def network_task():
    """Simulate outbound network requests."""
    url = random.choice(ENDPOINTS)
    try:
        with httpx.Client(timeout=15.0) as client:
            if "post" in url.lower():
                resp = client.post(url, json={"worker": socket.gethostname(), "timestamp": time.time()})
            else:
                resp = client.get(url)
            logger.info(
                "network: %s %s -> %d (%dB, %.0fms)",
                "POST" if "post" in url.lower() else "GET",
                url,
                resp.status_code,
                len(resp.content),
                resp.elapsed.total_seconds() * 1000,
            )
    except Exception as exc:
        logger.error("network: request to %s failed: %s", url, exc)


def dns_lookups():
    """Simulate DNS resolution."""
    domains = ["google.com", "github.com", "pypi.org", "npmjs.org", "docker.com"]
    domain = random.choice(domains)
    try:
        ip = socket.gethostbyname(domain)
        logger.info("DNS: resolved %s -> %s", domain, ip)
    except socket.gaierror as exc:
        logger.warning("DNS: failed to resolve %s: %s", domain, exc)


def main():
    logger.info("Demo Worker starting — hostname=%s pid=%d", socket.gethostname(), os.getpid())
    logger.info("Processing pipeline initialized")

    cycle = 0
    while True:
        cycle += 1
        logger.info("=== Processing cycle #%d ===", cycle)

        # Each cycle does a random mix of tasks
        tasks = random.sample(["cpu", "disk", "network", "dns", "cpu", "disk", "network"], k=random.randint(3, 6))

        for task in tasks:
            if task == "cpu":
                cpu_intensive_task()
            elif task == "disk":
                disk_io_task()
            elif task == "network":
                network_task()
            elif task == "dns":
                dns_lookups()

        # Random sleep between cycles (8-20 seconds)
        sleep_time = random.uniform(8, 20)
        logger.info("cycle #%d complete — sleeping %.1fs", cycle, sleep_time)
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
