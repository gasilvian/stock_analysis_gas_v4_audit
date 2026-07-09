"""SQLite artifact index for v4.0 research-audit artifacts (P1.8).

The P0.x series persisted v3.1 engine runs in SQLite but left every v4
artifact (audit summaries, sensitivity, explanations, business risk, memos,
workflow packages, ...) on disk only, addressable solely through filename
conventions. Chaining commands therefore required the operator to hand-wire
6-9 file paths per step — fragile at watchlist scale and identified as an
architectural gap in the Post-P0.14 audit.

This module adds a small, additive index in the same SQLite database:

    artifacts(artifact_id, ticker, kind, run_id, path, fmt, created_at,
              meta_json)

Design principles (aligned with the product doctrine):
- Additive only: no change to the existing Store schema or the canonical
  output contract; the table lives alongside the v3.1 tables.
- Honest resolution: ``latest_artifact`` returns None when nothing is
  registered — callers must surface UNKNOWN, never fabricate a path.
- Kinds are the verbatim path keys already emitted by the producers
  (e.g. ``audit_summary_json``, ``sensitivity_summary_json``); no lossy
  renaming layer that could drift from the producers.
- The index stores paths, not payloads: files remain the source of truth
  and the registry never rewrites or normalizes artifact content.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

ARTIFACTS_SCHEMA = """
CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id TEXT PRIMARY KEY,
    ticker      TEXT NOT NULL,
    kind        TEXT NOT NULL,
    run_id      TEXT,
    path        TEXT NOT NULL,
    fmt         TEXT,
    created_at  TEXT NOT NULL,
    meta_json   TEXT
);
CREATE INDEX IF NOT EXISTS idx_artifacts_ticker_kind_created
    ON artifacts (ticker, kind, created_at);
"""


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt_from_key_or_path(kind: str, path: str) -> str:
    if kind.endswith("_json") or path.endswith(".json"):
        return "json"
    if kind.endswith(("_md", "_report")) or path.endswith(".md"):
        return "md"
    if path.endswith(".jsonl"):
        return "jsonl"
    return "unknown"


def init_artifact_schema(db_path: str | Path) -> None:
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(ARTIFACTS_SCHEMA)
        conn.commit()
    finally:
        conn.close()


def register_artifact(
    db_path: str | Path,
    *,
    ticker: str,
    kind: str,
    path: str | Path,
    run_id: str | None = None,
    fmt: str | None = None,
    meta: Mapping[str, Any] | None = None,
) -> str:
    """Register one artifact file; returns the artifact_id."""
    init_artifact_schema(db_path)
    artifact_id = str(uuid.uuid4())
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "INSERT INTO artifacts (artifact_id, ticker, kind, run_id, path, fmt, created_at, meta_json)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (
                artifact_id,
                str(ticker),
                str(kind),
                run_id,
                str(path),
                fmt or _fmt_from_key_or_path(str(kind), str(path)),
                _now(),
                json.dumps(dict(meta), sort_keys=True) if meta else None,
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return artifact_id


def register_paths(
    db_path: str | Path,
    *,
    ticker: str,
    paths: Mapping[str, str],
    run_id: str | None = None,
    meta: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    """Register a producer's ``paths`` dict verbatim (key -> artifact kind).

    Returns {kind: artifact_id}. Keys whose values are falsy are skipped.
    """
    registered: dict[str, str] = {}
    for kind, path in paths.items():
        if not path:
            continue
        registered[kind] = register_artifact(
            db_path, ticker=ticker, kind=kind, path=path, run_id=run_id, meta=meta
        )
    return registered


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    if d.get("meta_json"):
        try:
            d["meta"] = json.loads(d["meta_json"])
        except (TypeError, ValueError):
            d["meta"] = None
    else:
        d["meta"] = None
    d.pop("meta_json", None)
    return d


def latest_artifact(
    db_path: str | Path,
    ticker: str,
    kind: str,
    *,
    run_id: str | None = None,
    require_existing_file: bool = True,
) -> dict[str, Any] | None:
    """Return the newest registered artifact for (ticker, kind), or None.

    None means UNKNOWN to callers — never substitute a guessed path. When
    ``require_existing_file`` is true (default), rows whose file no longer
    exists on disk are skipped so stale index entries cannot resurrect
    deleted artifacts.
    """
    p = Path(db_path)
    if not p.exists():
        return None
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        try:
            query = (
                "SELECT * FROM artifacts WHERE ticker = ? AND kind = ?"
                + (" AND run_id = ?" if run_id else "")
                + " ORDER BY created_at DESC, rowid DESC"
            )
            params: tuple[Any, ...] = (ticker, kind, run_id) if run_id else (ticker, kind)
            rows = conn.execute(query, params).fetchall()
        except sqlite3.OperationalError:
            return None  # table absent: nothing registered yet
    finally:
        conn.close()
    for row in rows:
        d = _row_to_dict(row)
        if require_existing_file and not Path(d["path"]).exists():
            continue
        return d
    return None


def list_artifacts(
    db_path: str | Path,
    *,
    ticker: str | None = None,
    kind: str | None = None,
    limit: int = 100,
) -> list[dict[str, Any]]:
    p = Path(db_path)
    if not p.exists():
        return []
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    try:
        clauses, params = [], []
        if ticker:
            clauses.append("ticker = ?")
            params.append(ticker)
        if kind:
            clauses.append("kind = ?")
            params.append(kind)
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        try:
            rows = conn.execute(
                f"SELECT * FROM artifacts{where} ORDER BY created_at DESC, rowid DESC LIMIT ?",
                (*params, int(limit)),
            ).fetchall()
        except sqlite3.OperationalError:
            return []
    finally:
        conn.close()
    return [_row_to_dict(r) for r in rows]
