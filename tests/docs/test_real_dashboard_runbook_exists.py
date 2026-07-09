import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RUNBOOK = os.path.join(ROOT, "docs", "real_dashboard_bootstrap_runbook.md")


def test_real_dashboard_runbook_exists_and_covers_required_topics():
    assert os.path.exists(RUNBOOK)
    with open(RUNBOOK, "r", encoding="utf-8") as fh:
        text = fh.read()
    for needle in [
        "real-dashboard-bootstrap",
        "create-curated-universe-from-yfinance",
        "uvicorn sws_engine.api.app:app",
        "streamlit run dashboard/app.py",
        "UNKNOWN",
        "production-readiness",
        "MISSING_CURATED_RATE_SOURCE",
        "MISSING_CURATED_ERP_SOURCE",
        "not investment advice",
    ]:
        assert needle in text, f"runbook missing required topic: {needle}"
