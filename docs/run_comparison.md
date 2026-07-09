# Run Comparison / Change Detection — v4.0 P0.12

## Scope

P0.12 adds deterministic comparison of two already-produced company run or audit artifacts.
It is a research-process audit artifact, not an investment recommendation.

The module compares:

- run identity: `run_id`, `valuation_date`, `assumptions_hash`, `provider_profile`;
- score and coverage deltas by axis when `score_summary` / `axis_scores` are present;
- check result and `reason_code` movements when `checks[]` are present;
- audit components: data confidence, model applicability, conclusion risk, provider/source quality;
- UNKNOWN count and critical missing inputs;
- warnings added/resolved;
- field lineage changes when lineage objects exist.

## Non-goals

P0.12 does not:

- fetch live data;
- rerun valuation, checks, growth or portfolio logic;
- modify `schemas/output_schema.json`;
- change `src/sws_engine/checks/`, `valuation/`, `growth/` or `portfolio/`;
- create buy/sell/hold or allocation recommendations;
- hide UNKNOWN or normalize score coverage.

## CLI

```bash
PYTHONPATH=src python -m sws_engine.cli compare-runs \
  --previous tests/fixtures/run_comparison/AAPL_previous_audit_summary.json \
  --current tests/fixtures/run_comparison/AAPL_current_audit_summary.json \
  --output out/p12_ci
```

Outputs:

```text
out/p12_ci/AAPL_run_comparison.json
out/p12_ci/AAPL_run_comparison_report.md
```

## API

```http
POST /research/compare-runs
```

Payload:

```json
{
  "previous": {"ticker": "AAPL", "run_id": "run_prev"},
  "current": {"ticker": "AAPL", "run_id": "run_curr"},
  "comparison_id": "AAPL-prev-curr",
  "artifact_type": "audit_summary"
}
```

## UNKNOWN policy

UNKNOWN is not treated as noise. If a check becomes UNKNOWN, if the current artifact still
contains UNKNOWN checks, or if new critical missing inputs appear, the comparison returns
`PASS_WITH_LIMITATIONS` with `RUN_COMPARISON_UNKNOWN_PRESERVED`.

## Guardrails

- Reports include the not-investment-advice footer.
- Recommendation-language guardrail rejects forbidden wording.
- Missing sections remain visible as UNKNOWN / unavailable, not inferred.
- Check-level comparison is only available when both artifacts contain `checks[]`.
