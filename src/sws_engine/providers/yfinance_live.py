"""Optional yfinance live provider.

This adapter feeds provider_profile=yfinance_pragmatic. It is intentionally
conservative and audited: missing provider components become missing payload
fields and visible warnings rather than invented inputs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from sws_engine.data.cache import JsonDiskCache
from sws_engine.providers.live_errors import LiveProviderFetchError, YFinanceDependencyError
from sws_engine.providers.yfinance_mapper import capability_summary_from_payload, map_yfinance_snapshot_to_input_payload


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _jsonable(value: Any) -> Any:
    """Convert pandas/yfinance structures into JSON-safe objects."""
    try:
        import pandas as pd  # type: ignore
    except Exception:  # pragma: no cover - pandas available in dev normally
        pd = None
    if pd is not None:
        if isinstance(value, pd.DataFrame):
            # orient as row -> date -> value, matching mapper support.
            out: dict[str, dict[str, Any]] = {}
            for idx, row in value.iterrows():
                out[str(idx)] = {str(k)[:10]: _jsonable(v) for k, v in row.dropna().items()}
            return out
        if isinstance(value, pd.Series):
            return {str(k)[:10]: _jsonable(v) for k, v in value.dropna().items()}
        if isinstance(value, pd.Timestamp):
            return value.date().isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    try:
        # NaN check without importing numpy.
        if isinstance(value, float) and value != value:
            return None
    except Exception:
        pass
    return value


class YFinanceLiveProvider:
    def __init__(self, cache: JsonDiskCache | None = None, timeout: int = 30, refresh: bool = False):
        self.cache = cache or JsonDiskCache("data/cache/yfinance")
        self.timeout = timeout
        self.refresh = refresh
        try:
            import yfinance as yf  # type: ignore
        except Exception as exc:  # pragma: no cover - tested by monkeypatch/import absence
            self.yf = None
            self.provider_version = "not-installed"
            self._dependency_error = exc
        else:
            self.yf = yf
            self.provider_version = getattr(yf, "__version__", "unknown")
            self._dependency_error = None

    def _require_yfinance(self):
        if self.yf is None:
            raise YFinanceDependencyError('Install live extra: pip install -e ".[live]"') from self._dependency_error

    def get_provider_versions(self) -> dict:
        return {"yfinance": self.provider_version, "adapter": "stepA-live-provider-v1"}

    def fetch_raw_snapshot(self, ticker: str) -> Dict[str, Any]:
        self._require_yfinance()
        key = f"{ticker.upper()}_{datetime.now(timezone.utc).date().isoformat()}_{self.provider_version}_full_snapshot"
        if not self.refresh:
            cached = self.cache.get_with_metadata(key, ttl_days=1)
            if cached is not None:
                return cached
        errors: list[str] = []
        warnings: list[str] = []
        raw: Dict[str, Any] = {
            "ticker": ticker.upper(),
            "fetched_at": _utc_now(),
            "provider": "yfinance",
            "provider_version": self.provider_version,
            "info": {},
            "fast_info": {},
            "history": [],
            "balance_sheet": {},
            "financials": {},
            "cashflow": {},
            "dividends": {},
            "splits": {},
            "actions": {},
            "errors": errors,
            "warnings": warnings,
        }
        try:
            t = self.yf.Ticker(ticker)
        except Exception as exc:
            raise LiveProviderFetchError(f"Could not initialize yfinance ticker {ticker}: {exc.__class__.__name__}") from exc

        def collect(name: str, getter):
            try:
                raw[name] = _jsonable(getter())
            except Exception as exc:
                raw[name] = {} if name != "history" else []
                msg = f"PROVIDER_COMPONENT_MISSING: {name} fetch failed with {exc.__class__.__name__}"
                warnings.append(msg)

        collect("info", lambda: getattr(t, "info", {}) or {})
        collect("fast_info", lambda: dict(getattr(t, "fast_info", {}) or {}))
        collect("history", lambda: getattr(t, "history")(period="5d").reset_index().to_dict(orient="records"))
        collect("balance_sheet", lambda: getattr(t, "balance_sheet", None) if getattr(t, "balance_sheet", None) is not None else t.get_balance_sheet())
        collect("financials", lambda: getattr(t, "financials", None) if getattr(t, "financials", None) is not None else getattr(t, "income_stmt", {}))
        collect("cashflow", lambda: getattr(t, "cashflow", {}))
        collect("dividends", lambda: getattr(t, "dividends", {}))
        collect("splits", lambda: getattr(t, "splits", {}))
        collect("actions", lambda: getattr(t, "actions", {}))
        return self.cache.put_with_metadata(key, raw, ttl_days=1, provider="yfinance", provider_version=self.provider_version)

    def build_payload(self, ticker: str, valuation_date: str | None = None,
                      market: str | None = None, industry: str | None = None,
                      overrides: dict | None = None) -> dict:
        raw = self.fetch_raw_snapshot(ticker)
        return map_yfinance_snapshot_to_input_payload(raw, valuation_date=valuation_date, market=market, industry=industry, overrides=overrides)

    def build_lineage(self, raw_snapshot: dict, mapped_fields: dict | None = None) -> dict:
        payload = map_yfinance_snapshot_to_input_payload(raw_snapshot)
        return payload.get("lineage", {})

    def capability_summary(self, payload: dict) -> dict:
        return capability_summary_from_payload(payload)
