"""CI gate: dashboard footer must preserve disclaimer and attribution."""
from __future__ import annotations

from pathlib import Path

REQUIRED = [
    "Not investment advice",
    "Not the live Simply Wall St model",
    "Derived from public Simply Wall St GitHub methodology",
]


def main() -> int:
    path = Path("dashboard/components/footer.py")
    if not path.exists():
        print("Missing dashboard/components/footer.py")
        return 1
    text = path.read_text(encoding="utf-8")
    missing = [s for s in REQUIRED if s not in text]
    if missing:
        print("Footer attribution/disclaimer check failed:")
        for item in missing:
            print(f"- missing: {item}")
        return 1
    print("OK: dashboard footer attribution and disclaimer present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
