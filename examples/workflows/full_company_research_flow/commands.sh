#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH=src python scripts/release/run_local_mvp_smoke.py --repo-root . --output out/p14_ci --release-id v4.0-mvp-p0.14
PYTHONPATH=src python scripts/ci/check_release_manifest.py out/p14_ci
