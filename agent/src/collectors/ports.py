from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

import psutil

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class OpenPort:
    port: int
    protocol: str
    pid: int
    process: str


def _get_process_name(pid: int) -> str:
    if pid <= 0:
        return "unknown"
    try:
        return psutil.Process(pid).name()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        try:
            return Path(f"/proc/{pid}/comm").read_text().strip()
        except OSError:
            return "unknown"


def _parse_ss_block(lines: list[str], protocol: str, seen: set[tuple[int, str]]) -> list[OpenPort]:
    """Parse ss output lines for a given protocol, deduplicating via seen."""
    ports: list[OpenPort] = []
    for line in lines:
        parts = line.split()
        if len(parts) < 5:
            continue
        # Parse local address (e.g., "0.0.0.0:8080" or "*:8080")
        local_addr = parts[3]
        port_str = local_addr.rsplit(":", 1)[-1]
        try:
            port_num = int(port_str)
        except ValueError:
            continue

        key = (port_num, protocol)
        if key in seen:
            continue
        seen.add(key)

        # Parse process info from the last column (e.g., 'users:(("python",pid=1,fd=7))')
        pid = 0
        proc_name = "unknown"
        if len(parts) >= 6:
            proc_col = parts[5]
            if "pid=" in proc_col:
                try:
                    pid = int(proc_col.split("pid=")[1].split(",")[0].split(")")[0])
                    proc_name = _get_process_name(pid)
                except (ValueError, IndexError):
                    pass
            if proc_name == "unknown" and "((" in proc_col:
                try:
                    proc_name = proc_col.split('(("')[1].split('"')[0]
                except IndexError:
                    pass

        ports.append(OpenPort(port=port_num, protocol=protocol, pid=pid, process=proc_name))
    return ports


def _ss_fallback() -> list[OpenPort]:
    """Use ss to find listening ports with process info."""
    ports: list[OpenPort] = []
    seen: set[tuple[int, str]] = set()
    try:
        tcp = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True, timeout=5)
        ports += _parse_ss_block(tcp.stdout.splitlines()[1:], "tcp", seen)

        udp = subprocess.run(["ss", "-ulnp"], capture_output=True, text=True, timeout=5)
        ports += _parse_ss_block(udp.stdout.splitlines()[1:], "udp", seen)

    except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
        logger.debug("ss fallback failed: %s", exc)

    return ports


def collect() -> list[OpenPort]:
    ports: list[OpenPort] = []
    seen: set[tuple[int, str]] = set()

    # Try psutil first
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status != "LISTEN":
                continue
            if not conn.laddr:
                continue

            port = conn.laddr.port
            proto = "tcp" if conn.type.name == "SOCK_STREAM" else "udp"
            key = (port, proto)
            if key in seen:
                continue
            seen.add(key)

            pid = conn.pid or 0
            proc_name = _get_process_name(pid)

            # Inside a container, PID 1 is the main process — if we can't determine
            # the pid but we know there's a listener, attribute it to PID 1
            if pid == 0:
                pid = 1
                proc_name = _get_process_name(1)

            ports.append(OpenPort(port=port, protocol=proto, pid=pid, process=proc_name))
    except (psutil.AccessDenied, OSError) as exc:
        logger.debug("psutil.net_connections failed: %s", exc)

    # If psutil found nothing, try ss
    if not ports:
        ports = _ss_fallback()
        # Same PID 1 fallback
        for p in ports:
            if p.pid == 0:
                p.pid = 1
                p.process = _get_process_name(1)

    return ports