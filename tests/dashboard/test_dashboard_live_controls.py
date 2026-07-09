import importlib.util

from dashboard.api_client import ApiClient
from dashboard.components.warnings_panel import important_warnings


def test_company_page_imports_with_live_controls():
    spec = importlib.util.spec_from_file_location("company_page_live", "dashboard/pages/1_Company_View.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert hasattr(module, "main")


def test_api_client_has_analyze_company_live():
    assert hasattr(ApiClient, "analyze_company_live")
    assert hasattr(ApiClient, "build_yfinance_payload")


def test_live_provider_warning_classification():
    warnings = ["LIVE_YFINANCE_PRAGMATIC: provider coverage may be incomplete; UNKNOWN results reflect missing inputs."]
    assert important_warnings(warnings)
