FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends iproute2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

ENV PYTHONUNBUFFERED=1

COPY agent /tmp/containerguard-agent
RUN pip install --no-cache-dir /tmp/containerguard-agent

COPY demos/basic-app/app.py /app/app.py
COPY demos/basic-app/launcher.py /app/launcher.py

EXPOSE 8080

CMD ["python", "/app/launcher.py"]
