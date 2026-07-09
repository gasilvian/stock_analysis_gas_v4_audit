"""Research workflow helpers for the v4 audit engine."""

from sws_engine.research.journal import build_decision_record, record_decision
from sws_engine.research.thesis import evaluate_thesis, thesis_status_to_files
from sws_engine.research.watchlist import (
    audit_watchlist,
    audit_watchlist_to_files,
    render_watchlist_report_md,
)

__all__ = [
    "audit_watchlist",
    "audit_watchlist_to_files",
    "render_watchlist_report_md",
    "evaluate_thesis",
    "thesis_status_to_files",
    "build_decision_record",
    "record_decision",
]
# P0.12 run comparison module is importable as sws_engine.research.run_comparison.
# P0.13 workflow package module is importable as sws_engine.research.workflow_package.
