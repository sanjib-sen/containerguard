from __future__ import annotations

import logging
from dataclasses import dataclass, field

import psutil

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class NetworkConnection:
    direction: str
    src_ip: str
    dst_ip: str | None
    dst_port: int
    protocol: str
    bytes_transferred: int


def collect() -> list[NetworkConnection]:
    connections: list[NetworkConnection] = []
    try:
        for conn in psutil.net_connections(kind="inet"):
            if conn.status == "NONE":
                continue

            proto = "tcp" if conn.type.name == "SOCK_STREAM" else "udp"
            laddr = conn.laddr
            raddr = conn.raddr

            if not laddr:
                continue

            if raddr:
                connections.append(NetworkConnection(
                    direction="outbound",
                    src_ip=laddr.ip if laddr.ip else "0.0.0.0",
                    dst_ip=raddr.ip if raddr.ip else None,
                    dst_port=raddr.port,
                    protocol=proto,
                    bytes_transferred=0,
                ))
            else:
                if conn.status == "LISTEN":
                    continue
                connections.append(NetworkConnection(
                    direction="inbound",
                    src_ip=laddr.ip if laddr.ip else "0.0.0.0",
                    dst_ip=None,
                    dst_port=laddr.port,
                    protocol=proto,
                    bytes_transferred=0,
                ))
    except (psutil.AccessDenied, OSError) as exc:
        logger.warning("network collection failed: %s", exc)

    return connections
