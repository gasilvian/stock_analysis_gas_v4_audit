# Dashboard mock data

This directory is reserved for lightweight UI mock payloads. The dashboard is
implemented as a FastAPI client and should consume `/analyze/*`, `/latest`,
`/history`, `/checks`, `/screener` and governance endpoints instead of reading
engine or SQLite modules directly.
