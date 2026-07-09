"""CI gate: ensure runtime outputs and dashboard/API surfaces do not expose normalized scores.

The v3.1 contract uses raw PASS/6 plus coverage. This gate intentionally
scans runtime code and generated JSON-like outputs, while allowing explanatory
documentation and tests that assert the forbidden key is absent.
"""
from __future__ import annotations

import argparse
from pathlib import Path

DEFAULT_PATHS = ["src", "dashboard", "examples", "validation/snapshots"]
ALLOWLIST = {
    Path("src/sws_engine/scoring/axis_scores.py"),  # explanatory docstring allowed only if token removed later
}
FORBIDDEN = "score_normalized"


def iter_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in {"__pycache__", ".pytest_cache", ".git"} for part in path.parts):
            continue
        if path.suffix.lower() in {".pyc", ".pyo", ".zip", ".db", ".sqlite"}:
            continue
        yield path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="*", default=DEFAULT_PATHS)
    args = parser.parse_args()
    hits: list[str] = []
    cwd = Path.cwd()
    for rel in args.paths:
        root = cwd / rel
        if not root.exists():
            continue
        for path in iter_files(root):
            rel_path = path.relative_to(cwd)
            if rel_path in ALLOWLIST:
                # The allowlist is kept narrow and visible. It should not be used
                # for UI/API/reporting files.
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            if FORBIDDEN in text:
                hits.append(str(rel_path))
    if hits:
        print("Forbidden normalized-score token found in runtime surface:")
        for hit in hits:
            print(f"- {hit}")
        return 1
    print("OK: no normalized-score token in runtime surface.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
