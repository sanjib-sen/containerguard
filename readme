# Container Guard

This project is for Advanced Operating Systems - COSC 6352 under guidance of Professor Bozhen Liu

## Features

### Near Real-Time Monitoring

Agents passes messages between server via rest API, API sends to frontend via WS

### Vulnerability Scanning

Trivy will be used for manual scans

### Compliance Checks

Standards and policies will be enforcibly via a structured frontend form

### Alerting and Reporting

Via the real-time connection between the server and client, there will be alerting and reporting for each agent connections

## Local Docker Stack

Start PostgreSQL and the server together:

```powershell
docker compose up --build
```

Endpoints:
- Server: `http://localhost:8001`
- Postgres: `localhost:5432`

The server uses the internal Docker hostname `db`, creates the `containerguard` database if it is missing, and then applies Alembic migrations on startup.
