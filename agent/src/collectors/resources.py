from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)

CGROUP_V2_MEMORY_MAX = Path("/sys/fs/cgroup/memory.max")


@dataclass(slots=True)
class ResourceSnapshot:
    cpu_percent: float
    memory_mb: float
    memory_limit_mb: float
    net_bytes_sent: float
    net_bytes_recv: float
    disk_read_bytes: float
    disk_write_bytes: float


def _read_memory_limit_mb() -> float:
    try:
        raw = CGROUP_V2_MEMORY_MAX.read_text().strip()
        if raw == "max":
            return psutil.virtual_memory().total / (1024 * 1024)
        return int(raw) / (1024 * 1024)
    except (FileNotFoundError, OSError, ValueError):
        return psutil.virtual_memory().total / (1024 * 1024)


def collect() -> ResourceSnapshot:
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    net = psutil.net_io_counters()

    disk_counters = psutil.disk_io_counters()
    disk_read = disk_counters.read_bytes if disk_counters else 0.0
    disk_write = disk_counters.write_bytes if disk_counters else 0.0

    return ResourceSnapshot(
        cpu_percent=cpu,
        memory_mb=mem.used / (1024 * 1024),
        memory_limit_mb=_read_memory_limit_mb(),
        net_bytes_sent=float(net.bytes_sent),
        net_bytes_recv=float(net.bytes_recv),
        disk_read_bytes=float(disk_read),
        disk_write_bytes=float(disk_write),
    )
