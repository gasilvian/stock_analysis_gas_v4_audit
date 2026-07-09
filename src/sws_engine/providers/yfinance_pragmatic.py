"""yfinance_pragmatic stub (no live integration in MVP).

Fields the public SWS methodology needs but yfinance cannot reliably supply
are marked source_quality=missing with PROVIDER_LIMITATION degradations,
so dependent checks become UNKNOWN and warnings are visible in output
(risk_register.md: 'Using yfinance as if it were SWS/S&P Capital IQ')."""
from sws_engine.core.enums import ProviderProfile, SourceQuality
from sws_engine.providers.base import BaseProvider, ProviderResult

# Inputs documented as unavailable/unreliable in yfinance for the public
# SWS methodology (source_map.md: yfinance provider observations, E3).
YFINANCE_UNAVAILABLE_FIELDS = (
    "fcf_estimates",
    "analyst_estimates_weighted",
    "roe_3y_estimate",
    "estimated_payout_3y",
    "intangible_assets",          # inconsistent -> tangible BV not exact
    "market_averages",            # SWS-style percentiles/medians not provided
    "industry_averages",
)


class YFinancePragmaticProvider(BaseProvider):
    profile = ProviderProfile.YFINANCE_PRAGMATIC.value

    def prepare(self, payload: dict) -> ProviderResult:
        payload = dict(payload)
        quality = {}
        degradations = []
        for f in YFINANCE_UNAVAILABLE_FIELDS:
            if payload.get(f) is None:
                quality[f] = SourceQuality.MISSING.value
                degradations.append(
                    f"PROVIDER_LIMITATION: '{f}' not available via yfinance; "
                    f"dependent checks degraded to UNKNOWN"
                )
        for k, v in payload.items():
            if v is not None and k not in ("lineage", "provider_profile"):
                quality.setdefault(k, SourceQuality.APPROXIMATION.value)
        degradations.append(
            "yfinance_pragmatic outputs are pragmatic approximations, "
            "not a faithful replication of the SWS methodology"
        )
        return ProviderResult(payload=payload, field_quality=quality,
                              degradations=degradations)


def get_provider(profile: str) -> BaseProvider:
    from sws_engine.providers.manual_inputs import ManualInputsProvider
    if profile == ProviderProfile.YFINANCE_PRAGMATIC.value:
        return YFinancePragmaticProvider()
    return ManualInputsProvider()
