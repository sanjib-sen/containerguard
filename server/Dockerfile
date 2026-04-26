FROM python:3.12-slim

# Install trivy for vulnerability scans
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg \
    && curl -sfL https://aquasecurity.github.io/trivy-repo/deb/public.key | gpg --dearmor -o /usr/share/keyrings/trivy.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/trivy.gpg] https://aquasecurity.github.io/trivy-repo/deb generic main" > /etc/apt/sources.list.d/trivy.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends trivy \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PROMETHEUS_MULTIPROC_DIR=/tmp/containerguard-prometheus

COPY pyproject.toml readme.md alembic.ini gunicorn.conf.py ./
COPY alembic ./alembic
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "src.main:app"]
