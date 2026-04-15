from __future__ import annotations


__all__ = ["run_heartbeat_monitor"]


def __getattr__(name: str):
    if name == "run_heartbeat_monitor":
        from .heartbeat_monitor import run_heartbeat_monitor

        return run_heartbeat_monitor
    raise AttributeError(name)
