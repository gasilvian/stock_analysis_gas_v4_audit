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

    # Field lineage providers whose declared quality is trusted at check time.
    # yfinance-sourced fields stay blanket approximation per the pragmatic
    # doctrine; explicit enrichment/injection sources carry their own truth.
    TRUSTED_LINEAGE_PROVIDERS = {"sec_companyfacts", "curated_rates", "manual_override"}

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
        # P1.3b (B4/B8): fields enriched from trusted explicit sources (SEC
        # official filings, curated rates injection, manual overrides) keep
        # their declared lineage quality instead of being blanket-stamped
        # approximation — otherwise SEC exact/E0 enrichment would be invisible
        # to every check. Fields without such lineage keep the pragmatic
        # approximation default, so pure-yfinance payloads are unchanged.
        field_lineage = ((payload.get("lineage") or {}).get("field_lineage") or {})
        for k, v in payload.items():
            if v is not None and k not in ("lineage", "provider_profile"):
                lin = field_lineage.get(k) or {}
                lin_provider = str(lin.get("provider") or lin.get("source_id") or "")
                lin_quality = lin.get("source_quality")
                if lin_provider in self.TRUSTED_LINEAGE_PROVIDERS and lin_quality:
                    quality.setdefault(k, str(lin_quality))
                else:
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
