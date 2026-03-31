# ContainerGuard

**Container Security Monitoring and Compliance Platform**

Course: COSC 6352 - Advanced Operating Systems, University of Houston
Professor: Bozhen Liu

ContainerGuard is a distributed monitoring platform that provides real-time visibility into container security posture. It consists of lightweight agents deployed inside containers, a central server that aggregates telemetry, a web dashboard for visualization, and a full observability stack (Prometheus, Grafana, Loki).

---

## Quick Start

### Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Docker Engine 24+ with Compose V2)
- Ports available: `3001`, `3002`, `3100`, `5432`, `8001`, `9090`

### Launch

```bash
docker compose up --build -d
```

This starts all 9 services. First run takes 2-3 minutes to pull images and build. Subsequent starts are faster.

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| **Dashboard** | http://localhost:3002 | React web UI |
| **Grafana** | http://localhost:3001 | Metrics + Logs (admin/admin) |
| **Server API** | http://localhost:8001 | FastAPI + Swagger docs at `/docs` |
| **Prometheus** | http://localhost:9090 | Metrics query UI |
| **Loki** | http://localhost:3100 | Log query API |
| **PostgreSQL** | localhost:5432 | DB (postgres/postgres/containerguard) |

### Stop

```bash
docker compose down
```

To also remove stored data (DB, metrics, logs):

```bash
docker compose down -v
```

---

## Architecture

```
                    ┌──────────────┐
                    │  Dashboard   │ :3002  (React + Nginx)
                    └──────┬───────┘
                           │ /api/* proxy
                           ▼
┌─────────┐       ┌────────────────┐       ┌────────────┐
│  Agent  │──────►│  Central Server│◄──────│  Heartbeat │
│ (sidecar│ HTTP  │   (FastAPI)    │       │  Monitor   │
│  per    │       │   :8001        │       └────────────┘
│container│       └───────┬────────┘
└─────────┘               │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        ┌──────────┐ ┌──────────┐ ┌──────┐
        │PostgreSQL│ │Prometheus│ │ Loki │
        │  :5432   │ │  :9090   │ │:3100 │
        └──────────┘ └────┬─────┘ └──┬───┘
                          │          │
                     ┌────▼──────────▼───┐
                     │     Grafana       │ :3001
                     └───────────────────┘
                              ▲
                     ┌────────┘
                     │
                ┌────┴────┐
                │Promtail │ (Docker log collector)
                └─────────┘
```

### Services (9 total)

| Service | Image | Role |
|---------|-------|------|
| **db** | `postgres:16` | Persistent state (agents, telemetry, alerts, compliance) |
| **migrate** | Built from `server/` | One-shot Alembic migration runner |
| **server** | Built from `server/` | FastAPI API gateway + WebSocket + Prometheus exporter |
| **heartbeat-monitor** | Built from `server/` | Independent worker that marks agents unreachable/offline |
| **agent** | Built from `agent/` | Collects container telemetry and pushes to server |
| **dashboard** | Built from `dashboard/` | React SPA served by Nginx with API reverse proxy |
| **prometheus** | `prom/prometheus` | Time-series metrics storage, scrapes server `/metrics/` |
| **loki** | `grafana/loki:3.4.2` | Log aggregation store |
| **promtail** | `grafana/promtail:3.4.2` | Collects Docker container logs, ships to Loki |
| **grafana** | `grafana/grafana` | Visualization for metrics (Prometheus) and logs (Loki) |

---

## Project Structure

```
containerguard/
├── docker-compose.yml              # Full stack orchestration (9 services)
│
├── agent/                          # Container Agent (Python)
│   ├── Dockerfile
│   ├── pyproject.toml              # httpx, psutil, pydantic-settings, watchdog
│   └── src/
│       ├── main.py                 # Entry point: registration, heartbeat, telemetry loops
│       ├── config.py               # Settings via env vars
│       ├── collectors/
│       │   ├── resources.py        # CPU, memory, disk, network I/O via psutil
│       │   ├── network.py          # Active TCP/UDP connections
│       │   ├── ports.py            # Listening ports with PID resolution
│       │   ├── filesystem.py       # File create/write/delete via watchdog
│       │   └── processes.py        # Running processes via psutil
│       └── transport/
│           └── client.py           # Async HTTP client for server communication
│
├── server/                         # Central Server (Python/FastAPI)
│   ├── Dockerfile
│   ├── pyproject.toml              # fastapi, sqlalchemy, asyncpg, prometheus_client, httpx
│   ├── gunicorn.conf.py            # Gunicorn + Uvicorn multi-worker config
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/               # Database migrations
│   │       ├── 20260320_0001_initial_schema.py
│   │       └── 20260327_0002_expand_telemetry_storage.py
│   └── src/
│       ├── main.py                 # FastAPI app, router registration, lifespan
│       ├── config.py               # pydantic-settings (PG_DSN, LOKI_URL, etc.)
│       ├── schemas.py              # Pydantic request/response models
│       ├── api/
│       │   ├── agents.py           # Agent CRUD + registration + heartbeat
│       │   ├── telemetry.py        # Telemetry ingest + per-agent + global queries
│       │   ├── logs.py             # Loki log proxy (query, labels, label values)
│       │   ├── websocket.py        # WebSocket broadcast for real-time dashboard
│       │   ├── alerts.py           # Alert endpoints (stub)
│       │   ├── compliance.py       # Compliance endpoints (stub)
│       │   └── scans.py            # Scan endpoints (stub)
│       ├── db/
│       │   ├── models.py           # 10 SQLAlchemy models
│       │   ├── session.py          # Async engine + session factory
│       │   ├── dataAccessLayer.py  # DAL with dependency injection
│       │   └── repository/
│       │       ├── agentsRepo.py   # Agent CRUD, status sync, heartbeat
│       │       └── telemetryRepo.py # Telemetry ingest, per-agent + global queries
│       ├── metrics/
│       │   └── exporter.py         # 15 Prometheus metrics (counters + gauges)
│       └── workers/
│           └── heartbeat_monitor.py # Marks stale agents unreachable/offline
│
├── dashboard/                      # Web Dashboard (React + TypeScript + Tailwind)
│   ├── Dockerfile                  # Multi-stage: Node build -> Nginx serve
│   ├── nginx.conf                  # Reverse proxy for API, WebSocket, logs
│   ├── package.json                # react, react-router-dom, recharts, tailwindcss
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx                 # Router: /, /agents, /agents/:id, /network, /logs
│       ├── api/
│       │   ├── client.ts           # REST API client (agents, telemetry, per-agent)
│       │   └── logs.ts             # Loki log query client
│       ├── hooks/
│       │   └── useWebSocket.ts     # WebSocket hook for real-time updates
│       ├── components/
│       │   ├── Sidebar.tsx         # Navigation sidebar
│       │   ├── StatusBadge.tsx     # Agent status badge (online/unreachable/offline)
│       │   └── LogViewer.tsx       # Terminal-style log viewer with filters
│       └── pages/
│           ├── Dashboard.tsx       # Overview: stat cards, top-N charts, agent table
│           ├── AgentList.tsx       # Searchable/filterable agent table
│           ├── AgentDetail.tsx     # Per-agent: charts, network, fs, procs, ports, logs
│           ├── NetworkView.tsx     # Global network activity table
│           └── Logs.tsx            # Global log viewer
│
├── prometheus/
│   └── prometheus.yml              # Scrape config targeting server:8000
│
├── loki/
│   └── loki-config.yml             # Filesystem storage, TSDB schema
│
├── promtail/
│   └── promtail-config.yml         # Docker SD, labels: container, service, project
│
├── grafana/
│   └── provisioning/
│       ├── datasources/
│       │   └── prometheus.yml      # Prometheus + Loki datasources
│       └── dashboards/
│           ├── dashboards.yml      # Dashboard provider config
│           └── container-guard.json # Pre-built dashboard (13 panels, 2 variables)
│
└── project-details.md              # Full system design document
```

---

## Dashboard Pages

### Overview (`/`)
Aggregate health across all agents:
- Stat cards: total agents, online/unreachable/offline counts, avg CPU, total memory
- Health distribution donut chart
- Top 10 CPU and memory consumers (clickable bar charts)
- Agent table with inline metrics (click any row to drill into agent detail)

### Agents (`/agents`)
Searchable, filterable agent list:
- Text search across hostname, image, container ID, IP
- Status filter buttons with counts
- Click any agent row to navigate to its detail page

### Agent Detail (`/agents/:id`)
Per-agent deep dive with 6 tabs:
- **Overview**: CPU, memory, network I/O, disk I/O time-series charts (live-updating via WebSocket)
- **Network**: Connection table (direction, IPs, port, protocol, bytes)
- **Filesystem**: File event table (create/write/delete, path, PID, process)
- **Processes**: Running process table (PID, command, user, start time)
- **Ports**: Listening ports (port, protocol, PID, process name)
- **Logs**: Container logs from Loki with text search and auto-refresh

### Network (`/network`)
Global network activity across all online agents.

### Logs (`/logs`)
Aggregated container logs from all services:
- Filter by service (agent, server, db, etc.)
- Filter by container name
- Filter by log level (error, warning, info, debug)
- Text search
- Auto-refresh toggle (5s interval)
- Terminal-style viewer with color-coded severity

---

## Grafana Dashboard

The pre-provisioned Grafana dashboard at http://localhost:3001 includes:

**Dropdown filters** (top of dashboard):
- **Agent** — select a specific agent hostname to filter all metric panels
- **Log Service** — select a specific service to filter the log panel

**Panels**:
- Agents Online / Total Agents / Telemetry Rate / Heartbeat Rate (stat)
- CPU Usage, Memory Usage, Network Sent/Recv, Disk Read/Write (time-series per agent)
- Network Events Rate, Filesystem Events Rate (time-series)
- Container Logs (Loki logs panel with service filter)

You can also use **Explore** (compass icon in sidebar) to run ad-hoc queries:
- Select **Prometheus** datasource for metric queries
- Select **Loki** datasource for log queries (e.g., `{service="agent"}`)

---

## API Reference

Base URL: `http://localhost:8001/api/v1`

Full interactive docs: http://localhost:8001/docs (Swagger UI)

### Agent Management
| Method | Path | Description |
|--------|------|-------------|
| POST | `/agents/register` | Register an agent |
| POST | `/agents/heartbeat` | Agent heartbeat |
| GET | `/agents/` | List all agents |
| GET | `/agents/{id}` | Get agent details |
| GET | `/agents/{id}/config` | Get agent config |
| DELETE | `/agents/{id}` | Deregister agent |

### Telemetry
| Method | Path | Description |
|--------|------|-------------|
| POST | `/telemetry` | Ingest telemetry batch |
| GET | `/telemetry/latest-resources` | Latest resource snapshot per agent |
| GET | `/telemetry/resources` | Resource snapshots (all online agents) |
| GET | `/telemetry/network` | Network events (all online agents) |
| GET | `/telemetry/filesystem` | Filesystem events (all online agents) |
| GET | `/telemetry/{agent_id}` | Raw telemetry for a single agent |
| GET | `/telemetry/{agent_id}/resources` | Resource history for one agent |
| GET | `/telemetry/{agent_id}/network` | Network events for one agent |
| GET | `/telemetry/{agent_id}/filesystem` | Filesystem events for one agent |
| GET | `/telemetry/{agent_id}/processes` | Process snapshots for one agent |
| GET | `/telemetry/{agent_id}/ports` | Port snapshots for one agent |

### Logs (Loki Proxy)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/logs/query?query={logql}` | Query logs from Loki |
| GET | `/logs/labels` | Available log label names |
| GET | `/logs/labels/{label}/values` | Values for a specific label |

### Metrics
| Method | Path | Description |
|--------|------|-------------|
| GET | `/metrics/` | Prometheus scrape endpoint |

### WebSocket
| Protocol | Path | Description |
|----------|------|-------------|
| WS | `/ws/dashboard` | Real-time telemetry broadcast |
| WS | `/ws/alerts` | Real-time alert broadcast |

---

## Database Schema

10 tables managed by Alembic migrations:

| Table | Purpose |
|-------|---------|
| `agents` | Registered agents with status and heartbeat tracking |
| `telemetry_events` | Raw telemetry batches (JSONB payload) |
| `network_events` | Parsed network connections |
| `filesystem_events` | File access events |
| `resource_snapshots` | CPU, memory, disk, network metrics |
| `port_snapshots` | Listening port snapshots |
| `process_snapshots` | Running process snapshots |
| `scan_results` | Vulnerability scan results |
| `compliance_rules` | Compliance rule definitions |
| `compliance_results` | Compliance evaluation results |
| `alerts` | Generated alerts |
| `alert_rules` | Alert threshold rules |

---

## Configuration

### Server Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PG_DSN` | (required) | PostgreSQL async DSN |
| `LOKI_URL` | (none) | Loki base URL for log proxy |
| `PROMETHEUS_MULTIPROC_DIR` | `/tmp/containerguard-prometheus` | Prometheus multiprocess dir |
| `WEB_CONCURRENCY` | `max(cpu_count, 2)` | Gunicorn worker count |
| `PORT` | `8000` | Gunicorn bind port |

### Agent Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_URL` | `http://containerguard-server:8000` | Central server URL |
| `CONTAINER_ID` | `$HOSTNAME` | Container identifier |
| `IMAGE` | `unknown` | Container image name |
| `TELEMETRY_INTERVAL_SECONDS` | `15` | Telemetry push interval |
| `HEARTBEAT_INTERVAL_SECONDS` | `5` | Heartbeat interval |
| `HTTP_TIMEOUT_SECONDS` | `10.0` | HTTP client timeout |
| `LOG_LEVEL` | `INFO` | Logging level |

---

## Development

### Running without Docker

**Server:**
```bash
cd server
pip install -e .
export PG_DSN=postgresql+asyncpg://postgres:postgres@localhost:5432/containerguard
alembic upgrade head
gunicorn -c gunicorn.conf.py src.main:app
```

**Agent:**
```bash
cd agent
pip install -e .
export SERVER_URL=http://localhost:8001
containerguard-agent
```

**Dashboard (dev mode with hot reload):**
```bash
cd dashboard
npm install
npm run dev
# Accessible at http://localhost:5173, proxies API to localhost:8001
```

### Adding a New Agent

To monitor an additional container, add another agent service in `docker-compose.yml`:

```yaml
  agent-redis:
    build:
      context: ./agent
    hostname: redis-cache
    depends_on:
      server:
        condition: service_started
    environment:
      SERVER_URL: http://containerguard-server:8000
      IMAGE: "redis:7"
      CONTAINER_ID: containerguard-agent-redis
```

### DB Verification

Connect via any PostgreSQL client:
- Host: `localhost:5432`
- Database: `containerguard`
- User: `postgres`
- Password: `postgres`

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Language | Python 3.12 |
| API Framework | FastAPI + Gunicorn + Uvicorn |
| ORM | SQLAlchemy 2.0 (async) + Alembic |
| Database | PostgreSQL 16 |
| Metrics | Prometheus + prometheus_client |
| Logs | Loki + Promtail |
| Visualization | Grafana |
| Frontend | React 18 + TypeScript + Tailwind CSS + Recharts |
| Real-time | WebSocket (native FastAPI) |
| Agent Monitoring | psutil, watchdog |
| HTTP Client | httpx (async) |
| Containerization | Docker + Docker Compose |
