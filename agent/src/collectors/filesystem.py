from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Thread

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)

DEFAULT_WATCH_PATHS = ["/etc", "/var/log", "/tmp"]


@dataclass(slots=True)
class FilesystemEvent:
    type: str
    path: str
    pid: int
    process: str
    timestamp: datetime


class _Handler(FileSystemEventHandler):
    def __init__(self, queue: asyncio.Queue[FilesystemEvent], loop: asyncio.AbstractEventLoop) -> None:
        self._queue = queue
        self._loop = loop

    def _enqueue(self, event_type: str, path: str) -> None:
        evt = FilesystemEvent(
            type=event_type,
            path=path,
            pid=0,
            process="unknown",
            timestamp=datetime.now(timezone.utc),
        )
        self._loop.call_soon_threadsafe(self._queue.put_nowait, evt)

    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._enqueue("create", event.src_path)

    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._enqueue("write", event.src_path)

    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            self._enqueue("delete", event.src_path)


class FilesystemCollector:
    def __init__(self, watch_paths: list[str] | None = None) -> None:
        self._watch_paths = watch_paths or DEFAULT_WATCH_PATHS
        self._queue: asyncio.Queue[FilesystemEvent] = asyncio.Queue(maxsize=1000)
        self._observer: Observer | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        handler = _Handler(self._queue, loop)
        self._observer = Observer()
        for path_str in self._watch_paths:
            path = Path(path_str)
            if path.is_dir():
                self._observer.schedule(handler, str(path), recursive=True)
                logger.info("watching %s", path)
            else:
                logger.debug("skipping non-existent path %s", path)
        self._observer.daemon = True
        self._observer.start()

    def stop(self) -> None:
        if self._observer is not None:
            self._observer.stop()
            self._observer.join(timeout=5)

    def drain(self) -> list[FilesystemEvent]:
        events: list[FilesystemEvent] = []
        while not self._queue.empty():
            try:
                events.append(self._queue.get_nowait())
            except asyncio.QueueEmpty:
                break
        return events
