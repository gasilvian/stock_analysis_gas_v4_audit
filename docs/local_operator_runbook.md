# Local Operator Runbook — v4.0 MVP

This runbook is the minimal local sequence for operating the v4.0 MVP as a research-audit system.

## 1. Validate the repository state

```bash
PYTHONPATH=src PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest tests/release tests/research tests/api tests/dashboard -q
```

Run the existing segmented test groups when preparing a full archive.

## 2. Generate the release closure package

```bash
PYTHONPATH=src python scripts/release/run_local_mvp_smoke.py \
  --repo-root . \
  --output out/p14_ci \
  --release-id v4.0-mvp-p0.14
```

This produces:

```text
out/p14_ci/local_mvp_smoke_summary.json
out/p14_ci/v4.0-mvp-p0.14_release_manifest.json
out/p14_ci/v4.0-mvp-p0.14_release_report.md
out/p14_ci/workflow_smoke/AAPL_workflow_package.json
out/p14_ci/workflow_smoke/AAPL_workflow_package_report.md
```

## 3. Run release guardrails

```bash
PYTHONPATH=src python scripts/ci/check_release_manifest.py out/p14_ci
```

Then run the full local gate aggregator:

```bash
PYTHONPATH=src python scripts/ci/run_all_v4_gates.py \
  --output out/p14_ci/gates_report.json
```

Because the aggregator includes the release manifest gate, generate the manifest before running it.

## 4. Rebuild the manifest with gate evidence

```bash
PYTHONPATH=src python -m sws_engine.cli release-package \
  --repo-root . \
  --release-id v4.0-mvp-p0.14 \
  --output out/p14_ci \
  --gates-report out/p14_ci/gates_report.json
```

## 5. Read the result correctly

Expected MVP result:

```text
MVP_COMPLETE_WITH_LIMITATIONS
production_readiness=NOT_READY
```

Do not reinterpret `NOT_READY` as a failure of the MVP. It means curated source population is still required before stronger operational use.

## 6. Do not override UNKNOWN

When an output is `UNKNOWN`, leave it visible. Do not fill it from memory, similar companies, public screenshots or unreviewed assumptions.

---
Atribuire: metodologia sursă provine din repo-urile publice Simply Wall St (Company-Analysis-Model, Portfolio-Analysis-Model), licență CC BY-NC-SA 4.0. Acest document este pentru uz intern/personal/educațional. Not investment advice.
