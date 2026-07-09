"""Auxiliary sensitivity layer for the v4.0 Research Audit Engine.

This package is additive: it does not change valuation formulas, checks,
growth, portfolio logic or output_schema.json.
"""

from sws_engine.sensitivity.scenario_runner import run_sensitivity
from sws_engine.sensitivity.report import sensitivity_company_to_files, sensitivity_report_md

__all__ = ["run_sensitivity", "sensitivity_company_to_files", "sensitivity_report_md"]
