# ContainerGuard — Project Status

**Course:** COSC 6352 - Advanced Operating Systems
**University:** Texas A&M University-Corpus Christi
**Team:** [Sanjib](https://github.com/sanjib-sen), [Jackson](https://github.com/seethesaenz), Habib

A distributed container security monitoring & compliance platform. Lightweight Python agents run inside containers and stream telemetry to a FastAPI server, which evaluates threshold rules, anomaly detection, and compliance policies in real time. A React dashboard, Grafana, Prometheus, and Loki provide complete observability over metrics, alerts, and logs.

---

## Table of Contents

1. [Milestone Status](#milestone-status)
2. [Architecture](#architecture)
3. [Tech Stack & Packages](#tech-stack--packages)
4. [Ports & URLs](#ports--urls)
5. [Services (Docker Compose)](#services-docker-compose)
6. [Repository Layout](#repository-layout)
7. [Database Schema](#database-schema)
8. [API Reference](#api-reference)
9. [Latest Updates — Milestone 3](#latest-updates--milestone-3)
10. [How to Run](#how-to-run)
11. [How to Verify](#how-to-verify)
12. [Configuration](#configuration)

---

## Milestone Status

### ✅ Milestone 1 — Foundation
- System design document
- Project scaffolding (monorepo, Docker Compose)
- Agent: resource collector (CPU, memory, network I/O via psutil)
- Server: FastAPI skeleton, agent registration, heartbeat
- Database schema + migrations (Alembic)
- Agent → Server telemetry push
- Prometheus exporter

### ✅ Milestone 2 — Core Monitoring
- Agent: network connection tracker
- Agent: port scanner with PID resolution
- Agent: filesystem watcher (watchdog on `/etc`, `/var/log`, `/tmp`)
- Agent: process enumerator
- Server: telemetry storage in PostgreSQL (6 normalized tables)
- Server: REST API (global + per-agent endpoints)
- Server: WebSocket broadcast for real-time data
- Dashboard: Overview / Agents list / Agent detail / Network / Logs
- Grafana dashboard with per-agent dropdown filter

### ✅ Bonus — Log Infrastructure
- Loki log aggregation store
- Promtail auto-discovery of Docker container logs
- Server log proxy API (LogQL forwarding)
- Dashboard: Global log viewer with filters
- Grafana: Loki datasource + log panels

### ✅ Milestone 3 — Security Features (just completed)
- **Alert Manager** — threshold rules with Redis-based cooldowns
- **Anomaly Detection** — Z-score over rolling window in Redis
- **Compliance Engine** — JSON predicates (5 rule types)
- **Network Allowlist/Blocklist** — via compliance engine
- **Vulnerability Scanning** — Trivy integration
- **WebSocket Alert Broadcast** — via Redis pub/sub
- **Prometheus metrics** for alerts, compliance, scans
- **Dashboard UI** — Alerts, Alert Rules, Compliance, Scans pages
- **Sidebar live alert badge**
- **End-to-end test script** — 13 checks, all passing

### ⏳ Milestone 4 — Polish & Demo (remaining)
- Agent ring buffer for offline resilience
- Performance tuning and load testing
- Final project report

---

## Architecture

```
                          ┌────────────────────┐
                          │   Browser          │
                          └──────────┬─────────┘
                                     │
                          ┌──────────▼─────────┐
                          │  Dashboard (React) │  :3002
                          │  Nginx reverse     │
                          │  proxy /api, /ws   │
                          └──────────┬─────────┘
                                     │
┌─────────────────┐                  │
│  Agent (sidecar)│ HTTP             ▼
│  inside each    ├───────►  ┌──────────────────┐
│  workload       │ /telemetry │  FastAPI Server │  :8002
│  container      │ /heartbeat │  + Gunicorn 8wk│
└─────────────────┘ /register  │                 │
                               │  Engines:       │
                               │   • Alert       │
                               │   • Anomaly     │
                               │   • Compliance  │
                               │   • Trivy Scan  │
                               └────────┬────────┘
                                        │
       ┌─────────────────┬───────────────┼───────────────┬─────────────────┐
       ▼                 ▼               ▼               ▼                 ▼
  ┌─────────┐       ┌─────────┐    ┌─────────┐     ┌─────────┐       ┌─────────┐
  │PostgreSQL│      │  Redis  │    │Prometheus│    │  Loki   │       │ Grafana │
  │ :5432   │      │  pub/sub│    │  :9090  │     │  :3100  │       │  :3001  │
  └─────────┘      │ cooldown│    └────┬────┘     └────┬────┘       └────┬────┘
                   │ broker  │         │               ▲                 │
                   └─────────┘         │               │                 │
                                       │       ┌───────┴────────┐        │
                                       │       │  Promtail      │        │
                                       │       │  (Docker logs) │        │
                                       │       └────────────────┘        │
                                       └─────────────────────────────────┘
                                                     reads metrics + logs
```

### Key design choices

- **Sidecar pattern**: each workload container runs the agent alongside the app (using a launcher.py that supervises both), giving the agent full visibility into the container's process and network namespaces.
- **Multi-worker fan-out via Redis**: 8 Gunicorn workers each subscribe to Redis pub/sub channels. When any worker processes telemetry, alert broadcasts reach every WebSocket client regardless of which worker holds the connection.
- **Alert cooldowns in Redis**: atomic `SET ... NX EX cooldown_sec` ensures rules don't fire repeatedly during the suppression window, even across workers.
- **Anomaly state in Redis**: rolling window (sliding list of last 30 samples) per-agent per-metric, TTL'd to 30 minutes.
- **Engines run synchronously inside the telemetry POST** so alerts fire within milliseconds of the offending sample being recorded.

---

## Tech Stack & Packages

### Backend (Python 3.12)

| Package | Purpose |
|---------|---------|
| `fastapi` | API framework |
| `gunicorn` + `uvicorn` | Production ASGI multi-worker server |
| `sqlalchemy[asyncio]` | Async ORM |
| `asyncpg` | PostgreSQL async driver |
| `alembic` | Schema migrations |
| `pydantic` + `pydantic-settings` | Validation, env-based config |
| `redis>=5.0` | Async Redis client (pub/sub + cooldown state) |
| `httpx` | Async HTTP client (Loki proxy) |
| `prometheus_client` | Metrics in multi-process mode |
| `websockets` | WebSocket protocol |
| **System tools** | `trivy` (vulnerability scanner) installed in server image |

### Agent (Python 3.12)

| Package | Purpose |
|---------|---------|
| `httpx` | Async HTTP for server communication |
| `psutil` | CPU, memory, network, process collectors |
| `watchdog` | Filesystem event monitoring |
| `pydantic-settings` | Env-based config |
| **System tools** | `iproute2` (`ss` for port detection) |

### Frontend (Node 20)

| Package | Purpose |
|---------|---------|
| `react` 19 + `react-dom` | UI framework |
| `react-router-dom` | Client-side routing |
| `recharts` | Charts (line, bar, pie, area) |
| `tailwindcss` | Utility CSS |
| `vite` | Build tool |
| `@vitejs/plugin-react` | React plugin |
| `typescript` | Static typing |

### Infrastructure (images)

| Image | Role |
|-------|------|
| `postgres:16` | DB |
| `redis:7-alpine` | Pub/sub + cooldown state |
| `prom/prometheus:latest` | Metrics scraper / store |
| `grafana/loki:3.4.2` | Log store |
| `grafana/promtail:3.4.2` | Docker log collector |
| `grafana/grafana:latest` | Visualization |
| `nginx:alpine` | Dashboard SPA + reverse proxy |
| `python:3.12-slim` | Server / agent base |
| `node:20-slim` | Dashboard build stage |

---

## Ports & URLs

### Public-facing (host machine)

| Port | Service | URL | Notes |
|------|---------|-----|-------|
| **3001** | Grafana | http://localhost:3001 | admin / admin |
| **3002** | Dashboard | http://localhost:3002 | React UI |
| **3100** | Loki | http://localhost:3100 | LogQL HTTP API |
| **5432** | PostgreSQL | `localhost:5432` | postgres / postgres / containerguard |
| **8002** | Server API | http://localhost:8002 | Swagger at `/docs` |
| **8080** | Demo workload | http://localhost:8080 | If running `demos/web-api` |
| **8088** | basic-app demo | http://localhost:8088 | If running `docker-compose.demos.yml` |
| **9090** | Prometheus | http://localhost:9090 | PromQL UI |

### Internal (Docker network only)

| Service | Hostname | Port |
|---------|----------|------|
| `containerguard-server` | `containerguard-server` | 8000 |
| `containerguard-redis` | `redis` | 6379 |
| `containerguard-loki` | `loki` | 3100 |
| `containerguard-db` | `db` | 5432 |
| `containerguard-prometheus` | `prometheus` | 9090 |

---

## Services (Docker Compose)

### Main stack — `docker-compose.yml` (12 services)

**Platform:**
| Service | Image | Role |
|---------|-------|------|
| `db` | `postgres:16` | State store with healthcheck |
| `migrate` | built `./server` | One-shot Alembic migrator |
| `redis` | `redis:7-alpine` | Pub/sub + cooldowns |
| `server` | built `./server` | FastAPI + engines + Trivy + Docker socket |
| `heartbeat-monitor` | built `./server` | Marks stale agents unreachable/offline |
| `dashboard` | built `./dashboard` | React SPA via Nginx proxy |

**Observability:**
| Service | Image | Role |
|---------|-------|------|
| `prometheus` | `prom/prometheus:latest` | Scrapes server `/metrics/` |
| `loki` | `grafana/loki:3.4.2` | Log store |
| `promtail` | `grafana/promtail:3.4.2` | Auto-discovers Docker logs |
| `grafana` | `grafana/grafana:latest` | Pre-provisioned dashboard, Prometheus + Loki datasources |

**Demo workloads + agents:**
| Service | Hostname | Notes |
|---------|----------|-------|
| `agent` | `demo-standalone` | Standalone agent demo |
| `demo-web-api` | — | FastAPI service generating real telemetry |
| `agent-web-api` | `web-api` | Sidecar agent (shared PID + network ns) |
| `demo-worker` | — | Background worker (CPU, disk, network) |
| `agent-worker` | `bg-worker` | Sidecar agent for worker |

### Secondary stack — `docker-compose.demos.yml`

Optional demo workload: `basic-app` running app + agent in one container via `launcher.py`. Joins the main compose network as external.

---

## Repository Layout

```
os/
├── docker-compose.yml                # Main stack (12 services)
├── docker-compose.demos.yml          # Optional basic-app demo
├── readme.md                         # Quick start
├── project-details.md                # System design + milestones
├── PROJECT_STATUS.md                 # ← This file
│
├── agent/                            # Python agent
│   ├── Dockerfile
│   ├── pyproject.toml
│   └── src/
│       ├── main.py                   # Entry point + loops
│       ├── config.py                 # Settings via env vars
│       ├── collectors/
│       │   ├── resources.py          # CPU/mem/disk/net via psutil
│       │   ├── network.py            # Active connections
│       │   ├── ports.py              # Listening ports w/ ss fallback
│       │   ├── filesystem.py         # watchdog file events
│       │   └── processes.py          # Process enumeration
│       └── transport/
│           └── client.py             # Async HTTP to server
│
├── server/                           # Central server
│   ├── Dockerfile                    # Includes Trivy install
│   ├── pyproject.toml
│   ├── gunicorn.conf.py              # Multi-worker + Prometheus multiproc
│   ├── alembic/versions/
│   │   ├── 20260320_0001_initial_schema.py
│   │   ├── 20260327_0002_expand_telemetry_storage.py
│   │   └── 20260426_0003_security_features.py     ← M3 schema
│   └── src/
│       ├── main.py                   # FastAPI lifespan, engine startup
│       ├── config.py                 # Settings + Redis URL
│       ├── schemas.py                # Pydantic request/response models
│       ├── realtime.py               # Redis pub/sub broker
│       ├── api/
│       │   ├── agents.py             # Agent CRUD
│       │   ├── telemetry.py          # Ingest + queries + engine wiring
│       │   ├── alerts.py             # Alert + AlertRule CRUD
│       │   ├── compliance.py         # Compliance CRUD + status
│       │   ├── scans.py              # Trivy scans
│       │   ├── logs.py               # Loki proxy
│       │   └── websocket.py          # /ws/dashboard, /ws/alerts
│       ├── engines/                  ← M3
│       │   ├── alerts.py             # Threshold + cooldown engine
│       │   ├── anomaly.py            # Z-score detection
│       │   ├── compliance.py         # 5 predicate types
│       │   └── scanner.py            # Trivy subprocess
│       ├── db/
│       │   ├── models.py             # 12 SQLAlchemy models
│       │   ├── session.py
│       │   ├── dataAccessLayer.py    # DAL with all 5 repos
│       │   └── repository/
│       │       ├── agentsRepo.py
│       │       ├── telemetryRepo.py
│       │       ├── alertsRepo.py     ← M3
│       │       ├── complianceRepo.py ← M3
│       │       └── scansRepo.py      ← M3
│       ├── metrics/
│       │   └── exporter.py           # 19 Prometheus metrics
│       └── workers/
│           └── heartbeat_monitor.py
│
├── dashboard/                        # React + TypeScript + Tailwind
│   ├── Dockerfile                    # Multi-stage Node → Nginx
│   ├── nginx.conf                    # Proxies /api, /ws, /metrics
│   ├── vite.config.ts
│   ├── package.json
│   └── src/
│       ├── App.tsx                   # Router with 9 routes
│       ├── api/
│       │   ├── client.ts             # All REST endpoints typed
│       │   └── logs.ts               # Loki query helpers
│       ├── hooks/
│       │   └── useWebSocket.ts       # Generic typed hook
│       ├── components/
│       │   ├── Sidebar.tsx           # Live alert badge
│       │   ├── StatusBadge.tsx
│       │   └── LogViewer.tsx         # Terminal-style log panel
│       └── pages/
│           ├── Dashboard.tsx         # Overview
│           ├── AgentList.tsx
│           ├── AgentDetail.tsx       # 6-tab deep dive
│           ├── NetworkView.tsx
│           ├── Logs.tsx
│           ├── Alerts.tsx            ← M3
│           ├── AlertRules.tsx        ← M3
│           ├── Compliance.tsx        ← M3
│           └── Scans.tsx             ← M3
│
├── demos/
│   └── basic-app/                    # App + agent in one container
│       ├── app.py
│       ├── launcher.py               # Subprocess supervisor
│       └── Dockerfile
│
├── demo/                             # Sidecar-pattern demos (used by main compose)
│   ├── web-api/
│   └── worker/
│
├── prometheus/prometheus.yml         # Scrape config
├── loki/loki-config.yml              # TSDB store
├── promtail/promtail-config.yml      # Docker SD
├── grafana/provisioning/             # Datasources + auto-loaded dashboard
│
└── scripts/                          ← M3
    ├── e2e-security-test.sh          # 13-step E2E test
    ├── seed-rules.sh                 # Idempotent rule seeding
    └── seed-rules.py                 # Python implementation
```

---

## Database Schema

12 tables managed by 3 Alembic migrations.

| Table | Purpose |
|-------|---------|
| `agents` | Registered agents, status, heartbeat |
| `telemetry_events` | Raw telemetry batches (JSONB) |
| `network_events` | Parsed network connections |
| `filesystem_events` | File access events |
| `resource_snapshots` | CPU, memory, disk, network metrics |
| `port_snapshots` | Listening ports |
| `process_snapshots` | Running processes |
| `scan_results` | Trivy vulnerability scan results (with `started_at`, `completed_at`, `error_message`) |
| `compliance_rules` | Compliance rule definitions (JSON predicate) |
| `compliance_results` | Compliance evaluation results |
| `alerts` | Generated alerts (with `rule_id`, `alert_metadata`, `resolved_at`) |
| `alert_rules` | Alert threshold rules (with `name`, `description`) |

---

## API Reference

Base URL: `http://localhost:8002/api/v1` (Swagger: http://localhost:8002/docs)

### Agents
```
POST   /agents/register          { container_id, hostname, image, ip }
POST   /agents/heartbeat         { agent_id }
GET    /agents/                  → list all
GET    /agents/{id}              → details
GET    /agents/{id}/config       → poll agent config
DELETE /agents/{id}              → deregister
```

### Telemetry
```
POST   /telemetry                Telemetry batch ingest
GET    /telemetry/latest-resources         → latest snapshot per agent
GET    /telemetry/resources                → all online agents (windowed)
GET    /telemetry/network                  → all online agents
GET    /telemetry/filesystem               → all online agents
GET    /telemetry/{agent_id}               → raw events for one agent
GET    /telemetry/{agent_id}/resources
GET    /telemetry/{agent_id}/network
GET    /telemetry/{agent_id}/filesystem
GET    /telemetry/{agent_id}/processes
GET    /telemetry/{agent_id}/ports
```

### Alerts (Milestone 3)
```
GET    /alerts/                  → ?agent_id=&status=&severity=&limit=
GET    /alerts/{id}
PATCH  /alerts/{id}              { status: open | acknowledged | resolved }

GET    /alerts/rules/
POST   /alerts/rules/            Create alert rule
PATCH  /alerts/rules/{id}        Partial update
DELETE /alerts/rules/{id}
```

### Compliance (Milestone 3)
```
GET    /compliance/rules/
POST   /compliance/rules/        Create predicate rule
DELETE /compliance/rules/{id}

GET    /compliance/results/      → ?agent_id=&limit=
GET    /compliance/status/       → latest result per (agent, rule)
```

**Supported predicate types** (in `rule_json.type`):
- `no_root_processes` (with `allow_pids` exception list)
- `no_unauthorized_ports` (with `allowed_ports`)
- `no_sensitive_paths` (with `paths` list)
- `network_allowlist` (with `allowed_ips` and `allowed_cidrs`)
- `network_blocklist` (with `blocked_ips` and `blocked_cidrs`)

### Scans (Milestone 3)
```
POST   /scans/                   { image, agent_id? } → triggers Trivy
GET    /scans/                   → list (newest first)
GET    /scans/{id}
```

### Logs (Loki Proxy)
```
GET    /logs/query?query=&limit=&start=&end=&direction=
GET    /logs/labels
GET    /logs/labels/{label}/values
```

### WebSocket
```
WS     /ws/dashboard             Real-time telemetry broadcast
WS     /ws/alerts                Real-time alert broadcast
```

### Metrics
```
GET    /metrics/                 Prometheus scrape endpoint (19 metrics)
```

---

## Latest Updates — Milestone 3

### Security Engines

**Alert Engine (`server/src/engines/alerts.py`)**
- Threshold-based rule evaluation against telemetry resources
- 6 operators: `gt`, `ge`, `lt`, `le`, `eq`, `ne`
- 7 supported metrics: `cpu_pct`, `mem_mb`, `mem_pct`, `net_bytes_sent`, `net_bytes_recv`, `disk_read_bytes`, `disk_write_bytes`
- Cooldown via Redis `SET NX EX cooldown_sec` (atomic across all workers)
- `fire_custom()` method called by anomaly + compliance engines
- All alerts published to Redis channel for WebSocket fan-out

**Anomaly Engine (`server/src/engines/anomaly.py`)**
- Z-score detection: `|value - mean| > 2.5σ`
- Rolling window: 30 most recent samples in Redis list (TTL'd 30 min)
- Tracks `cpu_pct` and `mem_mb`
- Min 8 samples required before evaluating
- Severity escalates from `medium` to `high` for |z| > 4

**Compliance Engine (`server/src/engines/compliance.py`)**
5 predicate types:
| Type | Checks |
|------|--------|
| `no_root_processes` | Processes running as root (with PID allow-list) |
| `no_unauthorized_ports` | Ports outside the allowed list |
| `no_sensitive_paths` | Filesystem events on sensitive paths |
| `network_allowlist` | Outbound connections must match allowed IPs/CIDRs |
| `network_blocklist` | Outbound connections must NOT match blocked IPs/CIDRs |

**Trivy Scanner (`server/src/engines/scanner.py`)**
- Async subprocess: `trivy image --format json --quiet --scanners vuln <image>`
- 5-minute timeout, parses JSON output
- Stores full vulnerability tree in `scan_results.vulnerabilities_json`
- Uses Docker socket to scan local images

### Database Migration `20260426_0003_security_features.py`
- `alert_rules` + `name`, `description`
- `alerts` + `rule_id`, `alert_metadata` (JSONB), `resolved_at`
- `scan_results` + `started_at`, `completed_at`, `error_message`, `agent_id`

### Dashboard pages added

| Page | Route | Features |
|------|-------|----------|
| **Alerts** | `/alerts` | Filter by status/severity, expand for metadata, ack/resolve buttons, click-through to agent |
| **Alert Rules** | `/alerts/rules` | Full CRUD form (metric, operator, threshold, severity, cooldown), enable/disable toggle |
| **Compliance** | `/compliance` | 5 rule presets, JSON editor for custom rules, latest status per (agent, rule), expandable offender details |
| **Scans** | `/scans` | Trigger by image, severity-tagged CVE table with links to Trivy URLs |

### Sidebar live alert badge
- Polls `/alerts/?status=open` every 15s
- Increments on WebSocket `/ws/alerts` messages

### Prometheus metrics added
- `containerguard_alerts_fired_total{severity, rule_name}` — counter
- `containerguard_compliance_evaluations_total{status}` — counter
- `containerguard_scans_total{status}` — counter
- `containerguard_scan_vulnerabilities{image, severity}` — gauge

### Grafana panels added
- Alerts Fired rate (by severity)
- Compliance Evaluations rate (by status)
- Vulnerabilities by Image (bar gauge)
- Scans Total (stat)

### Scripts (`scripts/`)
- `seed-rules.sh` / `seed-rules.py` — seeds 4 alert rules + 3 compliance rules (idempotent)
- `e2e-security-test.sh` — 13 checks covering server health, alert rules CRUD, threshold firing, anomaly detection, compliance rules + evaluation, alert lifecycle, Trivy scanning

### Commits delivered for M3
```
c5883fe docs: document seed-rules + e2e test scripts in readme
3e79e14 fix: enrich alert metadata with hostname, configure root logger
c51313a feat: prometheus metrics for alerts, compliance, scans + grafana panels
26fb7db feat: add idempotent rule-seeding script for default alert/compliance rules
a8b7b35 test: add e2e security test script (13 checks)
fb8dfb5 feat: alert manager, anomaly detection, compliance engine, trivy scans + UI
```

---

## How to Run

### One-time setup
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Engine 24+ with Compose V2)
- Free ports: `3001`, `3002`, `3100`, `5432`, `8002`, `8080`, `9090`

### Start everything

```bash
cd /Users/sanjib/codes/academia/os
docker compose up --build -d
```

First run takes 2-3 minutes to pull/build images. Subsequent starts: ~30s.

### Seed default rules

```bash
bash scripts/seed-rules.sh
```

Creates 4 alert rules + 3 compliance rules (idempotent).

### Stop

```bash
docker compose down
```

To wipe persistent data (DB, metrics, logs):

```bash
docker compose down -v
```

### Component subsets

```bash
# Platform without demo workloads
docker compose up -d db migrate redis server heartbeat-monitor dashboard prometheus loki promtail grafana

# Add demos
docker compose up -d demo-web-api demo-worker agent-web-api agent-worker

# Just observability
docker compose up -d prometheus loki promtail grafana

# Optional basic-app demo (separate compose)
docker compose -f docker-compose.demos.yml up --build -d
```

---

## How to Verify

### 1. Run end-to-end test

```bash
bash scripts/e2e-security-test.sh
```

Should print **`ALL TESTS PASSED (13/13)`**.

### 2. Check the dashboard

http://localhost:3002

- **Overview**: 3 agents online, charts updating live
- **Alerts**: badge in sidebar, alerts auto-refresh every 5s, click to expand → ack/resolve buttons
- **Alert Rules**: see seeded rules, click "+ New Rule" to add one
- **Compliance**: 3 seeded rules, latest status appears within 15s of telemetry ingest
- **Scans**: enter `python:3.9-slim` and click Scan → expand result for CVE table

### 3. Check Grafana

http://localhost:3001 (admin / admin)

- **Agent** dropdown filters all metric panels
- **Log Service** dropdown filters log panel
- New panels: Alerts Fired (rate), Compliance Evaluations (rate), Vulnerabilities by Image

### 4. Verify WebSocket alert broadcast

```bash
python3 -c "
import asyncio, websockets, json
async def listen():
  async with websockets.connect('ws://localhost:8002/ws/alerts') as ws:
    async with asyncio.timeout(30):
      while True:
        msg = json.loads(await ws.recv())
        if msg.get('type') == 'alert':
          print(f'[{msg[\"severity\"]}] {msg[\"rule_name\"]} on {msg[\"hostname\"]}')
asyncio.run(listen())"
```

### 5. Verify Trivy scan

```bash
curl -X POST http://localhost:8002/api/v1/scans/ \
  -H "Content-Type: application/json" \
  -d '{"image": "alpine:3.14"}'
```

Wait ~60s, then:

```bash
curl -s http://localhost:8002/api/v1/scans/ | python3 -m json.tool
```

### 6. Quick health checks

```bash
# All containers running?
docker compose ps

# Server logs for engine startup
docker compose logs server | grep -E "alert engine|anomaly engine|broker"

# Agents registered?
curl -s http://localhost:8002/api/v1/agents/ | python3 -m json.tool

# Alerts firing?
curl -s "http://localhost:8002/api/v1/alerts/?limit=10" | python3 -m json.tool

# Prometheus metrics
curl -s http://localhost:8002/metrics/ | grep containerguard | head -20
```

---

## Configuration

### Server environment variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PG_DSN` | yes | — | PostgreSQL async DSN |
| `REDIS_URL` | yes | — | Redis URL for pub/sub + cooldowns |
| `LOKI_URL` | no | — | Loki URL for log proxy |
| `PROMETHEUS_MULTIPROC_DIR` | no | `/tmp/containerguard-prometheus` | Multi-process metrics dir |
| `WEB_CONCURRENCY` | no | `max(cpu_count, 2)` | Gunicorn worker count |
| `PORT` | no | `8000` | Bind port |

### Agent environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVER_URL` | `http://containerguard-server:8000` | Central server URL |
| `CONTAINER_ID` | `$HOSTNAME` | Container identifier |
| `HOSTNAME` | from OS | Display name |
| `IMAGE` | `unknown` | Container image |
| `TELEMETRY_INTERVAL_SECONDS` | `15` | Telemetry push interval |
| `HEARTBEAT_INTERVAL_SECONDS` | `5` | Heartbeat interval |
| `LOG_LEVEL` | `INFO` | Logging level |

### Alert engine tunables (in code)

- Cooldown bucket: `containerguard:alert:cooldown:{rule_id}:{agent_id}`
- Custom alert cooldown (anomaly/compliance): defaults vary (60s anomaly, 300s compliance)

### Anomaly engine tunables (`engines/anomaly.py`)

```python
TRACKED_METRICS = ("cpu_pct", "mem_mb")
WINDOW_SIZE = 30           # Last N samples
WINDOW_TTL_SEC = 1800      # 30 min
Z_THRESHOLD = 2.5          # Alert when |z| > 2.5
MIN_SAMPLES = 8            # Need at least N samples
```

---

## Troubleshooting

### Server won't start — Redis DNS errors

The server has a 10-attempt retry with 1.5s backoff for Redis connection on startup. If it still fails, check that the `redis` service is healthy: `docker compose ps redis`.

### Alerts not appearing in dashboard

1. Check engines started: `docker compose logs server | grep "alert engine"`
2. Verify a rule exists: `curl http://localhost:8002/api/v1/alerts/rules/`
3. Check alerts table directly: `curl http://localhost:8002/api/v1/alerts/`

### WebSocket disconnects

The dashboard has automatic reconnection (3s backoff) and a 30s keepalive ping.

### Trivy scan fails

The Trivy DB updates on first run — initial scan can take 60-90s. If it persistently fails:
```bash
docker compose exec server trivy --version
docker compose exec server trivy image --download-db-only
```

### Port 8001 conflict

Server was moved to **8002** because port 8001 conflicts with `vcom-tunnel` on macOS Docker. All references in this doc and Swagger use 8002.

---

## Summary

ContainerGuard is a complete, working container-security monitoring stack with:

- **3 monitored agents** demonstrating the sidecar pattern
- **12 microservices** orchestrated via Docker Compose
- **6 collectors** producing real telemetry (resources, network, ports, processes, filesystem, with watchdog)
- **4 security engines** evaluating telemetry in real time
- **5 dashboard pages** for security operations
- **19 Prometheus metrics** + **Grafana panels** for SRE-style monitoring
- **Loki + Promtail** for centralized container logs
- **Full observability** end-to-end — agent → server → DB / Redis / Prometheus / Loki → Grafana / Dashboard

All Milestone 1, 2, and 3 deliverables are complete and verified by an end-to-end automated test suite (13/13 passing).
