# Container Security Monitoring and Compliance Platform (ContainerGuard)

## Course: COSC 6352 - Advanced Operating Systems

---

## 1. Project Overview

### Problem Statement
Containerized applications are increasingly deployed in production but lack unified visibility into their runtime security posture. Administrators need real-time insight into network traffic, port exposure, file system access, resource consumption, and vulnerability status across all running containers -- from a single pane of glass.

### What We Are Building
A **distributed monitoring platform** consisting of:
- A **lightweight agent** deployed as a sidecar or injected into each container that collects security telemetry (network I/O, open ports, file access, CPU/memory/network usage)
- A **central server** that aggregates telemetry, runs compliance checks, triggers vulnerability scans, and manages alerts
- A **web dashboard** for real-time visualization of all container security data
- A **Prometheus exporter** for all metrics, with Grafana integration

### Real-World Target
Analogous to commercial tools like Sysdig Secure, Falco, and Datadog Container Monitoring -- but purpose-built, lightweight, and fully open-source.

---

## 2. System Model & Assumptions

### Distributed System Type
- **Centralized architecture** with a single control-plane server and multiple distributed agents (one per monitored container)
- Agents are **stateless collectors** -- they push telemetry to the server and can restart without data loss

### Failure Model
- **Crash-failure model** (no Byzantine faults) -- agents and server may crash but do not act maliciously
- If an agent crashes, the server detects it via missed heartbeats and marks the container as "unreachable"
- If the server crashes, agents buffer telemetry locally (bounded ring buffer) and replay on reconnection

### Network Assumptions
- **Reliable network** within a Docker network (containers on the same host or Docker Swarm/overlay network)
- Communication over TCP (HTTP/WebSocket) -- retries with exponential backoff handle transient failures

### Consistency Model
- **Eventual consistency** for metrics and telemetry (acceptable lag of 1-5 seconds)
- **Strong consistency** for compliance state and alert acknowledgments (via PostgreSQL transactions)

---

## 3. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Host Machine / Docker Host               │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │Container1│  │Container2│  │Container3│   ...                 │
│  │┌────────┐│  │┌────────┐│  │┌────────┐│                      │
│  ││ Agent  ││  ││ Agent  ││  ││ Agent  ││                      │
│  │└───┬────┘│  │└───┬────┘│  │└───┬────┘│                      │
│  └────┼─────┘  └────┼─────┘  └────┼─────┘                      │
│       │              │              │                            │
│       └──────────────┼──────────────┘                            │
│                      │  HTTP REST + WebSocket                    │
│                      ▼                                           │
│  ┌─────────────────────────────────────────────┐                │
│  │           Central Server (FastAPI)           │                │
│  │                                              │                │
│  │  ┌────────────┐ ┌───────────┐ ┌───────────┐ │                │
│  │  │ Telemetry  │ │Compliance │ │  Vuln     │ │                │
│  │  │ Collector  │ │  Engine   │ │  Scanner  │ │                │
│  │  └─────┬──────┘ └─────┬─────┘ └─────┬─────┘ │                │
│  │        │              │              │       │                │
│  │  ┌─────▼──────────────▼──────────────▼─────┐ │                │
│  │  │          Event Bus (Redis Pub/Sub)      │ │                │
│  │  └─────┬──────────────┬──────────────┬─────┘ │                │
│  │        │              │              │       │                │
│  │  ┌─────▼──────┐ ┌────▼─────┐ ┌──────▼─────┐ │                │
│  │  │ Alert      │ │ Metrics  │ │  WebSocket │ │                │
│  │  │ Manager    │ │ Exporter │ │  Broadcaster│ │                │
│  │  └────────────┘ └──────────┘ └────────────┘ │                │
│  └──────────┬──────────┬──────────┬────────────┘                │
│             │          │          │                              │
│       ┌─────▼───┐ ┌───▼────┐ ┌──▼─────────┐                    │
│       │PostgreSQL│ │  Redis │ │ Prometheus  │                    │
│       │  (state) │ │(cache) │ │ (metrics)  │                    │
│       └─────────┘ └────────┘ └──────┬──────┘                    │
│                                     │                            │
│                              ┌──────▼──────┐                    │
│                              │   Grafana    │                    │
│                              └─────────────┘                    │
└─────────────────────────────────────────────────────────────────┘

         ┌─────────────────────────┐
         │   Web Dashboard (React) │  ◄── Browser
         └─────────────────────────┘
```

### Components

| Component | Role | Technology |
|-----------|------|------------|
| **Agent** | Collects container telemetry, pushes to server | Python, psutil, watchdog, socket |
| **Central Server** | API gateway, aggregation, orchestration | Python, FastAPI, SQLAlchemy |
| **Telemetry Collector** | Ingests and normalizes agent data | FastAPI endpoints + async workers |
| **Compliance Engine** | Evaluates rules against container state | Python rule engine (custom) |
| **Vulnerability Scanner** | Scans container images for CVEs | Trivy (CLI integration) |
| **Alert Manager** | Threshold-based alerting, notifications | Python + Redis Pub/Sub |
| **Metrics Exporter** | Exposes Prometheus /metrics endpoint | prometheus_client (Python) |
| **Web Dashboard** | Real-time UI for operators | React + TypeScript + TailwindCSS |
| **PostgreSQL** | Persistent state (events, alerts, compliance, config) | PostgreSQL 16 |
| **Redis** | Caching, pub/sub event bus, agent buffering | Redis 7 |
| **Prometheus** | Time-series metrics storage | Prometheus |
| **Grafana** | Metrics visualization and alerting | Grafana |

---

## 4. Tech Stack

| Layer | Technology | Justification |
|-------|-----------|---------------|
| **Language** | Python 3.12 | As specified; strong ecosystem for systems monitoring |
| **API Framework** | FastAPI | Async-native, high performance, auto OpenAPI docs |
| **ASGI Server** | Uvicorn + Gunicorn | Production-grade async server with worker management |
| **ORM** | SQLAlchemy 2.0 + Alembic | Industry standard ORM with async support; Alembic for migrations |
| **Database** | PostgreSQL 16 | ACID compliance for alerts/compliance state |
| **Cache / Pub-Sub** | Redis 7 | In-memory speed for real-time event bus and caching |
| **Metrics** | Prometheus + prometheus_client | De facto standard for metrics collection |
| **Dashboards** | Grafana | Native Prometheus integration, rich visualization |
| **Vuln Scanner** | Trivy | Industry-standard, open-source, scans images/filesystems |
| **Frontend** | React 18 + TypeScript + TailwindCSS | Modern, component-based UI; rich real-time capabilities |
| **Real-time** | WebSocket (native FastAPI) | Push-based updates for live dashboard |
| **Containerization** | Docker + Docker Compose | Required -- the project monitors containers |
| **System Monitoring** | psutil | Cross-platform CPU/memory/disk/network metrics |
| **File Monitoring** | watchdog | Filesystem event monitoring via inotify |
| **Network Capture** | scapy + socket | Packet inspection and connection tracking |
| **Task Queue** | asyncio tasks + Redis | Background jobs (scans, compliance checks) |
| **Package Manager** | uv | Fast Python package/project manager; replaces pip, venv, poetry |
| **Testing** | pytest + pytest-asyncio + httpx | Async-compatible testing |
| **Linting** | Ruff | Fast Python linter and formatter |

---

## 5. Agent Design (Per-Container)

The agent is a lightweight Python process (~15MB RAM) that runs inside each monitored container.

### Data Collection Modules

```
Agent Process
├── NetworkCollector      # Captures connections via /proc/net/tcp, /proc/net/udp + scapy
│   ├── Inbound requests (src IP, dst port, protocol, bytes)
│   ├── Outbound requests (dst IP, dst port, protocol, bytes)
│   └── DNS queries
├── PortCollector         # Enumerates listening ports via ss/netstat or /proc
│   └── Open ports + bound processes
├── FileCollector         # Watches filesystem via watchdog (inotify)
│   ├── File reads (path, process, timestamp)
│   └── File writes (path, process, timestamp)
├── ResourceCollector     # Reads cgroup stats + psutil
│   ├── CPU usage (%)
│   ├── Memory usage (RSS, cache, limit)
│   ├── Network I/O (bytes in/out, packets, errors)
│   └── Disk I/O (reads/writes, bytes)
├── ProcessCollector      # Enumerates running processes
│   └── PID, command, user, start time
└── Heartbeat             # Periodic liveness signal
```

### Agent Communication Protocol
- **Registration**: On startup, agent sends `POST /api/v1/agents/register` with container metadata (hostname, image, container ID, IP)
- **Telemetry Push**: Every **5 seconds**, agent sends `POST /api/v1/telemetry` with a batch of collected metrics
- **Heartbeat**: Every **10 seconds**, agent sends `POST /api/v1/agents/heartbeat`
- **Config Pull**: Agent polls `GET /api/v1/agents/{id}/config` every **60 seconds** for updated collection rules
- **Buffering**: If server is unreachable, agent stores up to **1000 telemetry records** in a local ring buffer and replays on reconnection

### Agent Data Format (JSON)
```json
{
  "agent_id": "container-abc123",
  "timestamp": "2026-02-22T10:30:00Z",
  "network": {
    "connections": [
      {"direction": "inbound", "src_ip": "10.0.0.5", "dst_port": 8080, "protocol": "tcp", "bytes": 1024}
    ],
    "dns_queries": [{"domain": "api.example.com", "resolved_ip": "93.184.216.34"}]
  },
  "ports": [{"port": 8080, "protocol": "tcp", "pid": 1, "process": "python"}],
  "filesystem": {
    "events": [
      {"type": "write", "path": "/etc/passwd", "pid": 42, "process": "bash", "timestamp": "..."}
    ]
  },
  "resources": {
    "cpu_percent": 23.5,
    "memory_mb": 128,
    "memory_limit_mb": 512,
    "net_bytes_sent": 50240,
    "net_bytes_recv": 102400,
    "disk_read_bytes": 4096,
    "disk_write_bytes": 8192
  },
  "processes": [
    {"pid": 1, "command": "python app.py", "user": "root", "started": "..."}
  ]
}
```

---

## 6. Central Server Design

### API Endpoints (FastAPI)

```
# Agent Management
POST   /api/v1/agents/register          # Agent registration
POST   /api/v1/agents/heartbeat         # Agent heartbeat
GET    /api/v1/agents                    # List all agents
GET    /api/v1/agents/{id}              # Get agent details
GET    /api/v1/agents/{id}/config       # Get agent config
DELETE /api/v1/agents/{id}              # Deregister agent

# Telemetry
POST   /api/v1/telemetry                # Ingest telemetry batch
GET    /api/v1/telemetry/{agent_id}     # Query telemetry for agent
GET    /api/v1/telemetry/network        # Network activity across all
GET    /api/v1/telemetry/filesystem     # File activity across all
GET    /api/v1/telemetry/resources      # Resource usage across all

# Vulnerability Scanning
POST   /api/v1/scans                    # Trigger scan for an image
GET    /api/v1/scans                    # List scan results
GET    /api/v1/scans/{id}              # Get scan details

# Compliance
GET    /api/v1/compliance/rules         # List compliance rules
POST   /api/v1/compliance/rules         # Create/update rule
GET    /api/v1/compliance/status        # Compliance status per container
POST   /api/v1/compliance/evaluate      # Trigger compliance check

# Alerts
GET    /api/v1/alerts                   # List alerts
PATCH  /api/v1/alerts/{id}             # Acknowledge/resolve alert
GET    /api/v1/alerts/rules             # Alert threshold rules
POST   /api/v1/alerts/rules             # Create alert rule

# WebSocket
WS     /ws/dashboard                    # Real-time dashboard feed
WS     /ws/alerts                       # Real-time alert feed

# Metrics
GET    /metrics                          # Prometheus scrape endpoint
```

### Database Schema (PostgreSQL)

```
agents           (id, container_id, hostname, image, ip, status, registered_at, last_heartbeat)
telemetry_events (id, agent_id, event_type, payload_json, created_at)   -- partitioned by time
network_events   (id, agent_id, direction, src_ip, dst_ip, port, protocol, bytes, timestamp)
filesystem_events(id, agent_id, event_type, path, pid, process_name, timestamp)
resource_snapshots(id, agent_id, cpu_pct, mem_mb, mem_limit, net_sent, net_recv, timestamp)
scan_results     (id, image_name, image_tag, vulnerabilities_json, scanned_at, status)
compliance_rules (id, name, description, rule_json, severity, enabled)
compliance_results(id, agent_id, rule_id, status, details, evaluated_at)
alerts           (id, agent_id, rule_name, severity, message, status, created_at, acknowledged_at)
alert_rules      (id, metric, operator, threshold, severity, cooldown_sec, enabled)
```

### Background Workers (asyncio)
- **Heartbeat Monitor**: Runs every 15s, marks agents as "unreachable" if heartbeat > 30s stale
- **Compliance Evaluator**: Runs every 60s, evaluates all rules against current agent state
- **Alert Processor**: Subscribes to Redis pub/sub, evaluates thresholds, creates alerts
- **Scan Scheduler**: Runs Trivy scans asynchronously via subprocess, stores results
- **Metric Updater**: Updates Prometheus gauges/counters from latest telemetry

---

## 7. Algorithms & Protocols

### Anomaly Detection (Resource Usage)
- **Sliding Window Average**: Maintain a 5-minute rolling average per metric per container
- **Z-Score Threshold**: Flag anomalies when current value deviates > 2 standard deviations from the rolling mean
- Configurable per metric (CPU, memory, network I/O)

### Network Security Rules
- **Allowlist/Blocklist**: Define allowed outbound destinations per container; alert on violations
- **Port Exposure Detection**: Alert when a container opens an unexpected port
- **Connection Rate Limiting**: Flag containers exceeding N connections/second

### Compliance Rule Engine
- Rules defined as JSON predicates evaluated against container state:
```json
{
  "name": "no-root-processes",
  "condition": "ALL processes.user != 'root'",
  "severity": "HIGH"
}
```
- Evaluated periodically and on telemetry events matching the rule scope

### Failure Handling
- **Agent -> Server**: Retry with exponential backoff (1s, 2s, 4s, 8s, max 30s)
- **Server -> Agent**: If heartbeat missed for 30s, mark unreachable; after 5 min, mark offline
- **Idempotent telemetry ingestion**: Each batch has a unique ID; server deduplicates

---

## 8. Concurrency / Parallel / Asynchronous / Distributed Design

### Inside Each Agent (Single Node)
- **asyncio event loop** drives all collectors concurrently
- Each collector (network, file, resource, process) runs as an **async task** within the loop
- **File monitoring** uses `watchdog` which runs a background **thread** (I/O bound); events are queued into the async loop via `asyncio.Queue`
- **Network capture** uses raw sockets in a separate **thread** (due to blocking recv); parsed packets enqueued to async queue
- **Synchronization**: `asyncio.Lock` protects the shared telemetry buffer; `asyncio.Queue` (thread-safe) bridges threads to the async loop
- **Batching**: A dedicated coroutine drains the queue every 5s and sends a single HTTP request

### Inside the Central Server (Single Node)
- **FastAPI + Uvicorn**: async request handling via ASGI; multiple worker processes via Gunicorn (1 worker per CPU core)
- **Background tasks**: `asyncio.create_task` for non-blocking work (compliance eval, scan dispatch)
- **Redis Pub/Sub**: Decouples telemetry ingestion from alert processing and WebSocket broadcast -- enables horizontal scaling later
- **Database connection pool**: SQLAlchemy async session with pool size matching worker count
- **WebSocket fan-out**: Single Redis subscription, one coroutine per connected client

### Across the Distributed System
- **Agents are independent**: No inter-agent communication; each pushes to the central server
- **Load distribution**: Natural -- each agent handles only its own container's telemetry
- **Server scalability**: Multiple Uvicorn workers share the same Redis and PostgreSQL; stateless request handling allows adding more server instances behind a load balancer
- **Scheduling**: Agents self-schedule their collection intervals; server schedules compliance/scan jobs via asyncio timers

---

## 9. Project Structure

```
container-guard/
├── docker-compose.yml              # Full stack orchestration
├── docker-compose.dev.yml          # Dev overrides
│
├── agent/                          # Container Agent
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                 # Agent entry point
│   │   ├── config.py               # Agent configuration
│   │   ├── collectors/
│   │   │   ├── __init__.py
│   │   │   ├── network.py          # Network connection tracking
│   │   │   ├── ports.py            # Open port enumeration
│   │   │   ├── filesystem.py       # File access monitoring
│   │   │   ├── resources.py        # CPU/memory/disk/net stats
│   │   │   └── processes.py        # Process enumeration
│   │   ├── transport/
│   │   │   ├── __init__.py
│   │   │   ├── client.py           # HTTP client to central server
│   │   │   └── buffer.py           # Ring buffer for offline mode
│   │   └── models.py               # Data models (Pydantic)
│   └── tests/
│
├── server/                         # Central Server
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic/                    # Database migrations
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Server configuration
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py           # Agent management endpoints
│   │   │   ├── telemetry.py        # Telemetry ingestion + query
│   │   │   ├── scans.py            # Vulnerability scan endpoints
│   │   │   ├── compliance.py       # Compliance endpoints
│   │   │   ├── alerts.py           # Alert endpoints
│   │   │   └── websocket.py        # WebSocket handlers
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── compliance_engine.py
│   │   │   ├── alert_manager.py
│   │   │   ├── scanner.py          # Trivy integration
│   │   │   └── anomaly.py          # Anomaly detection logic
│   │   ├── db/
│   │   │   ├── __init__.py
│   │   │   ├── models.py           # SQLAlchemy models
│   │   │   ├── session.py          # Async session factory
│   │   │   └── repositories.py     # Data access layer
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── heartbeat_monitor.py
│   │   │   ├── compliance_evaluator.py
│   │   │   ├── alert_processor.py
│   │   │   └── metric_updater.py
│   │   ├── metrics/
│   │   │   ├── __init__.py
│   │   │   └── exporter.py         # Prometheus metrics
│   │   └── schemas.py              # Pydantic request/response models
│   └── tests/
│
├── dashboard/                      # Web Dashboard
│   ├── Dockerfile
│   ├── package.json
│   ├── src/
│   │   ├── App.tsx
│   │   ├── pages/
│   │   │   ├── Dashboard.tsx       # Overview with all containers
│   │   │   ├── ContainerDetail.tsx  # Single container deep-dive
│   │   │   ├── NetworkView.tsx     # Network traffic visualization
│   │   │   ├── Alerts.tsx          # Alert list and management
│   │   │   ├── Compliance.tsx      # Compliance status
│   │   │   └── Scans.tsx           # Vulnerability scan results
│   │   ├── components/
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts     # WebSocket connection hook
│   │   └── api/
│   │       └── client.ts           # API client
│   └── tailwind.config.js
│
├── grafana/
│   ├── provisioning/
│   │   ├── dashboards/
│   │   │   └── container-guard.json
│   │   └── datasources/
│   │       └── prometheus.yml
│   └── Dockerfile
│
├── prometheus/
│   └── prometheus.yml              # Scrape config
│
└── demo/                           # Demo containers for testing
    ├── Dockerfile.web              # Sample web app container
    ├── Dockerfile.api              # Sample API container
    └── docker-compose.demo.yml     # Spins up demo workloads
```

---

## 10. Implementation Plan & Milestones

### Milestone 1: Foundation (Weeks 1-3) -- Proposal Checkpoint
- [x] System design document
- [ ] Project scaffolding (monorepo, Docker Compose, CI)
- [ ] Agent: resource collector (CPU, memory, network I/O via psutil)
- [x] Server: FastAPI skeleton, agent registration, heartbeat
- [x] Database schema + migrations (Alembic)
- [ ] Agent -> Server telemetry push (basic)
- [ ] Prometheus exporter with basic metrics
- **Deliverable**: Agent reports CPU/memory to server; visible in Prometheus

### Milestone 2: Core Monitoring (Weeks 4-6) -- Midterm Checkpoint
- [ ] Agent: network connection tracker (inbound/outbound)
- [ ] Agent: port scanner (open ports)
- [ ] Agent: file access monitor (watchdog)
- [ ] Agent: process enumerator
- [x] Server: telemetry storage in PostgreSQL
- [ ] Server: REST API for querying telemetry
- [ ] Server: WebSocket broadcast for real-time data
- [ ] Dashboard: basic container list + resource charts
- [ ] Grafana dashboard with all metrics
- **Deliverable**: Full telemetry pipeline working; live dashboard

### Milestone 3: Security Features (Weeks 7-9)
- [ ] Vulnerability scanning via Trivy integration
- [ ] Compliance rule engine + evaluation
- [ ] Alert manager with threshold rules
- [ ] Network allowlist/blocklist enforcement
- [ ] Anomaly detection (Z-score on resource metrics)
- **Deliverable**: Scan an image, evaluate compliance, trigger alerts

### Milestone 4: Polish & Demo (Weeks 10-12) -- Final Demo
- [ ] Dashboard: full UI (network view, alerts, compliance, scans)
- [ ] Agent ring buffer for offline resilience
- [ ] Demo scenario: deploy vulnerable containers, show detection
- [ ] Performance tuning and load testing
- [ ] Documentation and project report
- **Deliverable**: End-to-end demo with multiple containers

---

## 11. Evaluation Plan

### Correctness Tests
- **Unit tests**: Each collector module, compliance engine, alert manager
- **Integration tests**: Agent -> Server telemetry pipeline end-to-end
- **Manual fault injection**: Kill agents, kill server, verify recovery behavior

### Demo Scenarios
1. **Unauthorized file access**: A process writes to `/etc/shadow` inside a container -> alert fires within 5 seconds
2. **Port exposure**: A container opens an unexpected port -> dashboard shows it in real-time
3. **Resource anomaly**: Simulate CPU spike (stress-ng) -> anomaly detection triggers alert
4. **Vulnerable image**: Scan a known-vulnerable image -> CVE report shown in dashboard
5. **Network violation**: Container makes an outbound request to a blocked IP -> alert + logged
6. **Agent failure**: Kill an agent -> server marks container "unreachable" within 30 seconds
7. **Server failure**: Stop server -> agents buffer locally; restart server -> buffered data replays

### Performance Metrics
- **Telemetry latency**: Time from event at container to visibility on dashboard (target: < 3 seconds)
- **Agent overhead**: CPU and memory consumed by the agent itself (target: < 2% CPU, < 30MB RAM)
- **Server throughput**: Number of agents supported by a single server instance (target: 50+ containers)

---

## 12. Challenges & Difficulties

| Challenge | Mitigation |
|-----------|------------|
| **Race conditions** in concurrent collectors sharing the telemetry buffer | Use `asyncio.Lock` for the shared buffer; `asyncio.Queue` for thread-to-async bridge |
| **Agent overhead** impacting the monitored container's performance | Configurable collection intervals; efficient polling via /proc instead of spawning commands |
| **Telemetry data volume** overwhelming the server at scale | Batching (5s windows), server-side sampling, PostgreSQL table partitioning by time |
| **Clock skew** between agents and server causing event ordering issues | All timestamps are UTC; server applies its own receipt timestamp; events ordered by server time |
| **Network capture inside containers** requires elevated privileges | Agent container runs with `NET_RAW` and `SYS_PTRACE` capabilities; documented in security model |
| **Trivy scan duration** blocking the API | Scans run as async subprocess tasks; results polled/streamed via WebSocket |
| **WebSocket connection management** under high client count | Use Redis Pub/Sub as fan-out layer; each WebSocket handler subscribes to Redis, not directly to data pipeline |

---

## 13. Technology Constraints

- **Python** as the primary language for all backend components (as specified)
- **FastAPI** as the API framework for both agent and server
- All components run as **Docker containers** orchestrated via **Docker Compose**
- No Kubernetes dependency -- works on a single Docker host (can scale to Swarm later)
