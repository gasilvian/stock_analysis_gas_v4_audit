"""Assemble the company-analysis output object (SPEC v3.1 section 2.3)."""


def build_output(*, ticker, exchange, valuation_date, provider_profile,
                 valuation_model, valuation_variant, valuation_model_source_class,
                 fair_value, price, discount_pct, scores, checks, lineage,
                 warnings) -> dict:
    return {
        "ticker": ticker,
        "exchange": exchange,
        "valuation_date": valuation_date,
        "provider_profile": provider_profile,
        "valuation_model": valuation_model,
        "valuation_variant": valuation_variant,
        "valuation_model_source_class": valuation_model_source_class,
        "fair_value": fair_value,
        "price": price,
        "discount_pct": discount_pct,
        "scores": scores,
        "checks": [c.to_dict() for c in checks],
        "lineage": lineage,
        "warnings": warnings,
    }
