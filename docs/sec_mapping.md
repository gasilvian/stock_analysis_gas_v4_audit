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

## Payload merge and precedence (P1.3b)

The `{ticker}_sec_payload_updates.json` artifacts are now consumable:

- `build-payload-yfinance --sec-payload-updates PATH` merges one artifact
  into the freshly built payload;
- `real-dashboard-bootstrap --sec-dir DIR` looks up
  `{ticker}_sec_payload_updates.json` (directly or under `normalized/`) for
  every ticker and merges when present; absence is an honest no-op
  (`SEC_UPDATES_NOT_FOUND`).

Precedence, documented and enforced by `sws_engine.sec.payload_merge`:

1. SEC official filings (exact/E0/official_filing) replace provider
   (yfinance_pragmatic) values for the statement fields they cover.
2. Curated rates injection uses disjoint fields and is unaffected.
3. Manual operator overrides applied afterwards (the `merge-overrides` step)
   win over SEC — a deliberate operator decision outranks automation.
4. A SEC field with `source_quality=missing` or a null value never blanks or
   downgrades a present base value.

Conflict visibility: when the base payload carried a materially different
value (>0.5% relative for numerics), a record
`{field, base_value, base_provider, sec_value, relative_diff,
resolution=sec_precedence}` is appended to `payload.source_conflicts` and a
`SOURCE_CONFLICT_DETECTED` builder warning is emitted. Nothing is resolved
silently. `provider_profile` is intentionally preserved — per-field lineage,
not the profile, carries the official_filing truth, so yfinance degradation
on unenriched fields stays visible.

At check time, the `yfinance_pragmatic` profile honors the declared lineage
quality of trusted enrichment sources (`sec_companyfacts`, `curated_rates`,
`manual_override`); all other fields keep the blanket pragmatic
approximation. Confidence rises only as far as honesty allows: checks mixing
SEC and yfinance inputs stay approximation (worst-of-inputs), and the UNKNOWN
mass from missing analyst estimates / industry averages is untouched until
those curated sources exist (calibration backlog B3/B4).
