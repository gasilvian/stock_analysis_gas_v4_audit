from __future__ import annotations

import json
from ops.monitoring import inspect_latest_eod


def test_monitoring_alerts_on_batch_failure_ratio_over_20pct(tmp_path):
    logs = tmp_path / "logs"
    logs.mkdir()
    log = logs / "eod_refresh_2026-07-08.json"
    log.write_text(json.dumps({
        "batch_report": {
            "PASS": [{"ticker": "A"}, {"ticker": "B"}],
            "FAIL": [{"ticker": "C"}],
            "SKIPPED": [],
        },
        "alerts": [],
    }), encoding="utf-8")
    report = inspect_latest_eod(logs)
    assert report["latest_eod_log"].endswith("eod_refresh_2026-07-08.json")
    assert any("batch failures exceed 20%" in alert for alert in report["alerts"])
