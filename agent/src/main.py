from __future__ import annotations

import asyncio
import logging
from uuid import UUID

import psutil

from .collectors.filesystem import FilesystemCollector
from .collectors.network import collect as collect_network
from .collectors.ports import collect as collect_ports
from .collectors.processes import collect as collect_processes
from .collectors.resources import collect as collect_resources
from .config import Settings, get_settings
from .transport.client import AgentClient

logger = logging.getLogger(__name__)


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

            cycle += 1
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("telemetry push failed: %s", exc)
        await asyncio.sleep(settings.telemetry_interval_seconds)


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
            await asyncio.gather(heartbeat_task, telemetry_task)
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
