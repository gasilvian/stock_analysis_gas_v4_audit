"""SEC EDGAR ingestion foundation for v4.0 audit engine.

P0.3 scope is deliberately narrow and offline-testable: resolve CIKs, load
CompanyFacts JSON from cache/fixture, normalize a small statement snapshot, and
produce a mapping report. It does not change the core v3.1 output schema or any
financial formulas.
"""

__all__ = [
    "cik_resolver",
    "companyfacts_adapter",
    "xbrl_tag_resolver",
    "statement_snapshot",
    "mapping_report",
]
