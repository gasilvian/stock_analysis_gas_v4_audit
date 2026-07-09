from __future__ import annotations

import importlib
import importlib.util
import pathlib


def _import_path(path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_dashboard_modules_import_without_engine_or_db_side_effects():
    importlib.import_module("dashboard.app")
    importlib.import_module("dashboard.api_client")
    for module in [
        "dashboard.components.badges",
        "dashboard.components.footer",
        "dashboard.components.snowflake_radar",
        "dashboard.components.score_cards",
        "dashboard.components.warnings_panel",
        "dashboard.components.lineage_panel",
        "dashboard.components.checks_table",
        "dashboard.components.valuation_card",
        "dashboard.components.portfolio_components",
        "dashboard.components.audit_workflow",
    ]:
        importlib.import_module(module)


def test_dashboard_pages_import_as_smoke():
    pages = pathlib.Path("dashboard/pages")
    for page in sorted(pages.glob("*.py")):
        module = _import_path(page)
        assert hasattr(module, "main")


def test_dashboard_does_not_import_engine_or_persistence_directly():
    forbidden = ["run_company_analysis", "sws_engine.db", "sqlite3", "sws_engine.orchestration.company_run"]
    for path in pathlib.Path("dashboard").rglob("*.py"):
        if path.name == "api_client.py":
            # API client must use HTTP, not backend internals.
            pass
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text, f"Forbidden direct backend dependency {token} in {path}"
