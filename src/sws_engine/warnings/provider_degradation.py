"""Provider degradation and run-level warnings (visible in output)."""

DEMO_WARNING = ("DEMO_FIXTURE_ONLY: synthetic input data used for "
                "development/testing, not real company analysis")
DISCLAIMER = ("NOT_INVESTMENT_ADVICE: quantitative exploratory analysis of a "
              "public historical methodology; not the live Simply Wall St model")


def collect_warnings(payload: dict, provider_result, checks) -> list:
    warnings = [DISCLAIMER]
    if payload.get("demo_fixture") is True:
        warnings.append(DEMO_WARNING)
    if payload.get("synthetic_data") is True:
        warnings.append(
            "SYNTHETIC_CURATED_DATA: inputs are synthetic construction data, "
            "not real market data")
    warnings.extend(payload.get("builder_warnings") or [])
    warnings.extend(provider_result.degradations)
    n_provider_limited = sum(
        1 for c in checks
        if c.result == "UNKNOWN" and c.reason_code == "PROVIDER_LIMITATION")
    if n_provider_limited:
        warnings.append(
            f"PROVIDER_DEGRADATION: {n_provider_limited} checks UNKNOWN due to "
            f"provider limitations")
    warnings = list(dict.fromkeys(warnings))  # dedupe, keep order
    n_unknown = sum(1 for c in checks if c.result == "UNKNOWN")
    if n_unknown:
        warnings.append(
            f"COVERAGE: {n_unknown}/30 checks UNKNOWN; high scores with low "
            f"coverage are not comparable to high scores with high coverage")
    return warnings
