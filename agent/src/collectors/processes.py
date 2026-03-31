from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import psutil

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ProcessInfo:
    pid: int
    command: str
    user: str
    started: datetime


def collect() -> list[ProcessInfo]:
    processes: list[ProcessInfo] = []
    for proc in psutil.process_iter(["pid", "name", "username", "create_time"]):
        try:
            info = proc.info
            pid = info["pid"]
            name = info.get("name") or "unknown"
            user = info.get("username") or "unknown"
            create_time = info.get("create_time") or 0.0
            started = datetime.fromtimestamp(create_time, tz=timezone.utc)

            processes.append(ProcessInfo(
                pid=pid,
                command=name,
                user=user,
                started=started,
            ))
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue

    return processes
