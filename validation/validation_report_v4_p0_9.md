# Validation Report — v4.0 P0.9 Thesis Tracker and Decision Journal Foundation

## Scope implemented

Implemented the next controlled sprint after P0.8: **Thesis Tracker and Decision Journal Foundation**.

Implemented:

- `schemas/aux/thesis_status.schema.json` for additive thesis-status artifacts.
- `schemas/aux/decision_journal.schema.json` for additive decision-journal records.
- `src/sws_engine/research/thesis.py` for deterministic thesis rule evaluation:
  - `ON_TRACK`,
  - `WATCH`,
  - `BROKEN`,
  - `UNKNOWN`.
- `src/sws_engine/research/journal.py` for local research-process decision records.
- CLI `thesis-status`.
- CLI `record-decision`.
- API endpoint `POST /research/thesis/evaluate`.
- API endpoint `POST /research/decision`.
- `docs/thesis_decision_journal.md`.
- `config/reason_code_dictionary.yaml` extended to `reason_code_dictionary.v0.4` with P0.9 thesis/decision reason codes.
- `src/sws_engine/explain/dictionary.py` required reason-code set extended for P0.9 reason codes.
- Governance gate `scripts/ci/check_thesis_decision_guardrails.py`.
- Offline fixtures under `tests/fixtures/thesis_decision/`.
- Tests under `tests/research/` and `tests/api/test_api_thesis_decision.py` for:
  - thesis package schema validation,
  - ON_TRACK thesis status,
  - BROKEN thesis status,
  - UNKNOWN preservation for unevaluable rules,
  - CLI smoke execution,
  - API endpoint smoke execution,
  - decision-journal schema validation,
  - forbidden decision types (`buy`, `sell`, `hold`) rejected.

## P0.9 thesis statuses implemented

P0.9 implements deterministic research-process thesis statuses:

- `ON_TRACK`: all supplied rules are evaluable and not triggered.
- `WATCH`: at least one watch metric is triggered, or some rules are UNKNOWN.
- `BROKEN`: at least one invalidation rule is triggered.
- `UNKNOWN`: most rules are unevaluable or thesis inputs are missing.

These are process-discipline statuses, not investment recommendations and not buy/sell/hold signals.

## P0.9 decision journal implemented

P0.9 records research-process decisions only.

Allowed `decision_type` values:

- `research_deeper`
- `pass`
- `add_watch`
- `remove_watch`
- `review_thesis`
- `personal_action_external`

Forbidden decision types are rejected and not appended to the journal:

- `buy`
- `sell`
- `hold`
- `strong_buy`
- `strong_sell`

Each valid record captures:

- `data_confidence_at_decision`,
- `model_applicability_at_decision`,
- `conclusion_risk_at_decision`,
- `thesis_status_at_decision`,
- `run_id_at_decision`,
- manual review items available at decision time.

## P0.9 reason codes added

- `THESIS_INPUTS_MISSING`
- `THESIS_NO_EVALUABLE_RULES`
- `THESIS_INVALIDATION_TRIGGERED`
- `THESIS_MAJORITY_RULES_UNKNOWN`
- `THESIS_WATCH_METRIC_TRIGGERED`
- `THESIS_RULES_PARTIALLY_UNKNOWN`
- `THESIS_ON_TRACK`
- `THESIS_RULE_INPUT_MISSING`
- `THESIS_RULE_COMPARISON_FAILED`
- `THESIS_RULE_TRIGGERED`
- `THESIS_RULE_OK`
- `DECISION_RECORDED`
- `DECISION_INPUTS_MISSING`
- `DECISION_TYPE_NOT_ALLOWED`

## Explicitly not implemented

This sprint does **not** implement:

- Portfolio audit.
- Investment memo generator.
- Run comparison.
- Complex dashboard pages.
- Live data fetching.
- Full source conflict detector runtime.
- Sector-specific bank / REIT / insurer workflows.
- Automatic integration into canonical `output_schema.json`.
- Production-readiness PASS.
- Any investment recommendation text.
- BUY / SELL / HOLD language.

## Preservation checks

- `schemas/output_schema.json` not modified.
- `src/sws_engine/checks/` not modified.
- `src/sws_engine/valuation/` not modified.
- `src/sws_engine/growth/` not modified.
- `src/sws_engine/portfolio/` not modified.
- `config/assumptions.yaml` not modified.
- No `score_normalized` runtime surface introduced.
- UNKNOWN policy preserved: unevaluable thesis rules remain `UNKNOWN` and degrade thesis status.
- Decision journal rejects buy/sell/hold process leakage.
- Thesis and decision outputs are auxiliary research-workflow artifacts and are not v3.1 Snowflake checks.
- Reports include not-investment-advice footer.
- Production readiness remains `NOT_READY` until curated source files are populated and reviewed.

## CLI smoke runs

```bash
PYTHONPATH=src python -m sws_engine.cli thesis-status \
  --thesis tests/fixtures/thesis_decision/AAPL_thesis.yaml \
  --audit-summary tests/fixtures/thesis_decision/AAPL_audit_summary.json \
  --output out/p09_ci/thesis
```

Result:

```text
PASS_WITH_LIMITATIONS; ticker=AAPL; reason_code=THESIS_ON_TRACK; thesis_status=ON_TRACK; rules_summary={total: 3, ok: 3, triggered: 0, unknown: 0}
```

Artifacts:

```text
out/p09_ci/thesis/AAPL_thesis_status.json
out/p09_ci/thesis/AAPL_thesis_status_report.md
```

```bash
PYTHONPATH=src python -m sws_engine.cli record-decision \
  --decision tests/fixtures/thesis_decision/AAPL_decision.yaml \
  --journal out/p09_ci/decisions/decisions.jsonl \
  --audit-summary tests/fixtures/thesis_decision/AAPL_audit_summary.json \
  --thesis-status out/p09_ci/thesis/AAPL_thesis_status.json \
  --output out/p09_ci/decision
```

Result:

```text
PASS; ticker=AAPL; reason_code=DECISION_RECORDED; decision_type=research_deeper
```

Artifacts:

```text
out/p09_ci/decision/<AAPL_decision_record>.json
out/p09_ci/decision/<AAPL_decision_record>.md
out/p09_ci/decisions/decisions.jsonl
```

## Tests run

Segmented offline coverage:

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest \
  tests/api tests/audit tests/explain tests/sensitivity tests/rates tests/reference tests/sec tests/sources tests/research -q
```

Result:

```text
99 passed
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
205 passed, 2 skipped
```

Governance gates run:

```bash
PYTHONPATH=src python scripts/ci/validate_demo_outputs.py
PYTHONPATH=src python scripts/ci/check_no_score_normalized.py
PYTHONPATH=src python scripts/ci/check_attribution_footer.py
PYTHONPATH=src python scripts/ci/check_real_source_population_workflow.py
PYTHONPATH=src python scripts/ci/check_audit_unknown_preserved.py tests/fixtures/watchlist/audits
PYTHONPATH=src python scripts/ci/check_source_registry_field_rules.py
PYTHONPATH=src python scripts/ci/check_reason_code_dictionary_complete.py
PYTHONPATH=src python scripts/ci/check_watchlist_report_guardrails.py out/p08_ci
PYTHONPATH=src python scripts/ci/check_thesis_decision_guardrails.py out/p09_ci
```

Result:

```text
PASS / OK for demo output validation, no score_normalized, attribution footer,
real-source honesty workflow, UNKNOWN preservation, source-registry field rules,
reason-code dictionary completeness, watchlist report guardrails and thesis/decision guardrails.
Production readiness remains NOT_READY until curated source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. P0.9 implements deterministic thesis rule evaluation only; it does not interpret free-form thesis text.
2. Thesis status depends on supplied audit/business-risk/sensitivity artifacts; missing fields remain `UNKNOWN`.
3. Decision Journal is local JSONL and records research-process decisions only, not broker orders.
4. No portfolio audit or investment memo generator is included in this sprint.
5. Production readiness remains blocked by curated source population and review, by design.
