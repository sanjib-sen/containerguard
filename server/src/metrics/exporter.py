from __future__ import annotations

import os

from prometheus_client import CollectorRegistry, Counter, Gauge, REGISTRY, make_asgi_app, multiprocess


_MULTIPROC_DIR = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
if _MULTIPROC_DIR:
    os.makedirs(_MULTIPROC_DIR, exist_ok=True)


AGENT_REGISTER_REQUESTS_TOTAL = Counter(
    "containerguard_agent_register_requests_total",
    "Total successful agent register requests handled by the server.",
)

AGENT_HEARTBEATS_TOTAL = Counter(
    "containerguard_agent_heartbeats_total",
    "Total successful agent heartbeats handled by the server.",
)

TELEMETRY_INGESTS_TOTAL = Counter(
    "containerguard_telemetry_ingests_total",
    "Total telemetry batches successfully ingested by the server.",
)

NETWORK_EVENTS_STORED_TOTAL = Counter(
    "containerguard_network_events_stored_total",
    "Total network connection events stored in PostgreSQL.",
)

FILESYSTEM_EVENTS_STORED_TOTAL = Counter(
    "containerguard_filesystem_events_stored_total",
    "Total filesystem events stored in PostgreSQL.",
)

PROCESS_SNAPSHOTS_STORED_TOTAL = Counter(
    "containerguard_process_snapshots_stored_total",
    "Total process snapshots stored in PostgreSQL.",
)

PORT_SNAPSHOTS_STORED_TOTAL = Counter(
    "containerguard_port_snapshots_stored_total",
    "Total port snapshots stored in PostgreSQL.",
)

RESOURCE_SNAPSHOTS_STORED_TOTAL = Counter(
    "containerguard_resource_snapshots_stored_total",
    "Total resource snapshots stored in PostgreSQL.",
)

AGENTS_TOTAL = Gauge(
    "containerguard_agents_total",
    "Current number of registered agents.",
    multiprocess_mode="livemax",
)

AGENTS_ONLINE = Gauge(
    "containerguard_agents_online",
    "Current number of agents marked online.",
    multiprocess_mode="livemax",
)

RESOURCE_CPU_PERCENT = Gauge(
    "containerguard_agent_cpu_percent",
    "Latest reported CPU percent for an agent.",
    labelnames=("agent_id", "container_id", "hostname"),
    multiprocess_mode="livemostrecent",
)

RESOURCE_MEMORY_MB = Gauge(
    "containerguard_agent_memory_mb",
    "Latest reported memory usage in MB for an agent.",
    labelnames=("agent_id", "container_id", "hostname"),
    multiprocess_mode="livemostrecent",
)

RESOURCE_MEMORY_LIMIT_MB = Gauge(
    "containerguard_agent_memory_limit_mb",
    "Latest reported memory limit in MB for an agent.",
    labelnames=("agent_id", "container_id", "hostname"),
    multiprocess_mode="livemostrecent",
)

RESOURCE_NET_BYTES_SENT = Gauge(
    "containerguard_agent_net_bytes_sent",
    "Latest reported network bytes sent for an agent.",
    labelnames=("agent_id", "container_id", "hostname"),
    multiprocess_mode="livemostrecent",
)

RESOURCE_NET_BYTES_RECV = Gauge(
    "containerguard_agent_net_bytes_recv",
    "Latest reported network bytes received for an agent.",
    labelnames=("agent_id", "container_id", "hostname"),
    multiprocess_mode="livemostrecent",
)

RESOURCE_DISK_READ_BYTES = Gauge(
    "containerguard_agent_disk_read_bytes",
    "Latest reported disk read bytes for an agent.",
    labelnames=("agent_id", "container_id", "hostname"),
    multiprocess_mode="livemostrecent",
)

RESOURCE_DISK_WRITE_BYTES = Gauge(
    "containerguard_agent_disk_write_bytes",
    "Latest reported disk write bytes for an agent.",
    labelnames=("agent_id", "container_id", "hostname"),
    multiprocess_mode="livemostrecent",
)


def build_metrics_app():
    multiproc_dir = os.environ.get("PROMETHEUS_MULTIPROC_DIR")
    if multiproc_dir:
        os.makedirs(multiproc_dir, exist_ok=True)
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        return make_asgi_app(registry=registry)
    return make_asgi_app(registry=REGISTRY)


def set_agent_counts(*, total: int, online: int) -> None:
    AGENTS_TOTAL.set(total)
    AGENTS_ONLINE.set(online)


def record_agent_register() -> None:
    AGENT_REGISTER_REQUESTS_TOTAL.inc()


def record_agent_heartbeat() -> None:
    AGENT_HEARTBEATS_TOTAL.inc()


def record_telemetry_ingest(
    *,
    stored_network_connections: int,
    stored_filesystem_events: int,
    stored_processes: int,
    stored_ports: int,
    stored_resources: bool,
) -> None:
    TELEMETRY_INGESTS_TOTAL.inc()
    NETWORK_EVENTS_STORED_TOTAL.inc(stored_network_connections)
    FILESYSTEM_EVENTS_STORED_TOTAL.inc(stored_filesystem_events)
    PROCESS_SNAPSHOTS_STORED_TOTAL.inc(stored_processes)
    PORT_SNAPSHOTS_STORED_TOTAL.inc(stored_ports)
    if stored_resources:
        RESOURCE_SNAPSHOTS_STORED_TOTAL.inc()


def set_latest_resource_metrics(
    *,
    agent_id: str,
    container_id: str,
    hostname: str,
    cpu_percent: float,
    memory_mb: float,
    memory_limit_mb: float,
    net_bytes_sent: float,
    net_bytes_recv: float,
    disk_read_bytes: float,
    disk_write_bytes: float,
) -> None:
    labels = {
        "agent_id": agent_id,
        "container_id": container_id,
        "hostname": hostname,
    }
    RESOURCE_CPU_PERCENT.labels(**labels).set(cpu_percent)
    RESOURCE_MEMORY_MB.labels(**labels).set(memory_mb)
    RESOURCE_MEMORY_LIMIT_MB.labels(**labels).set(memory_limit_mb)
    RESOURCE_NET_BYTES_SENT.labels(**labels).set(net_bytes_sent)
    RESOURCE_NET_BYTES_RECV.labels(**labels).set(net_bytes_recv)
    RESOURCE_DISK_READ_BYTES.labels(**labels).set(disk_read_bytes)
    RESOURCE_DISK_WRITE_BYTES.labels(**labels).set(disk_write_bytes)
