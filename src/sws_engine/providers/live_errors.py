"""Controlled errors for optional live-data providers."""


class LiveProviderError(RuntimeError):
    """Base class for sanitized live provider failures."""


class YFinanceDependencyError(LiveProviderError):
    """Raised when the optional yfinance dependency is not installed."""


class LiveProviderFetchError(LiveProviderError):
    """Raised for controlled provider fetch failures."""
