FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 NEWSALERT_HOME=/app
WORKDIR /app

COPY pyproject.toml README.md ./
COPY newsalert ./newsalert
RUN pip install --no-cache-dir . && useradd --system --home /app newsalert && mkdir -p /app/data && chown newsalert /app/data
COPY config ./config

USER newsalert
VOLUME ["/app/data"]
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 CMD ["newsalert", "healthcheck"]
CMD ["newsalert", "run"]
