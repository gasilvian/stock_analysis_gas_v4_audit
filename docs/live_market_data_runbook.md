# Live Market Data Runbook — Step A

## Purpose

Step A adds a yfinance live adapter that produces `provider_profile=yfinance_pragmatic` payloads. It does not change SWS model rules and it does not turn yfinance into a faithful SWS data provider.

## Basic commands

```bash
python -m sws_engine.cli build-payload-yfinance --ticker AAPL --market US --industry Technology --output data/inputs/AAPL_yfinance_payload.json
python -m sws_engine.cli company-live --ticker AAPL --market US --industry Technology --output out/AAPL_output.json --report out/AAPL_report.md
python -m sws_engine.cli record-yfinance --ticker AAPL --output data/recorded_yfinance/AAPL_snapshot.json --refresh
python -m sws_engine.cli provider-capability --provider yfinance --ticker AAPL --output out/AAPL_capability_report.md
```

## Interpreting UNKNOWN

`UNKNOWN` is lack of evaluability. It is not a neutral pass/fail. yfinance commonly lacks analyst estimates with analyst count, forward FCF estimates, AFFO/FFO/NAV, bank NPL/deposit/charge-off fields, and SWS-style market/industry averages.

## Manual overrides

Use templates under `templates/` to fill curated inputs. Keep lineage on each override. Only switch to `sws_public_faithful_manual_inputs` when curated/manual inputs cover the required fields and the run is intentionally faithful/manual.

## Recorded fixtures

Tests use `data/recorded_yfinance/*_snapshot.json` without network. Fixtures may be yfinance-shaped synthetic snapshots and must not be presented as live market data.
