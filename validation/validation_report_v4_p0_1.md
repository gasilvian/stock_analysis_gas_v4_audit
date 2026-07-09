# Validation Report — v4.0 P0.1 Audit Layer Foundation

## Scope implemented

Implemented the first execution slice from `PLAN-Produs-Audit-Engine-v4.0_ACTUALIZAT.md`:

- `src/sws_engine/audit/` package.
- Data Confidence v1.
- Critical Missing Inputs Map.
- Model Applicability v1.
- Conclusion Risk v1.
- Audit Summary JSON.
- Audit Markdown Report.
- CLI `audit-company`.
- API endpoint `GET /companies/{ticker}/audit`.
- Minimal Company Audit dashboard panel.
- Auxiliary schemas under `schemas/aux/`.
- Governance script `scripts/ci/check_audit_unknown_preserved.py`.
- Tests under `tests/audit/` and `tests/api/test_api_audit.py`.
- Docs: `docs/product_strategy_v4.md`, `docs/audit_engine_principles.md`, `docs/audit_methodology.md`.

## Explicitly not implemented

Per P0.1 scope control, this branch does **not** implement:

- SEC CompanyFacts adapter.
- FRED/Treasury live loader.
- ERP curated workflow.
- full identifier master.
- source conflict detector.
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
- No `score_normalized` runtime surface introduced.
- UNKNOWN policy preserved and surfaced in JSON/Markdown audit artifacts.
- `yfinance_pragmatic` degradation is visible in Data Confidence and Audit Summary.
- Not investment advice footer included in audit report.

## Tests run

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Result:

```text
150 passed, 2 skipped
```

Governance gates run:

```bash
PYTHONPATH=src python scripts/ci/validate_demo_outputs.py
PYTHONPATH=src python scripts/ci/check_no_score_normalized.py
PYTHONPATH=src python scripts/ci/check_attribution_footer.py
PYTHONPATH=src python scripts/ci/check_real_source_population_workflow.py
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer, and real-source honesty workflow.
Production readiness remains NOT_READY until curated real-source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.1 audit logic is intentionally auxiliary and heuristic over existing outputs.
2. Audit artifacts are computed on demand; no persistent audit tables are added yet.
3. Data Confidence v1 uses check metadata and output coverage, not field-level source registry rules yet.
4. Model Applicability v1 uses payload/output heuristics and must be strengthened with Identifier Master in later phases.
5. Production-readiness is still blocked by curated source population, by design.
