from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection

from ..config import get_settings
from ..db import create_data_access_layer, get_session_factory
from ..metrics.exporter import set_agent_counts


logger = logging.getLogger(__name__)
HEARTBEAT_MONITOR_LOCK_KEY = 6_352_001


async def _try_acquire_monitor_lock(connection: AsyncConnection) -> bool:
    return bool(
        await connection.scalar(
            text("SELECT pg_try_advisory_lock(:lock_key)"),
            {"lock_key": HEARTBEAT_MONITOR_LOCK_KEY},
        )
    )


async def _release_monitor_lock(connection: AsyncConnection) -> None:
    await connection.execute(
        text("SELECT pg_advisory_unlock(:lock_key)"),
        {"lock_key": HEARTBEAT_MONITOR_LOCK_KEY},
    )


async def run_heartbeat_monitor() -> None:
    settings = get_settings()

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
            async with get_session_factory()() as session:
                connection = await session.connection()
                if await _try_acquire_monitor_lock(connection):
                    dal = create_data_access_layer(session)
                    try:
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
                    finally:
                        await _release_monitor_lock(connection)
            await asyncio.sleep(monitor_interval)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("heartbeat monitor iteration failed")
            await asyncio.sleep(monitor_interval)
