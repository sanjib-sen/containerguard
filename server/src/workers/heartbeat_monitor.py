from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from ..config import get_settings
from ..db import create_data_access_layer, dispose_engine, get_session_factory
from ..metrics.exporter import set_agent_counts


logger = logging.getLogger(__name__)


async def run_heartbeat_monitor() -> None:
    settings = get_settings()
    session_factory = get_session_factory()

    # Guard against invalid config that would make "offline" less stale than "unreachable".
    offline_after_seconds = max(
        settings.heartbeat_offline_after_seconds,
        settings.heartbeat_unreachable_after_seconds,
    )

    monitor_interval = settings.heartbeat_monitor_interval_seconds
    unreachable_after = timedelta(seconds=max(settings.heartbeat_unreachable_after_seconds, 1))
    offline_after = timedelta(seconds=offline_after_seconds)

    while True:
        try:
            async with session_factory() as session:
                dal = create_data_access_layer(session)
                sync_result = await dal.agents.sync_statuses(
                    unreachable_after=unreachable_after,
                    offline_after=offline_after,
                )
                set_agent_counts(
                    total=sync_result.total_agents,
                    online=sync_result.online_agents,
                )
                if sync_result.marked_unreachable or sync_result.marked_offline:
                    logger.info(
                        "heartbeat monitor updated agent states: unreachable=%s offline=%s",
                        sync_result.marked_unreachable,
                        sync_result.marked_offline,
                    )
            await asyncio.sleep(monitor_interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("heartbeat monitor iteration failed")
            await asyncio.sleep(monitor_interval)


async def _main() -> None:
    try:
        await run_heartbeat_monitor()
    finally:
        await dispose_engine()


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    asyncio.run(_main())


if __name__ == "__main__":
    main()
