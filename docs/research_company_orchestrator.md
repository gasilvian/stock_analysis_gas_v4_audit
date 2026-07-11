# Research Company Orchestrator (P2.1)

`research-company` runs the entire single-company research chain with one
command, replacing the eight hand-driven steps of the manual flow:

```
payload (with curated injections) -> engine -> persist -> audit
    -> sensitivity -> explain -> business-risk -> conflict-report -> memo
```

Every produced artifact is registered in the P1.8 SQLite artifact index, so
`generate-memo --auto`, `workflow-package` and the dashboard hub resolve them
without hand-wired paths. The chain itself emits a per-step report —
`<TICKER>_research_company_run.json` (schema:
`schemas/aux/research_company_run.schema.json`) plus a Markdown rendering —
registered under `research_company_run_json` / `research_company_run_md`.

## Modes

**Offline (`--input payload.json`)** — a pre-built payload is used as-is.
Optional estimates/averages/SEC injections still apply (they are pure
payload-level functions). Curated *rates* injection is live-mode only, because
it flows through the provider mapper; the report states this explicitly via
`RATES_INJECTION_NOT_APPLICABLE_OFFLINE` instead of pretending an injection
happened.

**Live (`--ticker AAPL`)** — the yfinance pragmatic provider builds the
payload with curated rates overrides (`--bond-csv`, `--erp-json`), mirroring
`real-dashboard-bootstrap`, then `--estimates-dir`, `--averages-json` and
`--sec-dir` injections apply on top. All P2.3 TTL/staleness enforcement and
review-lifecycle refusals apply unchanged, because the orchestrator calls the
same injection functions.

## Examples

```bash
# Offline, on the committed demo payload (same fixture as the e2e test):
PYTHONPATH=src python -m sws_engine.cli research-company \
  --input tests/fixtures/demo_complete_non_financial.json \
  --db out/research.db --output out/demo_chain

# Live, with the full curated injection stack:
PYTHONPATH=src python -m sws_engine.cli research-company \
  --ticker AAPL --db data/sws.db --output out/AAPL_chain \
  --bond-csv data/real_sources/rates/bond_yields_10y_curated.csv \
  --erp-json data/real_sources/rates/erp_curated.json \
  --sec-dir data/real_sources/sec \
  --averages-json data/real_sources/averages/averages_snapshot.json \
  --estimates-dir data/real_sources/estimates
```

## Status semantics and exit codes

| Chain status | Meaning | Exit code |
|---|---|---|
| `PASS` | every step PASS, no payload warnings | 0 |
| `PASS_WITH_LIMITATIONS` | at least one step UNKNOWN/FAIL/SKIPPED, or curated-source warnings | 2 |
| `FAIL` | payload, engine or persistence failed (nothing downstream can run) | 1 |

Step isolation: a failing audit-chain step is recorded as
`RESEARCH_CHAIN_STEP_FAILED` and the remaining independent steps still run.
The memo step depends on a registered audit summary; if the audit step failed,
the memo is honestly `SKIPPED`, never fabricated. An honest UNKNOWN (for
example sensitivity on a manual fair value) is preserved as UNKNOWN and
degrades the chain status without blocking it.

## Governance invariants

- UNKNOWN preserved end to end; `unknown_summary` lists UNKNOWN, failed and
  skipped steps plus the engine output's UNKNOWN check count.
- No invented values: missing curated sources produce visible
  `payload_warnings` and the fields stay MISSING.
- No recommendation or rating language anywhere in the rendered report
  (guardrail enforced at render time).
- No modifications to the frozen v3.1 engine, `output_schema.json` or the
  existing single-step commands — the orchestrator is a thin additive layer
  over the same functions the individual CLI commands call.

---

*Internal/personal/educational research audit artifact. Not investment
advice. Methodology attribution: public Simply Wall St Company/Portfolio
Analysis Model repositories (CC BY-NC-SA 4.0).*
