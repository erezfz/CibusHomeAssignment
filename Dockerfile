FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SERVER_HOST=0.0.0.0

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY config.py dependencies.py main.py migrate.py ps_client.py ./
COPY domains ./domains
COPY exceptions ./exceptions
COPY migrations ./migrations
COPY repositories ./repositories
COPY routes ./routes
COPY services ./services

CMD ["sh", "-c", "uvicorn main:app --host ${SERVER_HOST:-0.0.0.0} --port ${SERVER_PORT:-9000}"]
