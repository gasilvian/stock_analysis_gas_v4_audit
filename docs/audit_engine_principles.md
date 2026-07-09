# Audit Engine Principles v4.0

This repository implements the first slice of the Personal Investment Research Audit Engine.
It is a **decision hygiene engine**, not an investment recommendation engine.

## Non-negotiable rules

1. Missing data remains `UNKNOWN`; it is never invented or silently imputed.
2. The original v3.1 check contract remains unchanged: `PASS/FAIL/UNKNOWN + reason_code + source_quality + source_class + input_lineage`.
3. `schemas/output_schema.json` is not modified by the audit layer.
4. Existing `checks/`, `valuation/`, `growth/`, and `portfolio/` logic is not modified by the audit layer.
5. `yfinance_pragmatic` must remain visibly degraded in every derived audit output.
6. The audit layer produces auxiliary artifacts only: `audit_summary.json` and `audit_report.md`.
7. The product is internal/personal/educational only and is not investment advice.

## P0.1 scope

P0.1 implements the audit layer foundation over existing persisted outputs:

- Data Confidence v1.
- Critical Missing Inputs Map.
- Model Applicability v1.
- Conclusion Risk v1.
- Audit Summary.
- Audit Markdown Report.
- CLI `audit-company`.
- Minimal Company Audit dashboard panel.

P0.1 explicitly excludes SEC ingestion, FRED/Treasury live loaders, ERP workflow,
sensitivity, reverse DCF, red flags, watchlist audit, thesis tracker, decision journal,
portfolio audit, and memo generation.
