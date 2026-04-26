"""
Trivy vulnerability scanner integration.
Runs `trivy image --format json <image>` as an async subprocess.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any
from uuid import UUID

from ..db.repository.scansRepo import ScansRepository
from ..db.session import get_session_factory
from ..db.dataAccessLayer import create_data_access_layer

logger = logging.getLogger(__name__)


class TrivyScanner:
    TIMEOUT_SECONDS = 300  # 5 minutes max

    async def run_scan(self, scan_id: UUID, image: str) -> None:
        """Run trivy on the given image and update the scan record with results."""
        session_factory = get_session_factory()
        async with session_factory() as session:
            dal = create_data_access_layer(session)
            try:
                vulnerabilities = await self._run_trivy(image)
                await dal.scans.update_scan_completed(
                    scan_id,
                    vulnerabilities=vulnerabilities,
                    status="completed",
                )
                logger.info("scan %s completed for image %s", scan_id, image)
            except asyncio.TimeoutError:
                await dal.scans.update_scan_failed(
                    scan_id, error_message=f"Scan timed out after {self.TIMEOUT_SECONDS}s"
                )
                logger.error("scan %s timed out", scan_id)
            except Exception as exc:
                await dal.scans.update_scan_failed(scan_id, error_message=str(exc))
                logger.exception("scan %s failed", scan_id)

    async def _run_trivy(self, image: str) -> Any:
        cmd = ["trivy", "image", "--format", "json", "--quiet", "--scanners", "vuln", image]
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise

        if proc.returncode != 0:
            err_text = stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"trivy exited with code {proc.returncode}: {err_text[:500]}")

        try:
            data = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"failed to parse trivy JSON output: {exc}") from exc

        return data


scanner = TrivyScanner()
