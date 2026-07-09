"""Markdown report generator for company/portfolio outputs. Reports always
carry the non-advice disclaimer (risk_register.md)."""

AXES = ("value", "future", "past", "health", "dividend")


def company_report_md(out: dict) -> str:
    L = []
    L.append(f"# Snowflake Report - {out['ticker']} ({out['exchange']})")
    L.append(f"\nValuation date: {out['valuation_date']}  ")
    L.append(f"Provider profile: `{out['provider_profile']}`  ")
    L.append(f"Valuation: `{out['valuation_model']}` / "
             f"`{out['valuation_variant']}` "
             f"(source class {out['valuation_model_source_class']})\n")
    fv, price, disc = out.get("fair_value"), out.get("price"), out.get("discount_pct")
    L.append(f"Fair value: {fv if fv is not None else 'n/a'} | "
             f"Price: {price if price is not None else 'n/a'} | "
             f"Discount: {f'{disc:.1%}' if disc is not None else 'n/a'}\n")
    L.append("## Snowflake scores\n")
    L.append("| Axis | Score (PASS/6) | Known | Unknown | Coverage |")
    L.append("|---|---|---|---|---|")
    for axis in AXES:
        s = out["scores"][axis]
        L.append(f"| {axis} | {s['score_raw']}/6 | {s['known_checks_count']} "
                 f"| {s['unknown_checks_count']} | {s['coverage_pct']:.0%} |")
    L.append("\n## Checks\n")
    L.append("| Axis | # | Check | Result | Reason | Quality | Class |")
    L.append("|---|---|---|---|---|---|---|")
    for c in out["checks"]:
        L.append(f"| {c['axis']} | {c['id']} | {c['name']} | {c['result']} "
                 f"| {c['reason_code']} | {c['source_quality']} "
                 f"| {c['source_class']} |")
    if out.get("warnings"):
        L.append("\n## Warnings\n")
        for w in out["warnings"]:
            L.append(f"- {w}")
    L.append("\n---\n*Quantitative exploratory analysis of a public "
             "historical methodology. Not investment advice. Not the live "
             "Simply Wall St model.*")
    return "\n".join(L)


def portfolio_report_md(out: dict) -> str:
    L = [f"# Portfolio Report ({out['portfolio_type']})",
         f"\nValuation date: {out['valuation_date']}\n"]
    if out.get("snowflake"):
        L.append("## Portfolio Snowflake (weighted)\n")
        L.append("| Axis | Score |")
        L.append("|---|---|")
        for axis, score in out["snowflake"]["axes"].items():
            L.append(f"| {axis} | {score:.2f} |")
        if out["snowflake"].get("excluded_etf"):
            L.append(f"\nExcluded from Snowflake (ETF/funds): "
                     f"{', '.join(out['snowflake']['excluded_etf'])}")
    L.append("\n## Returns per position\n")
    L.append("| Ticker | Gain | Total Return | AYI | CAGR |")
    L.append("|---|---|---|---|---|")
    for t, r in (out.get("returns_per_position") or {}).items():
        if r is None:
            L.append(f"| {t} | n/a | n/a | n/a | n/a |")
            continue
        cagr = f"{r['cagr']:.2%}" if r["cagr"] is not None else "suppressed (AYI<1)"
        L.append(f"| {t} | {r['gain']:.2f} | {r['total_return']:.2%} "
                 f"| {r['avg_years_invested']:.2f} | {cagr} |")
    for w in out.get("warnings", []):
        L.append(f"\n- {w}")
    return "\n".join(L)
