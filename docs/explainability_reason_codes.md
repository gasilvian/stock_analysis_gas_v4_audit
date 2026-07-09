# Explainability and Reason Code Dictionary — v4.0 P0.6

## Scope

Sprint P0.6 adds a deterministic explainability layer. It does not change the v3.1 check contract, scoring, valuation, growth, portfolio logic, or `schemas/output_schema.json`.

The layer explains existing artifacts using reason-code templates:

- company checks with `PASS/FAIL/UNKNOWN`, `reason_code`, `source_quality`, `source_class`, `inputs`, `threshold`, `input_lineage`;
- audit summary drivers from Data Confidence, Model Applicability and Conclusion Risk;
- selected auxiliary reason codes emitted by SEC/rates/sensitivity modules.

It is deliberately template-driven. It does not generate free-form investment commentary.

## Files

- `config/reason_code_dictionary.yaml`
- `src/sws_engine/explain/dictionary.py`
- `src/sws_engine/explain/check_explainer.py`
- `schemas/aux/explanation_package.schema.json`
- `scripts/ci/check_reason_code_dictionary_complete.py`

## CLI

```bash
PYTHONPATH=src python -m sws_engine.cli explain-company \
  --input examples/demo_output.json \
  --output out/explain_demo \
  --mode analyst
```

or from a persisted run:

```bash
PYTHONPATH=src python -m sws_engine.cli explain-company \
  --ticker AAPL \
  --db data/sws.db \
  --output out/explain/AAPL \
  --mode plain_english
```

Outputs:

- `<TICKER>_explanations_<mode>.json`
- `<TICKER>_explanation_report_<mode>.md`

## API

```text
GET /companies/{ticker}/explain?mode=analyst|plain_english&include_pass=false
```

The endpoint computes explanations on demand from the latest persisted company output. It does not persist new canonical output and does not alter the v3.1 schema.

## Governance

The gate:

```bash
PYTHONPATH=src python scripts/ci/check_reason_code_dictionary_complete.py
```

fails if any required v3.1 or auxiliary reason code has no deterministic template.

## UNKNOWN policy

UNKNOWN remains visible. Explainability only describes why something is UNKNOWN; it does not resolve UNKNOWN and does not invent missing values.

## Not investment advice

All reports carry the existing attribution and not-investment-advice footer. The explainer vocabulary is limited to audit interpretation, data quality and remediation.
