# ContainerGuard

ContainerGuard is a distributed monitoring platform that provides real-time visibility into container security posture. It consists of lightweight agents deployed inside containers, a central server that aggregates telemetry, a web dashboard for visualization, and a full observability stack (Prometheus, Grafana, Loki).

This project was created for COSC 6352 - Advanced Operating Systems, Texas A&M at Corpus Christi

Developed by:
[sanjib](https://github.com/sanjib-sen)
[Jackson](https://github.com/seethesaenz)
habib

The repo has four main parts:

- `agent/` - the Python agent
- `server/` - the FastAPI API, database layer, metrics, and heartbeat worker
- `dashboard/` - the React UI
- `demos/` - example workloads that run the app and the agent in the same container

## Deployment Model

The agent is meant to run inside the workload container it is monitoring.

The main compose file, `docker-compose.yml`, starts only the central stack:

- PostgreSQL
- Redis
- migration job
- API server
- heartbeat worker
- dashboard
- Prometheus
- Loki
- Promtail
- Grafana

Redis is used as the server's WebSocket fan-out layer so live dashboard updates work correctly with multiple Gunicorn workers.

Demo workloads live in a separate compose file, `docker-compose.demos.yml`.

## Repo Layout

- `agent/` - agent package and collectors
- `server/` - API server, DB models, migrations, worker
- `dashboard/` - frontend
- `demos/basic-app/` - example same-container workload
- `docker-compose.yml` - central stack
- `docker-compose.demos.yml` - demo workloads
- `prometheus/`, `loki/`, `promtail/`, `grafana/` - observability config

## Run The Central Stack

Start the server, dashboard, database, and observability services:

```bash
docker compose up --build -d
```

Useful URLs:

- Dashboard: `http://localhost:3002`
- API docs: `http://localhost:8001/docs`
- Grafana: `http://localhost:3001`
- Prometheus: `http://localhost:9090`
- Loki: `http://localhost:3100`

To stop it:

```bash
docker compose down
```

To remove volumes too:

```bash
docker compose down -v
```

## Run The Demo Workloads

After the central stack is up, start the demos:

```bash
docker compose -f docker-compose.demos.yml up --build -d
```

The sample `basic-app` demo will be available at:

- App: `http://localhost:8088`
- Write endpoint: `http://localhost:8088/write`

The `/write` endpoint is useful if you want to trigger a file write from the application side and then inspect the resulting logs and filesystem activity.

To stop the demos:

```bash
docker compose -f docker-compose.demos.yml down
```

The demo compose file expects the central stack network to be named `containerguard_default`, which is what the main compose file creates by default.

## Demo Pattern

The example in `demos/basic-app/` shows the intended pattern:

- `Dockerfile` installs the agent into the workload image
- `app.py` runs the sample HTTP service
- `launcher.py` starts both the app and `containerguard-agent` in the same container

This is the model to copy if you want the agent to observe the same container your application is actually running in.

## Add The Agent To Another Workload

Use `demos/basic-app/` as the template.

The general pattern is:

1. Build your workload image so it also installs the agent from `agent/`.
2. Start both your app and `containerguard-agent` from the same container entrypoint or launcher.
3. Set the agent environment variables in that workload container.

The minimum env vars you usually want are:

- `SERVER_URL` - where the workload should send telemetry
- `CONTAINER_ID` - a stable ID or name for the workload
- `IMAGE` - the workload image name
- `TELEMETRY_INTERVAL_SECONDS`
- `HEARTBEAT_INTERVAL_SECONDS`

A compose service typically looks like this:

```yaml
services:
  my-app:
    build:
      context: .
      dockerfile: Dockerfile
    environment:
      SERVER_URL: http://containerguard-server:8000
      CONTAINER_ID: my-app
      IMAGE: my-app:latest
      TELEMETRY_INTERVAL_SECONDS: 15
      HEARTBEAT_INTERVAL_SECONDS: 5
    ports:
      - "8080:8080"
```

The important part is that your `Dockerfile` and entrypoint follow the same pattern as `demos/basic-app/`

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

That standalone server flow also requires a reachable local Redis instance.

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

## Notes

- There is no standalone agent service in the main compose stack.
- The demos are started separately from the central stack.
- A same-container workload still includes both the app process and the agent process, so process and resource telemetry will include both.
- The project currently has stubs for alerts, scans, and compliance APIs.
- Promtail reads Docker logs from the Docker socket, so this setup is intended for a local Docker environment.
