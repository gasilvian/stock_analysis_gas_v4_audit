# SEC CompanyFacts Mapping — v4.0 P0.3

P0.3 adds a controlled SEC-first foundation. It maps a small explicit list of
CompanyFacts tags into an auxiliary SEC statement snapshot and payload-updates
artifact. The core v3.1 engine, checks, valuation, growth, portfolio logic and
`schemas/output_schema.json` remain unchanged.

## Rules

- No undeclared XBRL tag substitution.
- Missing tags are reported as `XBRL_TAG_MISSING` and remain UNKNOWN.
- Capex is normalized as absolute outflow for `capex_history_3y`.
- SEC field lineage uses `source_id=sec_companyfacts`, `tier=official_filing`,
  `source_quality=exact`, `source_class=E0`.
- Live SEC access is optional; tests run from recorded fixtures only.

## First CLI

```bash
python -m sws_engine.cli refresh-sec-financials \
  --tickers AAPL,MSFT \
  --output data/real_sources/sec \
  --cik-map data/real_sources/reference/sec_company_tickers.json \
  --companyfacts-dir data/real_sources/sec/raw/companyfacts
```

Use `--live` only for controlled personal/internal refreshes with a valid SEC
User-Agent. Do not use live access in CI.

## User-Agent requirement (P1.3a hardening)

SEC fair-access policy requires an identifiable User-Agent with a real
contact email. Live fetches now enforce this before any network activity:

- Provide it via `--user-agent "your-name your-app contact@your-domain"` or
  the `SWS_SEC_USER_AGENT` environment variable.
- There is no built-in default; a missing, contactless, or placeholder
  (`example.invalid`) User-Agent raises a clear error instead of silently
  violating the policy.
- Offline/cache/fixture reads never require a User-Agent.
- Transient SEC responses (429/5xx) are retried up to 3 times with
  exponential backoff (1s/2s/4s) on top of the polite pre-request sleep.
- Successful live fetches are cached on disk (`raw/companyfacts/`), so
  repeat runs read the cache unless `--refresh` is passed.
