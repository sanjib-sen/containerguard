## Backend

#### Docker Setup

docker build -t containerguard-server ./server
docker run --rm -p 8000:8000 -e PG_DSN=postgresql+asyncpg://postgres:postgres@host.docker.internal:5432/containerguard containerguard-server

Notes:

- `PG_DSN` is required. `DATABASE_URL` also works.
- Inside Docker, `localhost` means the server container, not your host machine.
- If PostgreSQL is running in another container, put both containers on the same Docker network and use the Postgres container name as the host.

Recommended local development flow from the repo root:

docker compose up --build

#### DB verification

for verification you can connect to the DB via DBeaver or alternative via, localhost:5432/containerguard postgres:postgres