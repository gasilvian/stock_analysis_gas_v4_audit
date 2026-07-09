# Real universe and averages runbook

The averages builder supports a fallback hierarchy:

1. industry + country
2. industry + region
3. industry + global
4. market

Use:

```bash
python -m sws_engine.cli validate-universe --universe data/universe/universe_US_template.csv --output out/universe_US_coverage.json
python -m sws_engine.cli build-averages --universe data/universe/universe_US_template.csv --market US --date YYYY-MM-DD --min-universe 10 --out-dir data/averages
```

The builder excludes rows where `kind` is one of: `etf`, `fund`, `dr`,
`secondary_listing`.

PB averages are calculated only when tangible book value can be reconstructed:

```text
TBV = total_assets - intangible_assets - total_liabilities
PB = price / (TBV / shares_outstanding)
```

If `intangible_assets` is missing, the row is excluded from PB aggregation; it is
not approximated from generic book value.

The template universe files are seed lists, not real average snapshots. Populate
metrics from recorded/live payloads or curated sources before using for real runs.
