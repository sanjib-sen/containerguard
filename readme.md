# ContainerGuard

ContainerGuard is a distributed container monitoring platform for real-time security visibility. It combines a lightweight in-container agent with a FastAPI backend, React dashboard, and an observability stack built on Prometheus, Grafana, and Loki.

Created for COSC 6352 - Advanced Operating Systems, Texas A&M University-Corpus Christi.

Developed by [sanjib](https://github.com/sanjib-sen), [Jackson](https://github.com/seethesaenz), and habib.

## Repo Layout

- `agent/` - Python agent and collectors
- `server/` - FastAPI API, database layer, migrations, metrics, and heartbeat worker
- `dashboard/` - React frontend
- `demos/basic-app/` - example workload with the app and agent in the same container
- `docker-compose.yml` - central stack
- `docker-compose.demos.yml` - demo workloads
- `prometheus/`, `loki/`, `promtail/`, `grafana/` - observability configuration

## Architecture

- The main stack runs PostgreSQL, Redis, migrations, the API server, the heartbeat worker, the dashboard, Prometheus, Loki, Promtail, and Grafana.
- Agents are meant to run inside the workload container they monitor.
- Demo workloads are started separately from the central stack.

## Quick Start

Start the central stack:

```bash
docker compose up --build -d
```

Useful URLs:

- Dashboard: `http://localhost:3002`
- API docs: `http://localhost:8001/docs`
- Grafana: `http://localhost:3001`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`

Start the demo workloads:

```bash
docker compose -f docker-compose.demos.yml up --build -d
```

Demo app URLs:

- App: `http://localhost:8088`
- Write endpoint: `http://localhost:8088/write`

Stop everything:

```bash
docker compose -f docker-compose.demos.yml down
docker compose down
```

Use `docker compose down -v` if you also want to remove volumes.

The demo compose file expects the `containerguard_default` network created by the main compose file.

## Adding The Agent To Another Workload

Use `demos/basic-app/` as the template:

1. Install the agent from `agent/` into your workload image.
2. Start both your app and `containerguard-agent` from the same container entrypoint or launcher.
3. Set the required environment variables.

Minimum environment variables:

- `SERVER_URL`
- `CONTAINER_ID`
- `IMAGE`
- `TELEMETRY_INTERVAL_SECONDS`
- `HEARTBEAT_INTERVAL_SECONDS`

## Development

Server:

```bash
cd server
pip install -e .
$env:PG_DSN="postgresql+asyncpg://postgres:postgres@localhost:5432/containerguard"
$env:REDIS_URL="redis://localhost:6379/0"
alembic upgrade head
gunicorn -c gunicorn.conf.py src.main:app
```

The standalone server flow requires a local Redis instance.

Agent:

```bash
cd agent
pip install -e .
$env:SERVER_URL="http://localhost:8001"
containerguard-agent
```

Dashboard:

```bash
cd dashboard
npm install
npm run dev
```
