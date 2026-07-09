# Validation Report — v4.0 P0.6 Explainability and Reason Code Narratives Foundation

## Scope implemented

Implemented the next controlled sprint after P0.5: **Explainability, Reason Codes and UNKNOWN Narratives Foundation**.

Implemented:

- `config/reason_code_dictionary.yaml` with deterministic templates for v3.1 check reason codes and auxiliary v4 audit/source/sensitivity reason codes.
- `src/sws_engine/explain/` package:
  - `dictionary.py`
  - `check_explainer.py`
  - package exports in `__init__.py`
- `schemas/aux/explanation_package.schema.json` for additive explanation artifacts.
- CLI `explain-company` for output-json and persisted-run explanation generation.
- API endpoint `GET /companies/{ticker}/explain`.
- Minimal integration in `audit_report.md` generation: a P0.6 “Check explanations” section is rendered when original checks are available to the report renderer.
- Governance gate `scripts/ci/check_reason_code_dictionary_complete.py`.
- `docs/explainability_reason_codes.md`.
- Tests under `tests/explain/` and `tests/api/test_api_explain.py`.

## Explicitly not implemented

This sprint does **not** implement:

- Free-form LLM explanations.
- AI rewriting.
- Investment recommendation text.
- BUY / SELL / HOLD language.
- Red flag engine.
- Accounting quality.
- Capital allocation.
- Watchlist audit.
- Thesis tracker.
- Decision journal.
- Portfolio audit.
- Investment memo generator.
- Complex dashboard pages.
- Automatic integration into canonical `output_schema.json`.
- Production-readiness PASS.

## Preservation checks

- `schemas/output_schema.json` not modified.
- `src/sws_engine/checks/` not modified.
- `src/sws_engine/valuation/` not modified.
- `src/sws_engine/growth/` not modified.
- `src/sws_engine/portfolio/` not modified.
- `config/assumptions.yaml` not modified.
- No `score_normalized` runtime surface introduced.
- UNKNOWN policy preserved: explainability describes UNKNOWN; it does not resolve UNKNOWN or invent values.
- Templates are deterministic and source-bound: explanations use only reason_code, result, inputs, threshold, source_quality, source_class and input_lineage.
- Reports include not-investment-advice footer.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke run

```bash
PYTHONPATH=src python -m sws_engine.cli explain-company \
  --input examples/demo_output.json \
  --output out/explain_ci \
  --include-pass
```

Result:

```text
PASS; ticker=DEMO; checks_explained_count=30; known_reason_codes_complete_for_package=true
```

Artifacts:

```text
out/explain_ci/DEMO_explanations_analyst.json
out/explain_ci/DEMO_explanation_report_analyst.md
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/api tests/audit tests/explain tests/sensitivity tests/rates tests/reference tests/sec tests/sources -q
```

Result:

```text
78 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/averages_real tests/ci tests/contract tests/dashboard tests/data_layer tests/deploy \
  tests/docs tests/gold tests/governance tests/integration tests/manual tests/ops \
  tests/persistence tests/portfolio tests/providers tests/synthetic -q
```

Result:

```text
106 passed
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
184 passed, 2 skipped
```

Governance gates run:

```bash
PYTHONPATH=src python scripts/ci/validate_demo_outputs.py
PYTHONPATH=src python scripts/ci/check_no_score_normalized.py
PYTHONPATH=src python scripts/ci/check_attribution_footer.py
PYTHONPATH=src python scripts/ci/check_real_source_population_workflow.py
PYTHONPATH=src python scripts/ci/check_audit_unknown_preserved.py out/audit_ci
PYTHONPATH=src python scripts/ci/check_source_registry_field_rules.py
PYTHONPATH=src python scripts/ci/check_reason_code_dictionary_complete.py
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation, source-registry field rules,
and reason-code dictionary completeness.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.6 explains reason codes with deterministic templates only; no LLM rewriting is enabled.
2. The dictionary covers supported v3.1 and current auxiliary v4 reason codes; future modules must add templates and pass the gate.
3. Audit-report integration is minimal. Full memo/report composition remains future work.
4. Explainability does not fix missing data; UNKNOWN remains UNKNOWN.
5. Production readiness remains blocked by curated source population and review, by design.
