import multiprocessing
import os
import shutil
import tempfile

from prometheus_client import multiprocess


PROMETHEUS_MULTIPROC_DIR = os.getenv(
    "PROMETHEUS_MULTIPROC_DIR",
    os.path.join(tempfile.gettempdir(), "containerguard-prometheus"),
)
os.environ["PROMETHEUS_MULTIPROC_DIR"] = PROMETHEUS_MULTIPROC_DIR


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", str(max(multiprocessing.cpu_count(), 2))))
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
errorlog = "-"
graceful_timeout = 30
timeout = 30
keepalive = 30


def on_starting(server):
    shutil.rmtree(PROMETHEUS_MULTIPROC_DIR, ignore_errors=True)
    os.makedirs(PROMETHEUS_MULTIPROC_DIR, exist_ok=True)
    server.log.info("initialized Prometheus multiprocess dir at %s", PROMETHEUS_MULTIPROC_DIR)


def child_exit(server, worker):
    multiprocess.mark_process_dead(worker.pid, path=PROMETHEUS_MULTIPROC_DIR)
