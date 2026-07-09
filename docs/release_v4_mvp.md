# v4.0 MVP Release Closure

This document defines the P0.14 release closure for the Personal Investment Research Audit Engine v4.0.

The release is an MVP closure, not a production-readiness claim. The product remains a local, internal, personal and educational decision-hygiene engine. It does not provide investment advice and does not output action-oriented investment language.

## Release status

Expected status for P0.14:

```text
MVP_COMPLETE_WITH_LIMITATIONS
```

The limitation is intentional: curated real-source files still need population and review before production-readiness can pass.

## P0.14 artifacts

P0.14 adds:

```text
schemas/aux/release_manifest.schema.json
src/sws_engine/release/manifest.py
scripts/ci/check_release_manifest.py
scripts/ci/run_all_v4_gates.py
scripts/release/run_local_mvp_smoke.py
docs/release_v4_mvp.md
docs/local_operator_runbook.md
examples/workflows/full_company_research_flow/
validation/validation_report_v4_p0_14.md
```

## Release manifest contract

The release manifest records:

```text
release_id
repository branch/commit
scope guardrails
capability closure table
validation reports found
indexed workflow artifacts
gate summary
known limitations
manual review items
next phase
```

The manifest is additive. It does not modify `schemas/output_schema.json`, the Snowflake checks, valuation, growth, portfolio formulas or `config/assumptions.yaml`.

## Required local command

```bash
PYTHONPATH=src python -m sws_engine.cli release-package \
  --repo-root . \
  --release-id v4.0-mvp-p0.14 \
  --output out/p14_ci
```

Optional gate aggregation, after the first manifest exists:

```bash
PYTHONPATH=src python scripts/ci/run_all_v4_gates.py \
  --output out/p14_ci/gates_report.json

PYTHONPATH=src python -m sws_engine.cli release-package \
  --repo-root . \
  --release-id v4.0-mvp-p0.14 \
  --output out/p14_ci \
  --gates-report out/p14_ci/gates_report.json
```

## Required interpretation

`MVP_COMPLETE_WITH_LIMITATIONS` means the local audit/research workflow is closed enough to use as a controlled MVP. It does not mean data is production-grade.

`NOT_READY` under production readiness must remain visible until curated universe, rates, ERP and Identifier Master files are populated and reviewed.

## Known limitations

The release must preserve these limitations:

- Missing data remains `UNKNOWN`.
- Pragmatic provider degradation remains visible.
- Live data fetching is not part of release validation.
- Full source conflict runtime is deferred.
- Sector-specific workflows remain foundation-level.
- Transaction-based attribution, optimization, broker integration and action-oriented investment language remain outside MVP scope.

---
Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St (Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. Acest document este pentru uz intern/personal/educațional. Not investment advice.
