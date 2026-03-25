FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml readme.md alembic.ini gunicorn.conf.py ./
COPY alembic ./alembic
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8000

CMD ["gunicorn", "-c", "gunicorn.conf.py", "src.main:app"]
