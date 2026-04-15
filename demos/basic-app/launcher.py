from __future__ import annotations

import signal
import subprocess
import sys
import time


CHILDREN: list[subprocess.Popen[str]] = []


def _stop_children(timeout_seconds: float = 10.0) -> None:
    for child in CHILDREN:
        if child.poll() is None:
            child.terminate()

    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if all(child.poll() is not None for child in CHILDREN):
            return
        time.sleep(0.2)

    for child in CHILDREN:
        if child.poll() is None:
            child.kill()


def _handle_signal(signum: int, _frame: object) -> None:
    _stop_children()
    raise SystemExit(128 + signum)


def main() -> int:
    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT, _handle_signal)

    app_proc = subprocess.Popen([sys.executable, "/app/app.py"], text=True)
    agent_proc = subprocess.Popen(["containerguard-agent"], text=True)
    CHILDREN.extend([app_proc, agent_proc])

    try:
        while True:
            for child in CHILDREN:
                return_code = child.poll()
                if return_code is not None:
                    _stop_children()
                    return return_code
            time.sleep(0.5)
    finally:
        _stop_children()


if __name__ == "__main__":
    raise SystemExit(main())
