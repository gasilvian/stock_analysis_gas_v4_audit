# Security and internal access baseline

This project is an internal analytical prototype. Do not expose the API or dashboard publicly without a separate security review.

Minimum settings for a shared internal environment:

```bash
export SWS_API_AUTH_ENABLED=true
export SWS_API_KEY='<long-random-secret>'
export SWS_CORS_ORIGINS='http://localhost:8501,http://127.0.0.1:8501'
export DASHBOARD_API_KEY="$SWS_API_KEY"
```

Rules:

- Bind local-only unless there is a reviewed network boundary.
- Do not store real secrets in the repository.
- Keep database, cache and validation snapshots on persistent volumes.
- Keep the footer disclaimer and attribution visible in the dashboard.
- Live provider outputs are `yfinance_pragmatic`; missing data must stay visible as UNKNOWN/provider degradation.
