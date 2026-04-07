## Central Server

FastAPI backend that receives agent telemetry, stores it in PostgreSQL, exposes Prometheus metrics, proxies Loki logs, and broadcasts real-time updates via WebSocket.

### Running with Docker Compose (recommended)

From the repo root:

```bash
docker compose up --build
```

This starts PostgreSQL, Redis, runs Alembic migrations, and starts the server with Gunicorn multi-worker.

### Running standalone

```bash
cd server
pip install -e .
export PG_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/containerguard
export REDIS_URL=redis://localhost:6379/0
alembic upgrade head
gunicorn -c gunicorn.conf.py src.main:app
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes for multi-worker fan-out | none | Redis URL for WebSocket pub/sub fan-out |
| `PG_DSN` | Yes | — | PostgreSQL async connection string |
| `LOKI_URL` | No | — | Loki URL for log proxy endpoints |
| `PROMETHEUS_MULTIPROC_DIR` | No | `/tmp/containerguard-prometheus` | Prometheus multiprocess dir |
| `WEB_CONCURRENCY` | No | `max(cpu_count, 2)` | Gunicorn worker count |
| `PORT` | No | `8000` | Bind port |

### API Docs

Interactive Swagger UI: http://localhost:8001/docs

### Database

- PostgreSQL 16, database `containerguard`
- Migrations managed by Alembic in `alembic/versions/`
- Connect for verification: `localhost:5432`, user `postgres`, password `postgres`

### Architecture Notes

- **Gunicorn + Uvicorn workers**: Multi-process for production; Prometheus multiprocess mode shares metrics via a shared volume
- **Redis Pub/Sub**: Every API worker subscribes to shared dashboard and alert channels, then fans those messages out to its own local WebSocket clients
- **Heartbeat Monitor**: Runs as a separate container (not inside the API workers) to avoid lock/race conditions across workers
- **Migrations**: Run by a one-shot `migrate` service in Docker Compose before the server starts
- **WebSocket**: `/ws/dashboard` publishes telemetry through Redis before fan-out; `/ws/alerts` is wired for the same pattern
