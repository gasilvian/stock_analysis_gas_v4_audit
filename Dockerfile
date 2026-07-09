FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SWS_DB_PATH=/app/data/sws.db \
    SWS_ASSUMPTIONS_PATH=/app/config/assumptions.yaml \
    SWS_SCHEMA_PATH=/app/schemas/output_schema.json

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY config ./config
COPY schemas ./schemas
COPY data ./data
COPY validation ./validation

RUN python -m pip install --no-cache-dir -U pip \
    && python -m pip install --no-cache-dir -e ".[api,live]"

EXPOSE 8000

CMD ["uvicorn", "sws_engine.api.app:app", "--host", "0.0.0.0", "--port", "8000"]
