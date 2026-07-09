"""CLI: company analysis, portfolio analysis and markdown reports.

Usage:
  python -m sws_engine.cli company -i input.json [-a assumptions.yaml]
      [-s output_schema.json] [-o out.json] [--report out.md]
  python -m sws_engine.cli portfolio -i portfolio.json [-a assumptions.yaml]
      [-o out.json] [--report out.md]
  python -m sws_engine.cli api [--host 127.0.0.1] [--port 8000]
"""
import argparse
import json
import sys

DEFAULT_ASSUMPTIONS = "config/assumptions.yaml"
DEFAULT_SCHEMA = "schemas/output_schema.json"


def main(argv=None):
    ap = argparse.ArgumentParser(prog="sws-engine",
                                 description="SWS Snowflake Engine v3.1 "
                                             "(not investment advice)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("company", help="run company analysis")
    c.add_argument("-i", "--input", required=True)
    c.add_argument("-a", "--assumptions", default=DEFAULT_ASSUMPTIONS)
    c.add_argument("-s", "--schema", default=DEFAULT_SCHEMA)
    c.add_argument("-o", "--output")
    c.add_argument("--report")
    c.add_argument("--snapshot-dir", default=None)
    c.add_argument("--db", default=None,
                   help="optional SQLite DB path; when set, persist this single "
                        "run (input snapshot + run + output) so audit-company "
                        "and the v4 audit chain can consume it")

    p = sub.add_parser("portfolio", help="run portfolio analysis")
    p.add_argument("-i", "--input", required=True)
    p.add_argument("-a", "--assumptions", default=DEFAULT_ASSUMPTIONS)
    p.add_argument("-o", "--output")
    p.add_argument("--report")

    api = sub.add_parser("api", help="start the FastAPI backend")
    api.add_argument("--host", default="127.0.0.1")
    api.add_argument("--port", type=int, default=8000)
    api.add_argument("--reload", action="store_true")

    b = sub.add_parser("build-averages", help="build averages snapshot from a universe CSV")
    b.add_argument("--universe", required=True)
    b.add_argument("--market", required=True)
    b.add_argument("--date", required=True)
    b.add_argument("--min-universe", type=int, default=5)
    b.add_argument("--savings-rate", type=float, default=None)
    b.add_argument("--cpi", type=float, default=None)
    b.add_argument("--out-dir", default="data/averages")

    bp = sub.add_parser("build-payload", help="assemble a company payload from a recorded snapshot")
    bp.add_argument("--snapshot", required=True)
    bp.add_argument("--averages", required=True)
    bp.add_argument("--industry", required=True)
    bp.add_argument("--country", required=True)
    bp.add_argument("--date", required=True)
    bp.add_argument("--bond-csv", default="data/rates/bond_yields_10y.csv")
    bp.add_argument("--erp-json", default="data/rates/erp.json")
    bp.add_argument("-o", "--output", required=True)

    byf = sub.add_parser("build-payload-yfinance", help="build a company payload from live yfinance")
    byf.add_argument("--ticker", required=True)
    byf.add_argument("--valuation-date", default=None)
    byf.add_argument("--market", default=None)
    byf.add_argument("--industry", default=None)
    byf.add_argument("--output", required=True)
    byf.add_argument("--refresh", action="store_true")
    byf.add_argument("--sec-payload-updates", default=None,
                     help="P1.3b: optional {ticker}_sec_payload_updates.json from "
                          "refresh-sec-financials; merged with sec_precedence and "
                          "visible source_conflicts (manual merge-overrides applied "
                          "later still win)")

    cl = sub.add_parser("company-live", help="build yfinance payload and run company analysis")
    cl.add_argument("--ticker", required=True)
    cl.add_argument("--valuation-date", default=None)
    cl.add_argument("--market", default=None)
    cl.add_argument("--industry", default=None)
    cl.add_argument("-a", "--assumptions", default=DEFAULT_ASSUMPTIONS)
    cl.add_argument("-s", "--schema", default=DEFAULT_SCHEMA)
    cl.add_argument("--output", required=True)
    cl.add_argument("--report", default=None)
    cl.add_argument("--refresh", action="store_true")
    cl.add_argument("--persist", action="store_true")
    cl.add_argument("--db", default="data/sws.db")

    ryf = sub.add_parser("record-yfinance", help="record a yfinance raw snapshot")
    ryf.add_argument("--ticker", required=True)
    ryf.add_argument("--output", required=True)
    ryf.add_argument("--refresh", action="store_true")

    pc = sub.add_parser("provider-capability", help="write provider capability report")
    pc.add_argument("--provider", default="yfinance")
    pc.add_argument("--ticker", default=None)
    pc.add_argument("--output", required=True)

    vi = sub.add_parser("validate-input", help="dry-run: report missing fields and impacted checks")
    vi.add_argument("-i", "--input", required=True)
    vi.add_argument("--report", default=None, help="optional markdown report path")

    mo = sub.add_parser("merge-overrides", help="merge manual override JSON files into a base payload")
    mo.add_argument("--base", required=True)
    mo.add_argument("--override", action="append", required=True)
    mo.add_argument("-o", "--output", required=True)

    vr = sub.add_parser("validate-universe", help="write a ticker coverage report for a real/curated universe CSV")
    vr.add_argument("--universe", required=True)
    vr.add_argument("--output", required=True)

    rr = sub.add_parser("rates-report", help="inspect versioned rates/FX sources")
    rr.add_argument("--bond-csv", default="data/rates/bond_yields_10y.csv")
    rr.add_argument("--erp-json", default="data/rates/erp.json")
    rr.add_argument("--fx-csv", default="data/fx/fx_eod.csv")
    rr.add_argument("--output", default=None)

    er = sub.add_parser("eod-refresh", help="run the operational EOD refresh and write logs")
    er.add_argument("--watchlist", required=True)
    er.add_argument("--date", required=True)
    er.add_argument("--db", required=True)
    er.add_argument("--universe", required=True)
    er.add_argument("--market", required=True)
    er.add_argument("-a", "--assumptions", default=DEFAULT_ASSUMPTIONS)
    er.add_argument("-s", "--schema", default=DEFAULT_SCHEMA)
    er.add_argument("--bond-csv", default="data/rates/bond_yields_10y.csv")
    er.add_argument("--erp-json", default="data/rates/erp.json")
    er.add_argument("--fx-csv", default="data/fx/fx_eod.csv")
    er.add_argument("--logs-dir", default="logs")
    er.add_argument("--workers", type=int, default=2)
    er.add_argument("--provider-mode", choices=["recorded", "yfinance-live"], default="recorded")
    er.add_argument("--refresh-live", action="store_true")

    rdb = sub.add_parser("real-dashboard-bootstrap",
                         help="yfinance_pragmatic bootstrap: tickers -> engine -> SQLite -> dashboard-ready")
    rdb.add_argument("--tickers", default=None, help="comma-separated tickers, e.g. AAPL,MSFT")
    rdb.add_argument("--watchlist", default=None, help="optional CSV watchlist path")
    rdb.add_argument("--market", default="US")
    rdb.add_argument("--valuation-date", default="auto")
    rdb.add_argument("--db", default="data/sws.db")
    rdb.add_argument("--refresh", action=argparse.BooleanOptionalAction, default=False)
    rdb.add_argument("--persist", action=argparse.BooleanOptionalAction, default=True)
    rdb.add_argument("--output-dir", default="out/real_dashboard_bootstrap")
    rdb.add_argument("--continue-on-error", action=argparse.BooleanOptionalAction, default=True)
    rdb.add_argument("--min-success-count", type=int, default=1)
    rdb.add_argument("-a", "--assumptions", default=DEFAULT_ASSUMPTIONS)
    rdb.add_argument("-s", "--schema", default=DEFAULT_SCHEMA)
    rdb.add_argument("--bond-csv", default="data/real_sources/rates/bond_yields_10y_curated.csv")
    rdb.add_argument("--erp-json", default="data/real_sources/rates/erp_curated.json")
    rdb.add_argument("--sec-dir", default=None,
                     help="P1.3b: directory with refresh-sec-financials outputs "
                          "({ticker}_sec_payload_updates.json, directly or under normalized/); "
                          "when set, SEC official-filing values are merged into each payload "
                          "with sec_precedence and visible source_conflicts")

    ccu = sub.add_parser("create-curated-universe-from-yfinance",
                         help="create a pragmatic curated universe CSV from yfinance metadata")
    ccu.add_argument("--tickers", required=True)
    ccu.add_argument("--market", default="US")
    ccu.add_argument("--output", default="data/real_sources/universe/universe_US_curated.csv")
    ccu.add_argument("--refresh", action=argparse.BooleanOptionalAction, default=False)
    ccu.add_argument("--report", default="out/real_dashboard_bootstrap/universe_creation_report.md")

    lsr = sub.add_parser("legal-scope-report", help="validate legal/use-scope gate")
    lsr.add_argument("--scope", default="config/legal_scope.yaml")
    lsr.add_argument("--output", default=None)

    srr = sub.add_parser("source-registry-report", help="validate real/curated source registry")
    srr.add_argument("--registry", default="config/source_registry.yaml")
    srr.add_argument("--require-production", action="store_true")
    srr.add_argument("--output", default=None)

    prs = sub.add_parser("production-readiness", help="combined legal + source readiness gate")
    prs.add_argument("--scope", default="config/legal_scope.yaml")
    prs.add_argument("--registry", default="config/source_registry.yaml")
    prs.add_argument("--require-production", action="store_true")
    prs.add_argument("--output", default=None)

    pop = sub.add_parser("populate-real-sources", help="populate real-source folders from live yfinance watchlist")
    pop.add_argument("--watchlist", required=True)
    pop.add_argument("--out-dir", default="data/real_sources")
    pop.add_argument("--valuation-date", default=None)
    pop.add_argument("--refresh", action="store_true")

    dbp = sub.add_parser("init-db", help="create/upgrade the SQLite schema")
    dbp.add_argument("--db", required=True)

    ac = sub.add_parser("audit-company", help="run v4.0 P0.1 audit layer on latest persisted company output")
    ac.add_argument("--ticker", required=True)
    ac.add_argument("--db", default="data/sws.db")
    ac.add_argument("--output", required=True, help="output directory for audit_summary.json and audit_report.md")
    ac.add_argument("--run-id", default=None, help="optional persisted run_id to audit instead of latest")
    ac.add_argument("--audit-policies", default="config/audit_policies.yaml", help="audit-layer policy YAML, separate from model assumptions")
    ac.add_argument("--source-registry", default="config/source_registry.yaml", help="source registry with tier/ttl/field rules")
    ac.add_argument("--identifier-master", default="data/real_sources/reference/identifier_master.csv", help="optional identifier master CSV for model applicability")

    sec = sub.add_parser("refresh-sec-financials", help="normalize SEC CompanyFacts financial statement snapshots")
    sec.add_argument("--tickers", required=True, help="comma-separated tickers, e.g. AAPL,MSFT")
    sec.add_argument("--output", default="data/real_sources/sec", help="output directory for raw/cache, normalized snapshots and mapping reports")
    sec.add_argument("--cik-map", default="data/real_sources/reference/sec_company_tickers.json", help="SEC company_tickers JSON or simplified ticker->CIK map")
    sec.add_argument("--companyfacts-dir", default=None, help="optional offline fixture/cache directory containing CIK##########.json files")
    sec.add_argument("--valuation-date", default=None)
    sec.add_argument("--live", action="store_true", help="allow live SEC API fetch when cache/fixture is missing")
    sec.add_argument("--refresh", action="store_true", help="refresh live SEC API data instead of using cache when --live is set")
    sec.add_argument("--continue-on-error", action=argparse.BooleanOptionalAction, default=True)
    sec.add_argument("--user-agent", default=None,
                     help="SEC User-Agent with real contact email (SEC fair-access policy); "
                          "REQUIRED for --live (or set SWS_SEC_USER_AGENT). Offline/cache reads do not need it.")

    fr = sub.add_parser("refresh-rates-fred", help="convert a local FRED/Treasury 10Y export into reviewed-aware curated bond CSV")
    fr.add_argument("--input-csv", required=True, help="local FRED/Treasury export CSV; e.g. DATE,DGS10")
    fr.add_argument("--output", default="data/real_sources/rates/bond_yields_10y_curated.csv")
    fr.add_argument("--country", default="US")
    fr.add_argument("--currency", default="USD")
    fr.add_argument("--tenor", default="10Y")
    fr.add_argument("--series-id", default="DGS10")
    fr.add_argument("--source", default="FRED_DGS10_EXPORT")
    fr.add_argument("--source-url-reference", default="local_operator_export")
    fr.add_argument("--source-as-of", default=None)
    fr.add_argument("--review-status", default="operator_review_required")
    fr.add_argument("--report", default=None)

    ver = sub.add_parser("validate-erp-curated", help="validate ERP curated JSON and review lifecycle")
    ver.add_argument("--input", required=True)
    ver.add_argument("--output", default=None)
    ver.add_argument("--require-reviewed", action="store_true")

    eid = sub.add_parser("enrich-identifiers", help="build Identifier Master CSV from curated universe and optional SEC CIK map")
    eid.add_argument("--input", required=True, help="curated universe CSV")
    eid.add_argument("--cik-map", default=None, help="optional SEC company_tickers JSON or simplified ticker->CIK map")
    eid.add_argument("--output", default="data/real_sources/reference/identifier_master.csv")
    eid.add_argument("--valuation-date", default=None)
    eid.add_argument("--review-status", default="operator_review_required")
    eid.add_argument("--report", default=None)

    sens = sub.add_parser("sensitivity-company", help="run v4.0 P0.5 sensitivity and valuation range audit")
    sens.add_argument("--input", default=None, help="optional company input payload JSON; if omitted use --ticker/--db")
    sens.add_argument("--ticker", default=None, help="ticker for persisted run lookup")
    sens.add_argument("--db", default="data/sws.db")
    sens.add_argument("--run-id", default=None)
    sens.add_argument("--output", required=True, help="output directory for sensitivity_summary.json and sensitivity_report.md")
    sens.add_argument("-a", "--assumptions", default=DEFAULT_ASSUMPTIONS)
    sens.add_argument("--sensitivity-config", default="config/sensitivity.yaml")

    exp = sub.add_parser("explain-company", help="run v4.0 P0.6 deterministic reason-code explanations")
    exp.add_argument("--input", default=None, help="optional company output JSON; if omitted use --ticker/--db")
    exp.add_argument("--ticker", default=None, help="ticker for persisted run lookup")
    exp.add_argument("--db", default="data/sws.db")
    exp.add_argument("--run-id", default=None)
    exp.add_argument("--output", required=True, help="output directory for explanation artifacts")
    exp.add_argument("--mode", choices=["analyst", "plain_english"], default="analyst")
    exp.add_argument("--include-pass", action="store_true", help="also explain PASS checks; default explains FAIL/UNKNOWN only")
    exp.add_argument("--dictionary", default="config/reason_code_dictionary.yaml")
    exp.add_argument("--audit-policies", default="config/audit_policies.yaml")
    exp.add_argument("--source-registry", default="config/source_registry.yaml")
    exp.add_argument("--identifier-master", default="data/real_sources/reference/identifier_master.csv")

    br = sub.add_parser("business-risk-company", help="run v4.0 P0.7 red flags, accounting quality and capital allocation")
    br.add_argument("--input", default=None, help="optional company input payload JSON; if omitted use --ticker/--db")
    br.add_argument("--ticker", default=None, help="ticker for persisted run lookup")
    br.add_argument("--db", default="data/sws.db")
    br.add_argument("--run-id", default=None)
    br.add_argument("--output", required=True, help="output directory for business risk artifacts")

    wl = sub.add_parser("audit-watchlist", help="run v4.0 P0.8 watchlist triage from existing audit artifacts")
    wl.add_argument("--watchlist", required=True, help="local watchlist CSV with ticker, idea_source, priority")
    wl.add_argument("--audit-dir", default="out/audit", help="directory containing *_audit_summary_*.json artifacts")
    wl.add_argument("--business-risk-dir", default=None, help="optional directory containing *_business_risk_package.json artifacts")
    wl.add_argument("--output", required=True, help="output directory for watchlist_audit.json and markdown report")

    th = sub.add_parser("thesis-status", help="run v4.0 P0.9 thesis tracker evaluation")
    th.add_argument("--thesis", required=True, help="local thesis YAML with watch_metrics and invalidation_rules")
    th.add_argument("--audit-summary", default=None, help="optional audit_summary JSON artifact")
    th.add_argument("--business-risk", default=None, help="optional business_risk_package JSON artifact")
    th.add_argument("--sensitivity", default=None, help="optional sensitivity_summary JSON artifact")
    th.add_argument("--output", required=True, help="output directory for thesis_status JSON and markdown report")

    dj = sub.add_parser("record-decision", help="record v4.0 P0.9 research-process decision journal entry")
    dj.add_argument("--decision", required=True, help="decision JSON/YAML with ticker and process decision_type")
    dj.add_argument("--journal", required=True, help="local JSONL decision journal path")
    dj.add_argument("--audit-summary", default=None, help="optional audit_summary JSON artifact captured at decision time")
    dj.add_argument("--thesis-status", default=None, help="optional thesis_status JSON artifact captured at decision time")
    dj.add_argument("--output", required=True, help="output directory for decision record JSON and markdown report")

    pa = sub.add_parser("portfolio-audit", help="run v4.0 P0.10 minimal local portfolio audit")
    pa.add_argument("--holdings", required=True, help="local holdings CSV with ticker, weight and optional sector/factor/thesis/macro labels")
    pa.add_argument("--audit-dir", default="out/audit", help="directory containing audit_summary JSON artifacts")
    pa.add_argument("--business-risk-dir", default=None, help="optional directory containing business_risk_package JSON artifacts")
    pa.add_argument("--thesis-dir", default=None, help="optional directory containing thesis_status JSON artifacts")
    pa.add_argument("--sensitivity-dir", default=None, help="optional directory containing sensitivity_summary JSON artifacts")
    pa.add_argument("--portfolio-id", default="local_portfolio")
    pa.add_argument("--valuation-date", default=None)
    pa.add_argument("--output", required=True, help="output directory for portfolio_audit JSON and markdown report")

    gm = sub.add_parser("generate-memo", help="run v4.0 P0.11 deterministic investment research audit memo")
    gm.add_argument("--audit-summary", default=None, help="audit_summary JSON artifact (required unless --auto)")
    gm.add_argument("--auto", action="store_true",
                    help="P1.8: resolve unset artifact paths from the SQLite artifact index (latest per kind for --ticker); missing kinds stay UNKNOWN")
    gm.add_argument("--ticker", default=None, help="ticker for --auto artifact resolution")
    gm.add_argument("--db", default="data/sws.db", help="SQLite DB with the artifact index (used by --auto and for registering memo outputs)")
    gm.add_argument("--explanations", default=None, help="optional explanation_package JSON artifact")
    gm.add_argument("--sensitivity", default=None, help="optional sensitivity_summary JSON artifact")
    gm.add_argument("--business-risk", default=None, help="optional business_risk_package JSON artifact")
    gm.add_argument("--thesis-status", default=None, help="optional thesis_status JSON artifact")
    gm.add_argument("--decision-record", default=None, help="optional decision_journal record JSON artifact")
    gm.add_argument("--portfolio-audit", default=None, help="optional portfolio_audit JSON artifact")
    gm.add_argument("--memo-type", default="investment_audit")
    gm.add_argument("--mode", choices=["analyst", "plain_english"], default="analyst")
    gm.add_argument("--output", required=True, help="output directory for memo JSON and Markdown")

    cr = sub.add_parser("compare-runs", help="run v4.0 P0.12 deterministic run comparison / change detection")
    cr.add_argument("--previous", required=True, help="previous local run/audit JSON artifact")
    cr.add_argument("--current", required=True, help="current local run/audit JSON artifact")
    cr.add_argument("--output", required=True, help="output directory for run comparison JSON and Markdown")
    cr.add_argument("--comparison-id", default=None)
    cr.add_argument("--artifact-type", default="audit_summary")

    wf = sub.add_parser("workflow-package", help="run v4.0 P0.13 API/dashboard workflow package from existing artifacts")
    wf.add_argument("--audit-summary", default=None, help="audit_summary JSON artifact (required unless --auto)")
    wf.add_argument("--ticker", default=None, help="ticker for --auto artifact resolution")
    wf.add_argument("--explanations", default=None, help="optional explanation_package JSON artifact")
    wf.add_argument("--sensitivity", default=None, help="optional sensitivity_summary JSON artifact")
    wf.add_argument("--business-risk", default=None, help="optional business_risk_package JSON artifact")
    wf.add_argument("--thesis-status", default=None, help="optional thesis_status JSON artifact")
    wf.add_argument("--decision-record", default=None, help="optional decision_journal record JSON artifact")
    wf.add_argument("--portfolio-audit", default=None, help="optional portfolio_audit JSON artifact")
    wf.add_argument("--investment-memo", default=None, help="optional investment_memo JSON artifact")
    wf.add_argument("--run-comparison", default=None, help="optional run_comparison JSON artifact")
    wf.add_argument("--workflow-id", default=None)
    wf.add_argument("--mode", choices=["analyst", "plain_english"], default="analyst")
    wf.add_argument("--output", required=True, help="output directory for workflow package JSON and Markdown")
    wf.add_argument("--auto", action="store_true",
                    help="P1.8: resolve unset artifact paths from the SQLite artifact index (latest per kind for --ticker); missing kinds stay UNKNOWN")
    wf.add_argument("--db", default="data/sws.db", help="SQLite DB with the artifact index (used by --auto and for registering outputs)")

    rel = sub.add_parser("release-package", help="run v4.0 P0.14 MVP release closure manifest")
    rel.add_argument("--repo-root", default=".", help="repository root to inspect")
    rel.add_argument("--release-id", default="v4.0-mvp-p0.14")
    rel.add_argument("--output", required=True, help="output directory for release_manifest JSON and Markdown report")
    rel.add_argument("--validation-dir", default="validation")
    rel.add_argument("--production-readiness", default="NOT_READY", choices=["NOT_READY", "PASS"])
    rel.add_argument("--gates-report", default=None, help="optional gates_report.json to embed")

    bt = sub.add_parser("batch", help="run the watchlist batch and persist to DB")
    bt.add_argument("--watchlist", required=True)
    bt.add_argument("--date", required=True)
    bt.add_argument("--db", required=True)
    bt.add_argument("--universe", required=True)
    bt.add_argument("--market", required=True)
    bt.add_argument("-a", "--assumptions", default=DEFAULT_ASSUMPTIONS)
    bt.add_argument("-s", "--schema", default=DEFAULT_SCHEMA)
    bt.add_argument("--savings-rate", type=float, default=None)
    bt.add_argument("--cpi", type=float, default=None)
    bt.add_argument("--workers", type=int, default=2)

    hi = sub.add_parser("history", help="score history for a ticker/axis from DB")
    hi.add_argument("--db", required=True)
    hi.add_argument("--ticker", required=True)
    hi.add_argument("--axis", required=True)
    hi.add_argument("--since", default=None)

    sc = sub.add_parser("screener", help="latest runs filtered by score AND coverage")
    sc.add_argument("--db", required=True)
    sc.add_argument("--axis", required=True)
    sc.add_argument("--min-score", type=int, default=0)
    sc.add_argument("--min-coverage", type=float, default=0.66)

    args = ap.parse_args(argv)
    if args.cmd == "api":
        import uvicorn
        uvicorn.run("sws_engine.api.app:app", host=args.host, port=args.port, reload=args.reload)
        return 0

    if args.cmd == "legal-scope-report":
        from sws_engine.governance.legal_scope import validate_legal_scope
        rep = validate_legal_scope(args.scope).as_dict()
        if args.output:
            import os
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(rep, fh, indent=2)
            print(json.dumps({"written": args.output, "status": rep["status"]}, indent=2))
        else:
            print(json.dumps(rep, indent=2))
        return 0 if rep["status"] == "PASS" else 2

    if args.cmd == "source-registry-report":
        from sws_engine.sources.real_sources import validate_source_registry
        rep = validate_source_registry(args.registry, require_production=args.require_production).as_dict()
        if args.output:
            import os
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(rep, fh, indent=2)
            print(json.dumps({"written": args.output, "status": rep["status"]}, indent=2))
        else:
            print(json.dumps(rep, indent=2))
        return 0 if rep["status"] == "PASS" else 2

    if args.cmd == "production-readiness":
        from sws_engine.governance.legal_scope import validate_legal_scope
        from sws_engine.sources.real_sources import validate_source_registry
        legal = validate_legal_scope(args.scope).as_dict()
        sources = validate_source_registry(args.registry, require_production=args.require_production).as_dict()
        status = "PASS" if legal["status"] == "PASS" and sources["status"] == "PASS" else "NOT_READY"
        rep = {"status": status, "legal_scope": legal, "source_registry": sources}
        if args.output:
            import os
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(rep, fh, indent=2)
            print(json.dumps({"written": args.output, "status": status}, indent=2))
        else:
            print(json.dumps(rep, indent=2))
        return 0 if status == "PASS" else 2

    if args.cmd == "populate-real-sources":
        from sws_engine.sources.real_sources import populate_real_sources
        rep = populate_real_sources(watchlist_path=args.watchlist, output_dir=args.out_dir, valuation_date=args.valuation_date, refresh=args.refresh)
        print(json.dumps(rep, indent=2))
        return 0 if not rep.get("FAIL") else 2

    if args.cmd == "init-db":
        from sws_engine.db.store import Store
        st = Store(args.db)
        st.init_schema()
        st.close()
        print(json.dumps({"initialized": args.db}))
        return 0

    if args.cmd == "refresh-rates-fred":
        try:
            from sws_engine.rates.curated import build_curated_bond_csv_from_export, validate_bond_curated_csv, write_json_report
            rep = build_curated_bond_csv_from_export(
                input_csv=args.input_csv,
                output_csv=args.output,
                country=args.country,
                currency=args.currency,
                tenor=args.tenor,
                series_id=args.series_id,
                source=args.source,
                source_url_reference=args.source_url_reference,
                source_as_of=args.source_as_of,
                review_status=args.review_status,
            )
            rep["validation"] = validate_bond_curated_csv(args.output, require_reviewed=args.review_status == "reviewed")
            write_json_report(rep, args.report)
            print(json.dumps({
                "status": rep["status"],
                "observations_written": rep["observations_written"],
                "output_csv": rep["output_csv"],
                "review_status": rep["review_status"],
                "report": args.report,
            }, indent=2))
            return 0 if rep["observations_written"] else 2
        except Exception as exc:
            print(f"refresh-rates-fred failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "validate-erp-curated":
        try:
            from sws_engine.rates.curated import validate_erp_curated_json, write_json_report
            rep = validate_erp_curated_json(args.input, require_reviewed=args.require_reviewed)
            write_json_report(rep, args.output)
            print(json.dumps({
                "status": rep["status"],
                "countries_count": rep.get("countries_count"),
                "review_status": rep.get("review_status"),
                "expires_at": rep.get("expires_at"),
                "messages_count": len(rep.get("messages", [])),
                "report": args.output,
            }, indent=2))
            return 0 if rep["status"] == "PASS" else 2
        except Exception as exc:
            print(f"validate-erp-curated failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "enrich-identifiers":
        try:
            from sws_engine.reference.identifier_master import build_identifier_master, validate_identifier_master, write_json_report
            rep = build_identifier_master(
                universe_csv=args.input,
                output_csv=args.output,
                cik_map=args.cik_map,
                as_of=args.valuation_date,
                review_status=args.review_status,
            )
            rep["validation"] = validate_identifier_master(args.output, require_reviewed=args.review_status == "reviewed")
            write_json_report(rep, args.report)
            print(json.dumps({
                "status": rep["status"],
                "rows_written": rep["rows_written"],
                "output_csv": rep["output_csv"],
                "issues_count": len(rep.get("issues", [])),
                "report": args.report,
            }, indent=2))
            return 0 if rep["rows_written"] and rep["status"] != "FAIL" else 2
        except Exception as exc:
            print(f"enrich-identifiers failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "sensitivity-company":
        try:
            from sws_engine.sensitivity.report import sensitivity_company_to_files
            rep = sensitivity_company_to_files(
                args.output,
                input_path=args.input,
                db_path=args.db,
                ticker=args.ticker,
                run_id=args.run_id,
                assumptions_path=args.assumptions,
                sensitivity_config_path=args.sensitivity_config,
            )
            summary = rep["summary"]
            if args.db and not args.input:
                from sws_engine.db.artifacts import register_paths
                register_paths(args.db, ticker=str(summary.get("ticker")), paths=rep["paths"],
                               run_id=summary.get("run_id"))
            print(json.dumps({
                "status": summary.get("status"),
                "ticker": summary.get("ticker"),
                "run_id": summary.get("run_id"),
                "reason_code": summary.get("reason_code"),
                "fragility_level": (summary.get("fragility") or {}).get("fragility_level"),
                "terminal_value_pct": (summary.get("terminal_value_contribution") or {}).get("terminal_value_pct"),
                **rep["paths"],
            }, indent=2))
            return 0 if summary.get("status") != "UNKNOWN" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"sensitivity-company failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "explain-company":
        try:
            from sws_engine.audit.audit_summary import build_audit_summary, load_latest_audit_context_from_db
            from sws_engine.explain.check_explainer import build_explanation_package, write_explanation_artifacts
            if args.input:
                with open(args.input, "r", encoding="utf-8") as fh:
                    output = json.load(fh)
                summary = build_audit_summary(
                    output,
                    audit_policies_path=args.audit_policies,
                    source_registry_path=args.source_registry,
                    identifier_master_path=args.identifier_master,
                )
            else:
                if not args.ticker:
                    raise ValueError("--ticker is required when --input is omitted")
                ctx = load_latest_audit_context_from_db(args.db, args.ticker, run_id=args.run_id)
                output = ctx["output"]
                summary = build_audit_summary(
                    output,
                    run_id=ctx["run_id"],
                    input_payload=ctx.get("input_payload"),
                    assumptions_hash=ctx.get("assumptions_hash"),
                    engine_version=ctx.get("engine_version"),
                    audit_policies_path=args.audit_policies,
                    source_registry_path=args.source_registry,
                    identifier_master_path=args.identifier_master,
                )
            package = build_explanation_package(
                output,
                audit_summary=summary,
                mode=args.mode,
                include_pass=args.include_pass,
                dictionary_path=args.dictionary,
            )
            paths = write_explanation_artifacts(package, args.output)
            if args.db and not args.input:
                from sws_engine.db.artifacts import register_paths
                register_paths(args.db, ticker=str(package.get("ticker")), paths=paths,
                               run_id=package.get("run_id"))
            print(json.dumps({
                "status": "PASS",
                "ticker": package.get("ticker"),
                "checks_explained_count": package.get("checks_explained_count"),
                "unknown_checks_count": package.get("unknown_checks_count"),
                "fail_checks_count": package.get("fail_checks_count"),
                "known_reason_codes_complete_for_package": package.get("known_reason_codes_complete_for_package"),
                **paths,
            }, indent=2))
            return 0
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"explain-company failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "business-risk-company":
        try:
            from sws_engine.audit.risk_signals import business_risk_company_to_files
            rep = business_risk_company_to_files(
                args.output,
                input_path=args.input,
                db_path=args.db,
                ticker=args.ticker,
                run_id=args.run_id,
            )
            package = rep["package"]
            if args.db and not args.input:
                from sws_engine.db.artifacts import register_paths
                register_paths(args.db, ticker=str(package.get("ticker")), paths=rep["paths"],
                               run_id=package.get("run_id"))
            print(json.dumps({
                "status": package.get("status"),
                "ticker": package.get("ticker"),
                "run_id": package.get("run_id"),
                "reason_code": package.get("reason_code"),
                "red_flags_count": package.get("red_flags_summary", {}).get("fail_count"),
                "accounting_quality_grade": package.get("accounting_quality", {}).get("grade"),
                "capital_allocation_assessment": package.get("capital_allocation", {}).get("assessment"),
                **rep["paths"],
            }, indent=2))
            return 0 if package.get("status") != "UNKNOWN" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"business-risk-company failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "audit-watchlist":
        try:
            from sws_engine.research.watchlist import audit_watchlist_to_files
            rep = audit_watchlist_to_files(
                args.watchlist,
                args.output,
                audit_dir=args.audit_dir,
                business_risk_dir=args.business_risk_dir,
            )
            package = rep["package"]
            print(json.dumps({
                "status": package.get("status"),
                "reason_code": package.get("reason_code"),
                "watchlist_size": package.get("watchlist_size"),
                "bucket_counts": package.get("bucket_counts"),
                "manual_review_count": package.get("manual_review_count"),
                "unknown_artifact_count": package.get("unknown_artifact_count"),
                **rep["paths"],
            }, indent=2))
            return 0 if package.get("status") != "UNKNOWN" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"audit-watchlist failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "thesis-status":
        try:
            from sws_engine.research.thesis import thesis_status_to_files
            rep = thesis_status_to_files(
                args.thesis,
                args.output,
                audit_summary_path=args.audit_summary,
                business_risk_path=args.business_risk,
                sensitivity_path=args.sensitivity,
            )
            package = rep["package"]
            print(json.dumps({
                "status": package.get("status"),
                "reason_code": package.get("reason_code"),
                "ticker": package.get("ticker"),
                "thesis_status": package.get("thesis_status"),
                "rules_summary": package.get("rules_summary"),
                **rep["paths"],
            }, indent=2))
            return 0 if package.get("status") != "UNKNOWN" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"thesis-status failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "record-decision":
        try:
            from sws_engine.research.journal import decision_to_files
            rep = decision_to_files(
                args.decision,
                args.journal,
                args.output,
                audit_summary_path=args.audit_summary,
                thesis_status_path=args.thesis_status,
            )
            record = rep["record"]
            print(json.dumps({
                "status": record.get("status"),
                "reason_code": record.get("reason_code"),
                "ticker": record.get("ticker"),
                "decision_type": record.get("decision_type"),
                "decision_id": record.get("decision_id"),
                **rep["paths"],
            }, indent=2))
            return 0 if record.get("status") == "PASS" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"record-decision failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "portfolio-audit":
        try:
            from sws_engine.audit.portfolio_audit import portfolio_audit_to_files
            rep = portfolio_audit_to_files(
                args.holdings,
                args.output,
                audit_dir=args.audit_dir,
                business_risk_dir=args.business_risk_dir,
                thesis_dir=args.thesis_dir,
                sensitivity_dir=args.sensitivity_dir,
                portfolio_id=args.portfolio_id,
                valuation_date=args.valuation_date,
            )
            package = rep["package"]
            print(json.dumps({
                "status": package.get("status"),
                "reason_code": package.get("reason_code"),
                "portfolio_id": package.get("portfolio_id"),
                "holdings_count": package.get("holdings_count"),
                "weighted_data_confidence": (package.get("weighted_data_confidence") or {}).get("level"),
                "weighted_conclusion_risk": (package.get("weighted_conclusion_risk") or {}).get("level"),
                "unknown_exposure_pct": (package.get("unknown_exposure") or {}).get("weight_pct"),
                **rep["paths"],
            }, indent=2))
            return 0 if package.get("status") != "UNKNOWN" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"portfolio-audit failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    def _resolve_auto_artifacts(db_path, ticker, wanted):
        """P1.8: fill unset artifact paths from the SQLite artifact index.

        ``wanted`` maps argparse attribute -> artifact kind (verbatim path
        key registered by the producer). Explicit CLI paths always win;
        kinds with no registered artifact stay None (UNKNOWN downstream).
        Returns {attr: resolution_note} for transparency in stdout.
        """
        from sws_engine.db.artifacts import latest_artifact
        notes = {}
        for attr, kind in wanted.items():
            if getattr(args, attr, None):
                notes[attr] = "explicit"
                continue
            found = latest_artifact(db_path, ticker, kind)
            if found:
                setattr(args, attr, found["path"])
                notes[attr] = f"auto:{found['artifact_id'][:8]}"
            else:
                notes[attr] = "UNKNOWN"
        return notes

    if args.cmd == "generate-memo":
        try:
            auto_notes = None
            if args.auto:
                if not args.ticker:
                    raise ValueError("--ticker is required with --auto")
                auto_notes = _resolve_auto_artifacts(args.db, args.ticker, {
                    "audit_summary": "audit_summary_json",
                    "explanations": "explanations_json",
                    "sensitivity": "sensitivity_summary_json",
                    "business_risk": "business_risk_package_json",
                    "thesis_status": "thesis_status_json",
                    "decision_record": "decision_record_json",
                    "portfolio_audit": "portfolio_audit_json",
                })
            if not args.audit_summary:
                raise ValueError("--audit-summary is required (no registered audit_summary found for --auto)")
            from sws_engine.reporting.investment_memo import investment_memo_to_files
            rep = investment_memo_to_files(
                args.output,
                audit_summary_path=args.audit_summary,
                explanations_path=args.explanations,
                sensitivity_path=args.sensitivity,
                business_risk_path=args.business_risk,
                thesis_status_path=args.thesis_status,
                decision_record_path=args.decision_record,
                portfolio_audit_path=args.portfolio_audit,
                memo_type=args.memo_type,
                mode=args.mode,
            )
            package = rep["package"]
            import os as _os
            if args.db and (args.auto or _os.path.exists(str(args.db))):
                from sws_engine.db.artifacts import register_paths
                register_paths(args.db, ticker=str(package.get("ticker")), paths=rep["paths"],
                               run_id=package.get("run_id"))
            print(json.dumps({
                "status": package.get("status"),
                "reason_code": package.get("reason_code"),
                "ticker": package.get("ticker"),
                "memo_type": package.get("memo_type"),
                **({"auto_resolution": auto_notes} if auto_notes else {}),
                "manual_review_items_count": len(package.get("manual_review_items") or []),
                "recommendation_language_absent": package.get("recommendation_language_absent"),
                **rep["paths"],
            }, indent=2))
            return 0 if package.get("status") != "FAIL" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"generate-memo failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "compare-runs":
        try:
            from sws_engine.research.run_comparison import run_comparison_to_files
            rep = run_comparison_to_files(
                args.output,
                previous_path=args.previous,
                current_path=args.current,
                comparison_id=args.comparison_id,
                artifact_type=args.artifact_type,
            )
            package = rep["package"]
            print(json.dumps({
                "status": package.get("status"),
                "reason_code": package.get("reason_code"),
                "ticker": package.get("ticker"),
                "comparison_id": package.get("comparison_id"),
                "material_change_count": package.get("material_change_count"),
                "new_unknown_count": (package.get("checks_changes") or {}).get("new_unknown_count"),
                "recommendation_language_absent": package.get("recommendation_language_absent"),
                **rep["paths"],
            }, indent=2))
            return 0 if package.get("status") != "FAIL" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"compare-runs failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1


    if args.cmd == "workflow-package":
        try:
            auto_notes = None
            if args.auto:
                if not args.ticker:
                    raise ValueError("--ticker is required with --auto")
                auto_notes = _resolve_auto_artifacts(args.db, args.ticker, {
                    "audit_summary": "audit_summary_json",
                    "explanations": "explanations_json",
                    "sensitivity": "sensitivity_summary_json",
                    "business_risk": "business_risk_package_json",
                    "thesis_status": "thesis_status_json",
                    "decision_record": "decision_record_json",
                    "portfolio_audit": "portfolio_audit_json",
                    "investment_memo": "investment_memo_json",
                    "run_comparison": "comparison_json",
                })
            if not args.audit_summary:
                raise ValueError("--audit-summary is required (no registered audit_summary found for --auto)")
            from sws_engine.research.workflow_package import workflow_package_to_files
            rep = workflow_package_to_files(
                args.output,
                audit_summary_path=args.audit_summary,
                explanations_path=args.explanations,
                sensitivity_path=args.sensitivity,
                business_risk_path=args.business_risk,
                thesis_status_path=args.thesis_status,
                decision_record_path=args.decision_record,
                portfolio_audit_path=args.portfolio_audit,
                investment_memo_path=args.investment_memo,
                run_comparison_path=args.run_comparison,
                workflow_id=args.workflow_id,
                mode=args.mode,
            )
            package = rep["package"]
            import os as _os
            if args.db and (args.auto or _os.path.exists(str(args.db))):
                from sws_engine.db.artifacts import register_paths
                register_paths(args.db, ticker=str(package.get("ticker")), paths=rep["paths"])
            print(json.dumps({
                "status": package.get("status"),
                "reason_code": package.get("reason_code"),
                "ticker": package.get("ticker"),
                "workflow_id": package.get("workflow_id"),
                **({"auto_resolution": auto_notes} if auto_notes else {}),
                "ready_count": (package.get("readiness_summary") or {}).get("ready_count"),
                "manual_review_count": (package.get("readiness_summary") or {}).get("manual_review_count"),
                "total_unknown_indicators": (package.get("readiness_summary") or {}).get("total_unknown_indicators"),
                "recommendation_language_absent": package.get("recommendation_language_absent"),
                **rep["paths"],
            }, indent=2))
            return 0 if package.get("status") != "FAIL" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"workflow-package failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "release-package":
        try:
            from sws_engine.release.manifest import release_to_files
            rep = release_to_files(
                args.output,
                repo_root=args.repo_root,
                release_id=args.release_id,
                validation_dir=args.validation_dir,
                production_readiness=args.production_readiness,
                gates_report_path=args.gates_report,
            )
            manifest = rep["manifest"]
            print(json.dumps({
                "status": manifest.get("status"),
                "reason_code": manifest.get("reason_code"),
                "release_id": manifest.get("release_id"),
                "capabilities_passed": (manifest.get("capability_summary") or {}).get("pass"),
                "capabilities_total": (manifest.get("capability_summary") or {}).get("total"),
                "production_readiness": (manifest.get("scope_guardrails") or {}).get("production_readiness"),
                **rep["paths"],
            }, indent=2))
            return 0 if manifest.get("status") != "BLOCKED" else 2
        except (FileNotFoundError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"release-package failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "refresh-sec-financials":
        try:
            from sws_engine.sec.workflow import refresh_sec_financials
            rep = refresh_sec_financials(
                tickers=args.tickers,
                output_dir=args.output,
                cik_map=args.cik_map,
                companyfacts_dir=args.companyfacts_dir,
                valuation_date=args.valuation_date,
                live=args.live,
                refresh=args.refresh,
                continue_on_error=args.continue_on_error,
                user_agent=args.user_agent,
            )
            print(json.dumps({
                "status": rep["status"],
                "tickers_succeeded": len(rep["tickers_succeeded"]),
                "tickers_failed": len(rep["tickers_failed"]),
                "tickers_skipped": len(rep["tickers_skipped"]),
                "report_path": f"{args.output}/sec_refresh_report.json",
            }, indent=2))
            return 0 if rep["tickers_succeeded"] else 2
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"refresh-sec-financials failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "audit-company":
        try:
            from sws_engine.audit.audit_report import audit_company_from_db_to_files
            rep = audit_company_from_db_to_files(
                args.db,
                args.ticker,
                args.output,
                run_id=args.run_id,
                audit_policies_path=args.audit_policies,
                source_registry_path=args.source_registry,
                identifier_master_path=args.identifier_master,
            )
            summary = rep["summary"]
            paths = rep["paths"]
            from sws_engine.db.artifacts import register_paths
            register_paths(args.db, ticker=str(summary.get("ticker")), paths=paths,
                           run_id=summary.get("run_id"))
            print(json.dumps({
                "status": "PASS_WITH_LIMITATIONS",
                "ticker": summary.get("ticker"),
                "run_id": summary.get("run_id"),
                "data_confidence": summary.get("data_confidence", {}).get("level"),
                "model_applicability": summary.get("model_applicability", {}).get("status"),
                "conclusion_risk": summary.get("conclusion_risk", {}).get("risk_level"),
                "unknown_checks_count": summary.get("data_confidence", {}).get("unknown_checks_count"),
                "provider_degradation_visible": summary.get("provider_degradation_visible"),
                **paths,
            }, indent=2))
            return 0
        except FileNotFoundError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        except Exception as exc:
            print(f"audit-company failed: {exc.__class__.__name__}: {exc}", file=sys.stderr)
            return 1

    if args.cmd == "batch":
        from sws_engine.orchestration.batch import run_batch
        report = run_batch(
            watchlist_path=args.watchlist, valuation_date=args.date,
            db_path=args.db, universe_csv=args.universe, market=args.market,
            assumptions_path=args.assumptions, schema_path=args.schema,
            savings_rate=args.savings_rate, cpi=args.cpi,
            workers=args.workers)
        print(json.dumps(report, indent=2))
        return 0 if not report["FAIL"] else 1

    if args.cmd == "history":
        from sws_engine.db.store import Store
        st = Store(args.db)
        rows = st.score_history(args.ticker, args.axis, args.since)
        st.close()
        print(json.dumps(rows, indent=2))
        return 0

    if args.cmd == "screener":
        from sws_engine.db.store import Store
        st = Store(args.db)
        rows = st.screener(axis=args.axis, min_score=args.min_score,
                           min_coverage=args.min_coverage)
        st.close()
        print(json.dumps(rows, indent=2))
        return 0

    if args.cmd == "build-averages":
        from sws_engine.averages.builder import (build_averages, load_universe,
                                                 save_snapshot)
        snap = build_averages(load_universe(args.universe), as_of=args.date,
                              min_universe_count=args.min_universe,
                              savings_rate=args.savings_rate, cpi=args.cpi)
        path = save_snapshot(snap, args.out_dir, args.market)
        print(json.dumps({"written": path, "warnings": snap["warnings"]}, indent=2))
        return 0

    if args.cmd == "build-payload":
        from sws_engine.orchestration.payload_builder import build_company_payload
        with open(args.averages, "r", encoding="utf-8") as fh:
            averages = json.load(fh)
        payload, pr = build_company_payload(
            snapshot_path=args.snapshot, averages_snapshot=averages,
            industry=args.industry, country=args.country,
            valuation_date=args.date, bond_csv=args.bond_csv,
            erp_json=args.erp_json)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
        print(json.dumps({"written": args.output,
                          "degradations": pr.degradations}, indent=2))
        return 0

    if args.cmd in {"build-payload-yfinance", "company-live", "record-yfinance", "provider-capability"}:
        try:
            if args.cmd == "provider-capability":
                from sws_engine.providers.capability_matrix import live_capability_summary
                cap = live_capability_summary()
                lines = ["# Provider capability report", "", f"Provider: {args.provider}", f"Ticker: {args.ticker or 'n/a'}", "", "| Field | Quality | Source | Fallback |", "|---|---|---|---|"]
                for row in cap["rows"]:
                    lines.append(f"| {row['contract_field']} | {row['source_quality']} | {row['yfinance_source']}:{row['yfinance_attribute']} | {row['fallback_policy']} |")
                with open(args.output, "w", encoding="utf-8") as fh:
                    fh.write("\n".join(lines))
                print(json.dumps({"written": args.output, "counts": cap["counts"]}, indent=2))
                return 0

            from sws_engine.providers.yfinance_live import YFinanceLiveProvider
            provider = YFinanceLiveProvider(refresh=getattr(args, "refresh", False))
            if args.cmd == "record-yfinance":
                snap = provider.fetch_raw_snapshot(args.ticker)
                from sws_engine.data.recorded_fixtures import save_recorded_snapshot
                path = save_recorded_snapshot(args.ticker, snap, args.output)
                print(json.dumps({"written": path, "provider_versions": provider.get_provider_versions()}, indent=2))
                return 0

            payload = provider.build_payload(args.ticker, valuation_date=args.valuation_date, market=args.market, industry=args.industry)
            if args.cmd == "build-payload-yfinance":
                sec_merge_report = None
                if getattr(args, "sec_payload_updates", None):
                    from sws_engine.sec.payload_merge import apply_sec_payload_updates, load_sec_payload_updates
                    sec_merge_report = apply_sec_payload_updates(
                        payload, load_sec_payload_updates(args.sec_payload_updates))
                import os
                os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
                with open(args.output, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=2)
                from sws_engine.providers.yfinance_mapper import capability_summary_from_payload
                result = {"written": args.output, "capability_summary": capability_summary_from_payload(payload)}
                if sec_merge_report is not None:
                    result["sec_merge"] = {
                        "status": sec_merge_report["status"],
                        "reason_code": sec_merge_report["reason_code"],
                        "applied_fields_count": len(sec_merge_report["applied_fields"]),
                        "conflicts_count": len(sec_merge_report["conflicts"]),
                        "skipped_missing_count": len(sec_merge_report["skipped_missing"]),
                    }
                print(json.dumps(result, indent=2))
                return 0

            from sws_engine.orchestration.company_run import run_company_analysis
            out = run_company_analysis(payload, args.assumptions, args.schema)
            import os
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(out, fh, indent=2)
            if args.report:
                from sws_engine.reporting.report import company_report_md
                os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
                with open(args.report, "w", encoding="utf-8") as fh:
                    fh.write(company_report_md(out))
            if args.persist:
                from sws_engine.api.db_adapter import ApiDbAdapter
                db = ApiDbAdapter(args.db, args.assumptions)
                run_id = db.save_company_output(out, payload)
                db.close()
                print(json.dumps({"written": args.output, "run_id": run_id, "warnings": out.get("warnings", [])}, indent=2))
            else:
                print(json.dumps({"written": args.output, "warnings": out.get("warnings", [])}, indent=2))
            return 0
        except Exception as exc:
            print(str(exc), file=sys.stderr)
            return 1

    if args.cmd == "merge-overrides":
        from sws_engine.manual.overrides import load_override_file, merge_overrides
        with open(args.base, "r", encoding="utf-8") as fh:
            base = json.load(fh)
        overrides = [load_override_file(p) for p in args.override]
        merged, report = merge_overrides(base, overrides)
        import os
        os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            json.dump(merged, fh, indent=2)
        report.output_path = args.output
        print(json.dumps(report.__dict__, indent=2))
        return 0

    if args.cmd == "validate-universe":
        from sws_engine.averages.builder import load_universe, save_universe_coverage
        rows = load_universe(args.universe)
        path = save_universe_coverage(rows, args.output)
        print(json.dumps({"written": path}, indent=2))
        return 0

    if args.cmd == "rates-report":
        from sws_engine.rates.sources import rates_source_report
        rep = rates_source_report(bond_csv=args.bond_csv, erp_json=args.erp_json, fx_csv=args.fx_csv)
        if args.output:
            import os
            os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
            with open(args.output, "w", encoding="utf-8") as fh:
                json.dump(rep, fh, indent=2)
            print(json.dumps({"written": args.output}, indent=2))
        else:
            print(json.dumps(rep, indent=2))
        return 0

    if args.cmd == "eod-refresh":
        from sws_engine.ops.eod_refresh import run_eod_refresh
        rep = run_eod_refresh(
            valuation_date=args.date, watchlist_path=args.watchlist, db_path=args.db,
            universe_csv=args.universe, market=args.market, assumptions_path=args.assumptions,
            schema_path=args.schema, bond_csv=args.bond_csv, erp_json=args.erp_json,
            fx_csv=args.fx_csv, logs_dir=args.logs_dir, workers=args.workers,
            provider_mode=args.provider_mode, refresh_live=args.refresh_live)
        print(json.dumps(rep, indent=2))
        return 0 if not rep.get("alerts") else 2

    if args.cmd == "real-dashboard-bootstrap":
        from sws_engine.ops.real_dashboard_bootstrap import run_real_dashboard_bootstrap
        rep = run_real_dashboard_bootstrap(
            tickers=args.tickers, watchlist_path=args.watchlist,
            market=args.market, valuation_date=args.valuation_date,
            db_path=args.db, refresh=args.refresh, persist=args.persist,
            output_dir=args.output_dir, continue_on_error=args.continue_on_error,
            min_success_count=args.min_success_count,
            assumptions_path=args.assumptions, schema_path=args.schema,
            bond_csv=args.bond_csv, erp_json=args.erp_json,
            sec_dir=args.sec_dir)
        print(json.dumps({
            "status": rep["status"],
            "tickers_succeeded": rep["tickers_succeeded"],
            "tickers_failed": rep["tickers_failed"],
            "persisted_count": rep["persisted_count"],
            "warnings_count": rep["warnings_count"],
            "unknown_checks_count": rep["unknown_checks_count"],
            "summary_path": rep["summary_path"],
            "report_path": rep["report_path"],
            "next_commands": rep["next_commands"],
        }, indent=2))
        return 0 if rep["status"] == "PASS_WITH_LIMITATIONS" else 2

    if args.cmd == "create-curated-universe-from-yfinance":
        from sws_engine.ops.curated_universe import create_curated_universe
        rep = create_curated_universe(
            tickers=args.tickers, market=args.market,
            output_path=args.output, refresh=args.refresh,
            report_path=args.report)
        print(json.dumps({
            "output_path": rep["output_path"],
            "rows_written": rep["rows_written"],
            "tickers_failed": rep["tickers_failed"],
            "warnings": rep["warnings"],
            "report_path": rep["report_path"],
        }, indent=2))
        return 0 if rep["rows_written"] > 0 else 2

    with open(args.input, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if args.cmd == "validate-input":
        from sws_engine.manual.overrides import dry_run_report
        report = dry_run_report(payload)
        if args.report:
            import os
            os.makedirs(os.path.dirname(args.report) or ".", exist_ok=True)
            lines = ["# Input validation dry-run", "", f"Ticker: {report.get('ticker')}", f"Provider profile: {report.get('provider_profile')}", "", "## Missing fields", ""]
            lines.extend(f"- {f}" for f in report["missing_fields"])
            lines += ["", "## Impacted checks likely UNKNOWN", ""]
            for chk, fields in report["impacted_checks_likely_unknown"].items():
                lines.append(f"- {chk}: {', '.join(fields)}")
            lines += ["", "## Manual override recommendations", ""]
            for field, tmpl in report["manual_override_recommendations"].items():
                lines.append(f"- {field}: {tmpl}")
            with open(args.report, "w", encoding="utf-8") as fh:
                fh.write("\n".join(lines))
            report["report"] = args.report
        print(json.dumps(report, indent=2))
        return 0

    if args.cmd == "company":
        from sws_engine.orchestration.company_run import run_company_analysis
        out = run_company_analysis(payload, args.assumptions, args.schema,
                                   snapshot_dir=args.snapshot_dir)
        report_fn = "company"
        if getattr(args, "db", None):
            # P1.0 additive: optional single-run persistence so the v4 audit
            # chain (audit-company, sensitivity-company, explain-company, ...)
            # can consume a real run without requiring the batch command.
            # Mirrors the batch persistence path; engine behavior unchanged.
            import sws_engine as _pkg
            from sws_engine.db.store import Store, assumptions_hash
            store = Store(args.db)
            store.init_schema()
            store.upsert_instrument(ticker=out["ticker"])
            snapshot_id = store.save_input_snapshot(out["ticker"], payload)
            run_id = store.create_run(
                ticker=out["ticker"], valuation_date=out.get("valuation_date"),
                snapshot_id=snapshot_id,
                assumptions_hash=assumptions_hash(args.assumptions),
                engine_version=getattr(_pkg, "__version__", "unknown"),
                status="PASS")
            store.save_output(run_id, out)
            store.close()
            print(json.dumps({"persisted_run_id": run_id, "db": args.db,
                              "ticker": out["ticker"]}, indent=2))
    else:
        from sws_engine.config.assumptions_loader import load_assumptions
        from sws_engine.portfolio.portfolio_run import run_portfolio_analysis
        out = run_portfolio_analysis(payload, load_assumptions(args.assumptions))
        report_fn = "portfolio"

    text = json.dumps(out, indent=2)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        print(text)

    if args.report:
        from sws_engine.reporting.report import (company_report_md,
                                                 portfolio_report_md)
        md = company_report_md(out) if report_fn == "company" \
            else portfolio_report_md(out)
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(f"report written: {args.report}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
