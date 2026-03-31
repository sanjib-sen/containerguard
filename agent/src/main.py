from __future__ import annotations

import asyncio
import logging
import random
from uuid import UUID

import httpx
import psutil

from .collectors.filesystem import FilesystemCollector
from .collectors.network import collect as collect_network
from .collectors.ports import collect as collect_ports
from .collectors.processes import collect as collect_processes
from .collectors.resources import collect as collect_resources
from .config import Settings, get_settings
from .transport.client import AgentClient

logger = logging.getLogger(__name__)

# Simulated outbound targets for demo
DEMO_OUTBOUND_TARGETS = [
    ("https://api.github.com", "GitHub API health check"),
    ("https://registry.npmjs.org", "NPM registry probe"),
    ("https://pypi.org/simple/", "PyPI index check"),
    ("https://httpbin.org/get", "External API call"),
    ("https://ifconfig.me", "External IP lookup"),
]

SECURITY_EVENTS = [
    ("INFO", "security.scan", "Routine file integrity check passed"),
    ("INFO", "security.auth", "Service token refreshed successfully"),
    ("WARNING", "security.network", "Unusual outbound connection volume detected: {} connections in last interval"),
    ("INFO", "security.compliance", "Container resource usage within defined limits"),
    ("WARNING", "security.filesystem", "Sensitive path /etc/shadow was read by process pid={}"),
    ("INFO", "security.network", "DNS resolution completed: {} unique domains resolved"),
    ("INFO", "security.ports", "Open port scan complete: {} ports listening"),
    ("WARNING", "security.resource", "Memory usage at {}% of container limit"),
    ("INFO", "security.heartbeat", "Agent health check: all collectors operational"),
    ("ERROR", "security.network", "Connection to external endpoint timed out after 10s"),
]


async def register_with_retry(client: AgentClient, settings: Settings) -> UUID:
    backoff = [1, 2, 4, 8, 16, 30]
    attempt = 0
    while True:
        try:
            agent_id = await client.register()
            logger.info("registered as agent_id=%s", agent_id)
            return agent_id
        except Exception as exc:
            wait = backoff[min(attempt, len(backoff) - 1)]
            logger.warning(
                "registration failed (attempt %d): %s — retrying in %ds",
                attempt + 1,
                exc,
                wait,
            )
            await asyncio.sleep(wait)
            attempt += 1


async def heartbeat_loop(
    client: AgentClient, agent_id: UUID, settings: Settings
) -> None:
    while True:
        try:
            await client.heartbeat(agent_id)
            logger.debug("heartbeat sent")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("heartbeat failed: %s", exc)
        await asyncio.sleep(settings.heartbeat_interval_seconds)


async def telemetry_loop(
    client: AgentClient,
    agent_id: UUID,
    settings: Settings,
    fs_collector: FilesystemCollector,
) -> None:
    cycle = 0
    while True:
        try:
            resources = collect_resources()
            network = collect_network()
            ports = collect_ports()
            processes = collect_processes()
            fs_events = fs_collector.drain()

            await client.push_telemetry(
                agent_id,
                resources=resources,
                network=network,
                ports=ports,
                filesystem=fs_events,
                processes=processes,
            )

            logger.info(
                "telemetry batch #%d: cpu=%.1f%% mem=%.1f/%.1fMB net_conns=%d ports=%d procs=%d fs_events=%d",
                cycle,
                resources.cpu_percent,
                resources.memory_mb,
                resources.memory_limit_mb,
                len(network),
                len(ports),
                len(processes),
                len(fs_events),
            )

            # Emit a simulated security log every cycle
            _emit_security_log(resources, network, ports)

            cycle += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("telemetry push failed: %s", exc)
        await asyncio.sleep(settings.telemetry_interval_seconds)


async def demo_outbound_loop(settings: Settings) -> None:
    """Simulate periodic outbound network calls for demo visibility."""
    sec_logger = logging.getLogger("agent.network.outbound")
    async with httpx.AsyncClient(timeout=10.0) as client:
        while True:
            target_url, description = random.choice(DEMO_OUTBOUND_TARGETS)
            try:
                resp = await client.get(target_url)
                sec_logger.info(
                    "outbound request: %s -> %s [%d] %dB (%s)",
                    description,
                    target_url,
                    resp.status_code,
                    len(resp.content),
                    f"{resp.elapsed.total_seconds()*1000:.0f}ms",
                )
            except Exception as exc:
                sec_logger.warning(
                    "outbound request failed: %s -> %s (%s)",
                    description,
                    target_url,
                    exc,
                )
            # Random interval between 8-25 seconds
            await asyncio.sleep(random.uniform(8, 25))


def _emit_security_log(resources, network, ports) -> None:
    """Emit a random security-style log message with real data."""
    sec_logger = logging.getLogger("agent.security")
    level_str, category, template = random.choice(SECURITY_EVENTS)
    level = getattr(logging, level_str)

    # Fill in dynamic values
    if "{}" in template:
        if "connections" in template:
            msg = template.format(len(network))
        elif "ports" in template:
            msg = template.format(len(ports))
        elif "Memory" in template:
            pct = int((resources.memory_mb / resources.memory_limit_mb) * 100) if resources.memory_limit_mb > 0 else 0
            msg = template.format(pct)
        elif "pid" in template:
            msg = template.format(random.randint(1, 500))
        elif "domains" in template:
            msg = template.format(random.randint(2, 15))
        else:
            msg = template.format(random.randint(1, 100))
    else:
        msg = template

    sec_logger.log(level, "[%s] %s", category, msg)


async def main() -> None:
    settings = get_settings()

    logger.info("ContainerGuard agent starting up")
    logger.info("config: server=%s telemetry_interval=%ds heartbeat_interval=%ds",
                settings.server_url, settings.telemetry_interval_seconds, settings.heartbeat_interval_seconds)

    # Prime psutil cpu_percent so the first real reading is meaningful.
    psutil.cpu_percent(interval=0.1)

    loop = asyncio.get_running_loop()
    fs_collector = FilesystemCollector()
    fs_collector.start(loop)

    try:
        async with AgentClient(settings) as client:
            agent_id = await register_with_retry(client, settings)
            logger.info("agent online — starting telemetry collection")

            heartbeat_task = asyncio.create_task(heartbeat_loop(client, agent_id, settings))
            telemetry_task = asyncio.create_task(telemetry_loop(client, agent_id, settings, fs_collector))
            outbound_task = asyncio.create_task(demo_outbound_loop(settings))
            await asyncio.gather(heartbeat_task, telemetry_task, outbound_task)
    finally:
        fs_collector.stop()
        logger.info("agent shutting down")


def entrypoint() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    asyncio.run(main())


if __name__ == "__main__":
    entrypoint()
