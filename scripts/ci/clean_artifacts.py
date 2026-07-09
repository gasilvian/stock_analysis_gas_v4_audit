"""Remove local build/test artifacts before packaging."""
from __future__ import annotations

import shutil
from pathlib import Path

PATTERNS = ["__pycache__", ".pytest_cache", "*.pyc", "*.pyo", "*.egg-info"]


def main() -> int:
    root = Path.cwd()
    removed = []
    for pattern in PATTERNS:
        for path in root.rglob(pattern):
            if path.name == ".git":
                continue
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)
            else:
                path.unlink(missing_ok=True)
            removed.append(str(path.relative_to(root)))
    print("Removed artifacts:")
    for path in removed[:200]:
        print(f"- {path}")
    if len(removed) > 200:
        print(f"... {len(removed) - 200} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
