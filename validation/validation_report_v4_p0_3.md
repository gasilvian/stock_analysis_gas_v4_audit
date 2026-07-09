# Validation Report — v4.0 P0.3 SEC-first Financial Statements Foundation

## Scope implemented

Implemented the next controlled sprint after P0.2: **SEC-first Financial Statements Foundation**.

Implemented:

- `src/sws_engine/sec/` package.
- SEC CIK resolver for `company_tickers.json` and simplified ticker→CIK maps.
- SEC CompanyFacts adapter with offline cache/fixture-first behavior and optional live mode.
- Explicit XBRL tag resolver with declared candidate tags only.
- Normalized SEC statement snapshot builder.
- Capex sign normalizer for `capex_history_3y`.
- Initial bank-specific tag support for deposits / allowance fields where present in SEC facts.
- SEC mapping report JSON + Markdown renderer.
- CLI `refresh-sec-financials`.
- Recorded SEC fixtures for AAPL and JPM-like bank coverage under `tests/fixtures/sec/`.
- Tests under `tests/sec/` for CIK resolution, tag mapping, missing-tag UNKNOWN handling, bank partial mapping and CLI workflow.
- `docs/sec_mapping.md`.
- Backward-compatible `config/source_registry.yaml` extensions for `sec_companyfacts` and `sec_companyfacts_bank_tags`.

## Explicitly not implemented

This sprint does **not** implement:

- SEC live batch population as CI requirement.
- Full XBRL taxonomy coverage.
- SEC Frames API averages builder.
- Full `refresh-sec-financials` merge into engine payload execution.
- FRED/Treasury live loader.
- ERP curated workflow.
- full Identifier Master population.
- full source conflict detector runtime.
- sensitivity matrix.
- reverse DCF.
- red flag engine.
- accounting quality.
- capital allocation.
- watchlist audit.
- thesis tracker.
- decision journal.
- portfolio audit.
- memo generator.
- production-readiness PASS.
- complex dashboard pages.

## Preservation checks

- `schemas/output_schema.json` not modified.
- `src/sws_engine/checks/` not modified.
- `src/sws_engine/valuation/` not modified.
- `src/sws_engine/growth/` not modified.
- `src/sws_engine/portfolio/` not modified.
- `config/assumptions.yaml` not modified.
- No `score_normalized` runtime surface introduced.
- UNKNOWN policy preserved: missing CIKs and missing XBRL tags are reported as skipped / `XBRL_TAG_MISSING`, not inferred.
- SEC field lineage uses `source_id=sec_companyfacts`, `tier=official_filing`, `source_quality=exact`, `source_class=E0`.
- Production readiness remains `NOT_READY` until curated real-source files are populated.

## Tests run

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Result:

```text
163 passed, 2 skipped
```

SEC CLI smoke run:

```bash
PYTHONPATH=src python -m sws_engine.cli refresh-sec-financials \
  --tickers AAPL,JPM,NOPE \
  --output out/sec_ci \
  --cik-map tests/fixtures/sec/company_tickers.json \
  --companyfacts-dir tests/fixtures/sec/companyfacts \
  --valuation-date 2026-07-09
```

Result:

```text
PASS_WITH_LIMITATIONS; tickers_succeeded=2; tickers_failed=0; tickers_skipped=1
```

Governance gates run:

```bash
PYTHONPATH=src python scripts/ci/validate_demo_outputs.py
PYTHONPATH=src python scripts/ci/check_no_score_normalized.py
PYTHONPATH=src python scripts/ci/check_attribution_footer.py
PYTHONPATH=src python scripts/ci/check_real_source_population_workflow.py
PYTHONPATH=src python scripts/ci/check_audit_unknown_preserved.py out/audit_ci
PYTHONPATH=src python scripts/ci/check_source_registry_field_rules.py
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation and source-registry field rules.
Production readiness remains NOT_READY until curated real-source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. SEC mapping is a P0.3 foundation slice, not full XBRL taxonomy coverage.
2. Live SEC refresh is implemented as optional but not exercised in CI.
3. SEC snapshots are generated as auxiliary payload-updates artifacts; they do not yet run a full engine payload merge automatically.
4. Source conflict detection is still structural/limited; full runtime conflict resolution remains P1.
5. Production readiness remains blocked by curated source population, by design.
