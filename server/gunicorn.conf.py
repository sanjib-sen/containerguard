import multiprocessing
import os


bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
workers = int(os.getenv("WEB_CONCURRENCY", str(max(multiprocessing.cpu_count(), 2))))
worker_class = "uvicorn.workers.UvicornWorker"
accesslog = "-"
errorlog = "-"
graceful_timeout = 30
timeout = 30
keepalive = 30
