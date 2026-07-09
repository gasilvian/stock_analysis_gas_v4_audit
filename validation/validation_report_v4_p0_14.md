# Validation Report — v4.0 P0.14 Release Hardening / Product Closure Foundation

## Scope implemented

Implemented the controlled sprint after P0.13: **Release Hardening / Product Closure Foundation**.

Implemented:

- `schemas/aux/release_manifest.schema.json` for additive MVP release-closure artifacts.
- `src/sws_engine/release/manifest.py` for deterministic local MVP release manifests and Markdown closure reports.
- CLI `release-package`.
- `scripts/release/run_local_mvp_smoke.py` as a one-command offline MVP smoke workflow.
- `scripts/ci/check_release_manifest.py` for release manifest/report guardrails.
- `scripts/ci/run_all_v4_gates.py` for aggregated v4.0 gate execution/reporting.
- `docs/release_v4_mvp.md`.
- `docs/local_operator_runbook.md`.
- `examples/workflows/full_company_research_flow/`.
- `config/reason_code_dictionary.yaml` extended to `reason_code_dictionary.v0.9` with P0.14 release reason codes.
- `src/sws_engine/explain/dictionary.py` required reason-code set extended for P0.14 release codes.
- Tests under `tests/release/` for:
  - release manifest schema validation,
  - production-readiness limitation visibility,
  - UNKNOWN/limitation report guardrails,
  - CLI smoke execution,
  - release manifest gate execution,
  - v4 gate aggregator dry-run.

## P0.14 release outputs implemented

P0.14 implements these auxiliary release-process outputs:

- `release_manifest`
- `release_report`
- `scope_guardrails`
- `capability_summary`
- `validation_summary`
- `artifact_index`
- `gate_summary`
- `known_limitations`
- `manual_review_items`
- `next_phase`

These outputs are release governance artifacts, not v3.1 Snowflake checks and not investment recommendations.

## P0.14 reason codes added

- `RELEASE_MVP_COMPLETE`
- `RELEASE_MVP_COMPLETE_WITH_LIMITATIONS`
- `RELEASE_REQUIRED_ARTIFACT_MISSING`
- `RELEASE_CAPABILITY_PRESENT`
- `RELEASE_CAPABILITY_ARTIFACT_MISSING`
- `RELEASE_PRODUCTION_NOT_READY`
- `RELEASE_OPTIONAL_ARTIFACT_MISSING`
- `RELEASE_GATES_NOT_RUN`
- `RELEASE_GUARDRAILS_PASS`
- `RELEASE_LOCAL_SMOKE_COMPLETED`

## CLI smoke run

```bash
PYTHONPATH=src python scripts/release/run_local_mvp_smoke.py \
  --repo-root . \
  --output out/p14_ci \
  --release-id v4.0-mvp-p0.14
```

Result:

```text
PASS_WITH_LIMITATIONS; summary_path=out/p14_ci/local_mvp_smoke_summary.json;
release_manifest_json=out/p14_ci/v4.0-mvp-p0.14_release_manifest.json;
release_report_md=out/p14_ci/v4.0-mvp-p0.14_release_report.md
```

## Release package run

```bash
PYTHONPATH=src python -m sws_engine.cli release-package \
  --repo-root . \
  --release-id v4.0-mvp-p0.14 \
  --output out/p14_ci \
  --gates-report out/p14_ci/gates_report.json
```

Result:

```text
MVP_COMPLETE_WITH_LIMITATIONS; reason_code=RELEASE_MVP_COMPLETE_WITH_LIMITATIONS;
capabilities_passed=9; capabilities_total=9; production_readiness=NOT_READY
```

Artifacts:

```text
out/p14_ci/v4.0-mvp-p0.14_release_manifest.json
out/p14_ci/v4.0-mvp-p0.14_release_report.md
out/p14_ci/gates_report.json
out/p14_ci/local_mvp_smoke_summary.json
```

## Governance gates run

```bash
PYTHONPATH=src python scripts/ci/check_release_manifest.py out/p14_ci
PYTHONPATH=src python scripts/ci/run_all_v4_gates.py --output out/p14_ci/gates_report.json
```

Result:

```text
check_release_manifest.py — PASS
run_all_v4_gates.py — PASS; reason_code=ALL_GATES_PASSED
```

The aggregated gate runner executed:

```text
validate_demo_outputs.py — PASS
check_no_score_normalized.py — PASS
check_attribution_footer.py — PASS
check_real_source_population_workflow.py — PASS/OK; production readiness remains NOT_READY as expected
check_audit_unknown_preserved.py — PASS
check_source_registry_field_rules.py — PASS
check_reason_code_dictionary_complete.py — PASS
check_watchlist_report_guardrails.py — PASS
check_thesis_decision_guardrails.py — PASS
check_portfolio_audit_guardrails.py — PASS
check_investment_memo_guardrails.py — PASS
check_run_comparison_guardrails.py — PASS
check_workflow_package_guardrails.py — PASS
check_release_manifest.py — PASS
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/release tests/research tests/api -q
```

Result:

```text
67 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/dashboard tests/audit tests/explain tests/sensitivity tests/rates tests/reference tests/sec tests/sources -q
```

Result:

```text
81 passed
```

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/averages_real tests/ci tests/contract tests/data_layer tests/deploy tests/docs \
  tests/gold tests/governance tests/integration tests/manual tests/ops tests/persistence \
  tests/portfolio tests/providers tests/synthetic -q
```

Result:

```text
89 passed
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
237 passed, 2 skipped
```

A single all-in-one pytest run was attempted but timed out in the sandbox after partial progress. The reliable result is the segmented coverage above.

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Preservation checks

- `schemas/output_schema.json` not modified.
- `src/sws_engine/checks/` not modified.
- `src/sws_engine/valuation/` not modified.
- `src/sws_engine/growth/` not modified.
- `src/sws_engine/portfolio/` not modified.
- `config/assumptions.yaml` not modified.
- No normalized-score runtime surface introduced.
- UNKNOWN policy preserved: release manifest keeps production readiness and missing/limited artifacts visible as manual review items.
- Provider degradation visibility policy is preserved in release manifest guardrails.
- Release outputs are auxiliary governance artifacts and are not v3.1 Snowflake checks.
- Reports include not-investment-advice footer.
- Recommendation-language guardrails reject forbidden wording.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## Explicitly not implemented

This sprint does **not** implement:

- Production-readiness PASS.
- Live data fetching.
- Full source conflict detector runtime.
- Sector-specific bank / REIT / insurer workflows.
- Transaction-based performance attribution.
- Portfolio optimization.
- Rebalancing recommendations.
- Broker integration.
- Automatic integration into canonical `output_schema.json`.
- Any investment recommendation text.
- Action-oriented investment labels or rating language.

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.14 closes the MVP release package, but it does not populate curated real-source files.
2. Production readiness remains `NOT_READY` by design.
3. P0.14 uses offline fixtures and existing local artifacts for release smoke validation.
4. The aggregated gate report is local checkout evidence, not external certification.
5. P1/P2 work remains required for mature real-source operation, source-conflict runtime and sector-specific workflows.
