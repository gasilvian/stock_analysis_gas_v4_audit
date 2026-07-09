"""Minimal operational health check for internal deployments.

The monitor intentionally keeps model-risk status visible. It does not mark the
product production-ready; it only checks API health and the latest EOD log. If
more than 20% of batch/live snapshot items failed, it emits an alert in the
monitoring JSON and returns a non-zero status for schedulers.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

FAILURE_ALERT_THRESHOLD = 0.20


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fetch_json(url: str) -> tuple[int, dict | None, str | None]:
    try:
        with urlopen(url, timeout=10) as resp:  # nosec B310 - internal health endpoint only
            body = resp.read().decode("utf-8")
            return resp.status, json.loads(body), None
    except Exception as exc:  # pragma: no cover - operational script
        return 0, None, str(exc)


def _failure_ratio(section: dict | None) -> tuple[int, int, float]:
    if not isinstance(section, dict):
        return 0, 0, 0.0
    fail_count = len(section.get("FAIL", []) or [])
    total = sum(len(section.get(k, []) or []) for k in ("PASS", "FAIL", "SKIPPED"))
    if total <= 0:
        return fail_count, total, 0.0
    return fail_count, total, fail_count / total


def _eod_alerts(payload: dict) -> list[str]:
    alerts = list(payload.get("alerts", []) or [])
    for label, key in (("batch", "batch_report"), ("live snapshot", "snapshot_refresh")):
        fail_count, total, ratio = _failure_ratio(payload.get(key))
        if total and ratio > FAILURE_ALERT_THRESHOLD:
            alerts.append(f"ALERT: {label} failures exceed 20% ({fail_count}/{total})")
    # Deduplicate while preserving order.
    deduped: list[str] = []
    for alert in alerts:
        if alert not in deduped:
            deduped.append(alert)
    return deduped


def inspect_latest_eod(logs_dir: Path) -> dict:
    logs = sorted(logs_dir.glob("eod_refresh_*.json"))
    if not logs:
        return {"latest_eod_log": None, "alerts": ["NO_EOD_LOG_FOUND"]}
    latest = logs[-1]
    try:
        payload = json.loads(latest.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"latest_eod_log": str(latest), "alerts": [f"UNREADABLE_EOD_LOG: {exc}"]}
    alerts = _eod_alerts(payload)
    return {"latest_eod_log": str(latest), "eod_summary": payload, "alerts": alerts}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--logs-dir", default="logs")
    args = parser.parse_args()
    logs_dir = Path(args.logs_dir)
    logs_dir.mkdir(parents=True, exist_ok=True)
    status, health, error = fetch_json(args.api_url.rstrip("/") + "/meta/health")
    report = {
        "checked_at": utc_now(),
        "api_url": args.api_url,
        "api_status_code": status,
        "api_error": error,
        "api_health": health,
    }
    report.update(inspect_latest_eod(logs_dir))
    out = logs_dir / f"monitoring_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    out.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    alerts = report.get("alerts", []) or []
    print(json.dumps({"written": str(out), "api_status_code": status, "api_ok": status == 200, "alerts": alerts}, indent=2))
    if status != 200:
        return 2
    return 3 if alerts else 0


if __name__ == "__main__":
    raise SystemExit(main())
