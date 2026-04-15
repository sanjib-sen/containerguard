from __future__ import annotations

import json
import logging
import os
import socket
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s basic-app %(message)s",
)
logger = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", "8080"))
TMP_DIR = Path("/tmp/basic-app")
REQUEST_LOG = TMP_DIR / "requests.log"


def _append_request_record(path: str) -> None:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    with REQUEST_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{datetime.now(timezone.utc).isoformat()} {path}\n")


class Handler(BaseHTTPRequestHandler):
    server_version = "ContainerGuardBasicApp/1.0"

    def _send_json(self, payload: dict[str, object], status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        _append_request_record(self.path)
        logger.info("handled GET %s", self.path)

        if self.path == "/health":
            self._send_json({"status": "ok"})
            return

        if self.path == "/write":
            marker = TMP_DIR / "manual-write.txt"
            marker.write_text(datetime.now(timezone.utc).isoformat(), encoding="utf-8")
            self._send_json({"status": "wrote", "path": str(marker)})
            return

        self._send_json(
            {
                "service": "basic-app",
                "status": "ok",
                "path": self.path,
                "pid": os.getpid(),
                "hostname": socket.gethostname(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    def log_message(self, format: str, *args: object) -> None:
        logger.info("%s - %s", self.address_string(), format % args)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    logger.info("basic app listening on port %s", PORT)
    server.serve_forever()


if __name__ == "__main__":
    main()
