# Validation Report — v4.0 P0.2 Data Confidence and Model Applicability Hardening

## Scope implemented

Implemented the next controlled sprint after P0.1:

- `config/audit_policies.yaml` for auxiliary audit-layer thresholds, source-quality weights, provider caps, TTLs and applicability policy.
- Backward-compatible `config/source_registry.yaml` extension with `tier`, `license_status`, `ttl_days`, `allowed_fields`, `field_quality_caps` and `field_rules`.
- `src/sws_engine/audit/policies.py` loader for audit policies and source registry.
- `src/sws_engine/audit/identifier_master.py` optional Identifier Master reader.
- Data Confidence v1.1: source tier mix, field quality details, stale-field detection, field-lineage score, policy version.
- Model Applicability v1.1: optional Identifier Master precedence; ADR/pharma/SaaS/foreign/loss-making contextual classifications.
- CLI `audit-company` parameters for audit policies, source registry and identifier master.
- API component endpoints:
  - `GET /companies/{ticker}/data-confidence`
  - `GET /companies/{ticker}/model-applicability`
- Dashboard Company Audit panel now surfaces source tier mix, stale fields and Identifier Master usage.
- New governance gate: `scripts/ci/check_source_registry_field_rules.py`.
- Tests for policies, field lineage, stale fields, Identifier Master precedence, component API endpoints and source registry field rules.

## Explicitly not implemented

This sprint does **not** implement:

- SEC CompanyFacts adapter.
- FRED/Treasury live loader.
- ERP curated workflow.
- full identifier master population.
- source conflict detector runtime.
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
- UNKNOWN policy preserved and surfaced in JSON/Markdown audit artifacts.
- `yfinance_pragmatic` degradation remains visible.
- Production readiness remains `NOT_READY` until curated real-source files are populated.

## Tests run

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q
```

Result:

```text
157 passed, 2 skipped
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
PASS / OK for demo output validation, no score_normalized, attribution footer, real-source honesty workflow, UNKNOWN preservation and source-registry field rules.
Production readiness remains NOT_READY until curated real-source files are populated, as expected.
```

Ruff:

```text
NOT_RUN: ruff is not installed in the sandbox environment.
```

## Verdict

PASS WITH LIMITATIONS.

Limitations:

1. Field-level source governance is structural in P0.2; runtime conflict detection is still P1.
2. Identifier Master support is optional; no curated Identifier Master file is populated yet.
3. Staleness is detected only when field lineage contains `as_of` / date metadata.
4. Data Confidence still operates over existing outputs and available lineage, not SEC/FRED official data.
5. Production readiness remains blocked by curated source population, by design.
