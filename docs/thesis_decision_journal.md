# v4.0 P0.9 — Thesis Tracker and Decision Journal Foundation

P0.9 adds the first research-discipline workflow layer on top of existing audit artifacts. It is additive and auxiliary: it does not change `schemas/output_schema.json`, check formulas, valuation, growth or portfolio logic.

## Scope

Implemented artifacts:

- `src/sws_engine/research/thesis.py`
- `src/sws_engine/research/journal.py`
- `schemas/aux/thesis_status.schema.json`
- `schemas/aux/decision_journal.schema.json`
- CLI `thesis-status`
- CLI `record-decision`
- API `POST /research/thesis/evaluate`
- API `POST /research/decision`

## Thesis Tracker

A thesis is a local YAML file curated by the operator. It may include `bull_case`, `bear_case`, `watch_metrics` and `invalidation_rules`.

Rules are machine-readable dictionaries:

```yaml
ticker: AAPL
thesis_type: quality_compounder
watch_metrics:
  - id: conclusion_risk_not_high
    source_field: conclusion_risk.risk_level
    operator: in
    threshold: [HIGH, UNKNOWN]
invalidation_rules:
  - id: rankable_required
    source_field: model_applicability.allowed_score_usage
    operator: neq
    threshold: rankable
```

Supported operators:

- `gt`, `gte`, `lt`, `lte`
- `eq`, `neq`
- `in`, `not_in`
- `contains`, `not_contains`

Status mapping:

- `BROKEN`: at least one invalidation rule is triggered.
- `UNKNOWN`: most rules are unevaluable.
- `WATCH`: at least one watch metric is triggered, or some rules are UNKNOWN.
- `ON_TRACK`: all supplied rules are evaluable and not triggered.

Missing fields return `UNKNOWN`; rules are not silently skipped.

## Decision Journal

The decision journal records research-process decisions only. It does not record broker orders and it does not permit `buy`, `sell` or `hold` as decision types.

Allowed `decision_type` values:

- `research_deeper`
- `pass`
- `add_watch`
- `remove_watch`
- `review_thesis`
- `personal_action_external`

Each record captures:

- ticker;
- decision type;
- data confidence at decision time;
- model applicability at decision time;
- conclusion risk at decision time;
- thesis status at decision time;
- run id at decision time;
- manual review items.

## CLI examples

```bash
PYTHONPATH=src python -m sws_engine.cli thesis-status \
  --thesis tests/fixtures/thesis_decision/AAPL_thesis.yaml \
  --audit-summary tests/fixtures/thesis_decision/AAPL_audit_summary.json \
  --output out/p09_ci/thesis
```

```bash
PYTHONPATH=src python -m sws_engine.cli record-decision \
  --decision tests/fixtures/thesis_decision/AAPL_decision.yaml \
  --journal out/p09_ci/decisions/decisions.jsonl \
  --audit-summary tests/fixtures/thesis_decision/AAPL_audit_summary.json \
  --output out/p09_ci/decision
```

## Guardrails

- No `BUY / SELL / HOLD` recommendation language.
- No live data fetch.
- No mutation of canonical v3.1 outputs.
- UNKNOWN is preserved and surfaced as manual review.
- Reports include the attribution and not-investment-advice footer.
