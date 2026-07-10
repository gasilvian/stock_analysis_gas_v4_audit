# Manual analyst estimates packs (B4)

One JSON per ticker: `{TICKER}_analyst_estimates.json` (copy the template,
never inject the template itself — it is refused by design).

Workflow per quarter (per the data-source inventory):
1. Read consensus estimates on a platform you have (TIKR / Koyfin /
   TradingView) — manual transcription only, no scraping.
2. Fill `earnings_estimates` (value + analyst count per fiscal year, the SWS
   weighted format) and optionally `fcf_estimates`, forward
   `earnings_growth` / `revenue_growth`, `becomes_profitable_in_5y`.
3. Set `source_as_of`, `expires_at` (recommended: next quarter), review the
   numbers, then set `review_status: reviewed`.
4. Inject via `real-dashboard-bootstrap --estimates-dir data/real_sources/estimates`
   or `build-payload-yfinance --estimates-pack <file>`.

Governance: unreviewed, expired, template or ticker-mismatched packs are
refused with explicit reason codes; injected lineage is
`manual_estimates_pack / assumption / E3 / manual_curated`. Estimates are
transcribed forecasts — never labeled exact, never invented.
