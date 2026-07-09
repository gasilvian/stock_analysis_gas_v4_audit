FROM python:3.11-slim AS dashboard

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DASHBOARD_API_URL=http://api:8000 \
    DASHBOARD_TIMEOUT_SECONDS=30

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src
COPY dashboard ./dashboard
COPY config ./config
COPY schemas ./schemas
COPY validation ./validation

RUN python -m pip install --no-cache-dir -U pip \
    && python -m pip install --no-cache-dir -e ".[dashboard]"

EXPOSE 8501

CMD ["streamlit", "run", "dashboard/app.py", "--server.address=0.0.0.0", "--server.port=8501"]
