## Central Server

FastAPI backend that receives agent telemetry, stores it in PostgreSQL, exposes Prometheus metrics, proxies Loki logs, and broadcasts real-time updates via WebSocket.

### Running with Docker Compose (recommended)

From the repo root:

```bash
docker compose up --build
```

This starts PostgreSQL, runs Alembic migrations, and starts the server with Gunicorn multi-worker.

### Running standalone

```bash
cd server
pip install -e .
export PG_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/containerguard
alembic upgrade head
gunicorn -c gunicorn.conf.py src.main:app
```

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
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
- **Heartbeat Monitor**: Runs as a separate container (not inside the API workers) to avoid lock/race conditions across workers
- **Migrations**: Run by a one-shot `migrate` service in Docker Compose before the server starts
- **WebSocket**: `/ws/dashboard` broadcasts telemetry on every ingest; `/ws/alerts` reserved for alert broadcast
