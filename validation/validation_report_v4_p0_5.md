# Validation Report — v4.0 P0.5 Sensitivity and Valuation Range Foundation

## Scope implemented

Implemented the next controlled sprint after P0.4: **Sensitivity and Valuation Range Foundation**.

Implemented:

- `config/sensitivity.yaml` for auxiliary sensitivity policy, separate from `config/assumptions.yaml`.
- `schemas/aux/sensitivity_summary.schema.json` for additive sensitivity output validation direction.
- `src/sws_engine/sensitivity/` package:
  - `config.py`
  - `scenario_runner.py`
  - `terminal_value.py`
  - `fragility.py`
  - `reverse_dcf.py`
  - `report.py`
- CLI `sensitivity-company` for input-payload and persisted-run sensitivity analysis.
- API endpoint `GET /companies/{ticker}/sensitivity`.
- Markdown and JSON artifacts:
  - `*_sensitivity_summary_*.json`
  - `*_sensitivity_report_*.md`
- `docs/sensitivity_valuation_range.md`.
- Offline fixture `tests/fixtures/sensitivity/fcf_payload.json`.
- Tests under `tests/sensitivity/` for:
  - valuation range generation,
  - discount-rate × terminal-growth scenario matrix,
  - reverse DCF implied base growth,
  - terminal value contribution UNKNOWN handling,
  - manual fair-value sensitivity blocking,
  - CLI smoke execution.

## Explicitly not implemented

This sprint does **not** implement:

- Any modification to base valuation formulas.
- Any modification to checks, growth, scoring or portfolio modules.
- Automatic integration of sensitivity into base `output_schema.json`.
- Analyst-FCF reverse DCF.
- DDM reverse solve.
- excess-returns sensitivity.
- AFFO/REIT-specific sensitivity.
- SEC Frames API averages builder.
- FX loaders for ECB/BNR.
- Full source conflict detector runtime.
- red flag engine.
- accounting quality.
- capital allocation.
- watchlist audit.
- thesis tracker.
- decision journal.
- portfolio audit.
- memo generator.
- complex dashboard pages.
- production-readiness PASS.

## Preservation checks

- `schemas/output_schema.json` not modified.
- `src/sws_engine/checks/` not modified.
- `src/sws_engine/valuation/` not modified.
- `src/sws_engine/growth/` not modified.
- `src/sws_engine/portfolio/` not modified.
- `config/assumptions.yaml` not modified.
- No `score_normalized` runtime surface introduced.
- UNKNOWN policy preserved: if base valuation is manual or UNKNOWN, sensitivity returns `UNKNOWN` with explicit reason code.
- Sensitivity uses copied payloads and existing valuation resolver; it does not mutate base model assumptions.
- Reports include not-investment-advice footer.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke run

```bash
PYTHONPATH=src python -m sws_engine.cli sensitivity-company \
  --input tests/fixtures/sensitivity/fcf_payload.json \
  --output out/p05_ci \
  --sensitivity-config config/sensitivity.yaml
```

Result:

```text
PASS; ticker=SENS; reason_code=SENSITIVITY_COMPUTED; fragility_level=MEDIUM
```

Artifacts:

```text
out/p05_ci/SENS_sensitivity_summary_input.json
out/p05_ci/SENS_sensitivity_report_input.md
```

## Tests run

The full all-in-one pytest command was attempted but hit the sandbox wall-clock timeout before completion. Equivalent coverage was run in segmented offline groups:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/api tests/audit tests/averages_real tests/ci tests/contract tests/dashboard \
  tests/data_layer tests/deploy tests/docs tests/gold tests/governance tests/integration \
  tests/manual tests/ops tests/persistence tests/portfolio tests/providers tests/synthetic -q
```

Result:

```text
152 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/rates tests/reference tests/sec tests/sources tests/sensitivity -q
```

Result:

```text
24 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/e2e tests/live -q
```

Result:

```text
2 skipped
```

Total segmented coverage:

```text
176 passed, 2 skipped
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
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.5 sensitivity is an auxiliary audit layer, not part of the canonical v3.1 output schema.
2. Reverse DCF currently supports only the two-stage FCF fallback case based on adjusted FCF.
3. Manual fair value inputs correctly block sensitivity and return `UNKNOWN`; the sprint does not invent a model-derived base case.
4. Analyst-FCF, DDM, excess-return and AFFO-specific sensitivity remain future work.
5. Production readiness remains blocked by curated source population and review, by design.
