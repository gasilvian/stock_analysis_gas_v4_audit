"""P1.8 unit tests for the SQLite artifact index (sws_engine.db.artifacts)."""
import sqlite3

from sws_engine.db.artifacts import (
    init_artifact_schema,
    latest_artifact,
    list_artifacts,
    register_artifact,
    register_paths,
)


def _touch(tmp_path, name, content="{}"):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_register_and_latest_roundtrip(tmp_path):
    db = tmp_path / "idx.db"
    path = _touch(tmp_path, "AAPL_audit_summary_r1.json")
    aid = register_artifact(db, ticker="AAPL", kind="audit_summary_json",
                            path=path, run_id="r1", meta={"note": "x"})
    found = latest_artifact(db, "AAPL", "audit_summary_json")
    assert found is not None
    assert found["artifact_id"] == aid
    assert found["path"] == path
    assert found["run_id"] == "r1"
    assert found["fmt"] == "json"
    assert found["meta"] == {"note": "x"}


def test_latest_returns_newest_and_is_scoped_per_ticker_and_kind(tmp_path):
    db = tmp_path / "idx.db"
    old = _touch(tmp_path, "old.json")
    new = _touch(tmp_path, "new.json")
    other = _touch(tmp_path, "other.json")
    register_artifact(db, ticker="AAPL", kind="audit_summary_json", path=old)
    register_artifact(db, ticker="AAPL", kind="audit_summary_json", path=new)
    register_artifact(db, ticker="MSFT", kind="audit_summary_json", path=other)
    register_artifact(db, ticker="AAPL", kind="sensitivity_summary_json", path=other)

    found = latest_artifact(db, "AAPL", "audit_summary_json")
    assert found["path"] == new  # same-second inserts break ties by rowid
    assert latest_artifact(db, "MSFT", "audit_summary_json")["path"] == other
    assert latest_artifact(db, "MSFT", "sensitivity_summary_json") is None


def test_latest_is_honest_about_missing_data(tmp_path):
    db = tmp_path / "idx.db"
    # No DB file at all -> None, never a fabricated path.
    assert latest_artifact(db, "AAPL", "audit_summary_json") is None
    # DB exists but table absent -> None.
    sqlite3.connect(str(db)).close()
    assert latest_artifact(db, "AAPL", "audit_summary_json") is None
    # Registered but the file was deleted -> skipped by default.
    ghost = _touch(tmp_path, "ghost.json")
    register_artifact(db, ticker="AAPL", kind="audit_summary_json", path=ghost)
    (tmp_path / "ghost.json").unlink()
    assert latest_artifact(db, "AAPL", "audit_summary_json") is None
    assert latest_artifact(db, "AAPL", "audit_summary_json",
                           require_existing_file=False) is not None


def test_register_paths_uses_verbatim_keys_and_skips_empty(tmp_path):
    db = tmp_path / "idx.db"
    j = _touch(tmp_path, "DEMO_audit_summary.json")
    m = _touch(tmp_path, "DEMO_audit_report.md", content="# md")
    registered = register_paths(
        db, ticker="DEMO",
        paths={"audit_summary_json": j, "audit_report_md": m, "empty": ""},
        run_id="r9",
    )
    assert set(registered) == {"audit_summary_json", "audit_report_md"}
    assert latest_artifact(db, "DEMO", "audit_summary_json")["fmt"] == "json"
    assert latest_artifact(db, "DEMO", "audit_report_md")["fmt"] == "md"
    assert latest_artifact(db, "DEMO", "empty") is None


def test_list_artifacts_filters_and_limit(tmp_path):
    db = tmp_path / "idx.db"
    init_artifact_schema(db)
    for i in range(5):
        register_artifact(db, ticker="AAPL", kind="audit_summary_json",
                          path=_touch(tmp_path, f"a{i}.json"))
    register_artifact(db, ticker="MSFT", kind="audit_summary_json",
                      path=_touch(tmp_path, "m.json"))
    assert len(list_artifacts(db)) == 6
    assert len(list_artifacts(db, ticker="AAPL")) == 5
    assert len(list_artifacts(db, ticker="AAPL", limit=2)) == 2
    assert len(list_artifacts(db, kind="audit_summary_json", ticker="MSFT")) == 1
    assert list_artifacts(tmp_path / "absent.db") == []
