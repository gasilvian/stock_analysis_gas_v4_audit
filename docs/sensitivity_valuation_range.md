# Sensitivity and Valuation Range — v4.0 P0.5

This sprint adds an auxiliary sensitivity layer for the Personal Investment Research Audit Engine.

Non-negotiable rules:

- It does not modify `schemas/output_schema.json`.
- It does not modify `src/sws_engine/checks/`, `valuation/`, `growth/` or `portfolio/`.
- It calls existing valuation functions on copied payloads.
- Missing valuation inputs return `UNKNOWN`; no values are invented.
- It reports a valuation range and fragility, not a BUY/SELL/HOLD signal.
- It remains internal/personal/educational and not investment advice.

Implemented outputs:

- `sensitivity_summary.json`
- `sensitivity_report.md`
- valuation range: bear/base/bull
- discount-rate × terminal-growth scenario matrix
- terminal value contribution
- reverse DCF implied base growth where deterministic inputs allow it
- valuation fragility level

Limitations:

- P0.5 implements reverse DCF for two-stage FCF fallback only.
- Analyst-FCF reverse DCF, DDM reverse solve, excess-return sensitivity and AFFO-specific sensitivity remain future work.
- Sensitivity cannot run when the base valuation is a manual fair value input or UNKNOWN.
