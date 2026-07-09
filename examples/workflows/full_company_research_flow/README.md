# Full Company Research Flow — Offline MVP Example

This example documents the local MVP workflow from existing artifacts to release closure.

```bash
# 1. Build workflow package from committed/offline artifacts
PYTHONPATH=src python -m sws_engine.cli workflow-package \
  --audit-summary tests/fixtures/workflow_package/AAPL_audit_summary.json \
  --explanations tests/fixtures/workflow_package/AAPL_explanations.json \
  --sensitivity tests/fixtures/workflow_package/AAPL_sensitivity_summary.json \
  --business-risk tests/fixtures/workflow_package/AAPL_business_risk_package.json \
  --thesis-status tests/fixtures/workflow_package/AAPL_thesis_status.json \
  --decision-record tests/fixtures/workflow_package/AAPL_decision_record.json \
  --portfolio-audit tests/fixtures/workflow_package/core_portfolio_audit.json \
  --investment-memo out/p11_ci/AAPL_investment_audit_memo.json \
  --run-comparison out/p12_ci/AAPL_run_comparison.json \
  --workflow-id p14-local-example \
  --output out/p14_ci/example_workflow

# 2. Generate release manifest
PYTHONPATH=src python -m sws_engine.cli release-package \
  --repo-root . \
  --release-id v4.0-mvp-p0.14 \
  --output out/p14_ci

# 3. Run release guardrail
PYTHONPATH=src python scripts/ci/check_release_manifest.py out/p14_ci
```

The workflow package and release manifest are research-audit artifacts. They do not provide investment advice.
