# Scheduler and EOD refresh

Current operational command:

```bash
./ops/eod_refresh_real.sh YYYY-MM-DD
```

Environment variables:

- `SWS_DB_PATH` default `data/sws.db`
- `SWS_WATCHLIST` default `data/watchlists/watchlist_synthetic.csv`
- `SWS_UNIVERSE` default `data/universe/universe_US-SYN.csv`
- `SWS_MARKET` default `US-SYN`
- `SWS_PROVIDER_MODE` default `recorded`; optional `yfinance-live`
- `SWS_LOGS_DIR` default `logs`

Suggested cron for internal use:

```cron
30 20 * * 1-5 cd /path/to/sws-snowflake-engine && ./ops/eod_refresh_real.sh >> logs/cron_eod.log 2>&1
```

The EOD runner writes `logs/eod_refresh_<date>.json` and raises an alert in the
JSON report when more than 20% of tickers fail. This is intentionally simple so
it can run on a workstation or internal VM.

No public deployment is implied. Keep dashboard/API bound to localhost unless a
separate security review is completed.
