from __future__ import annotations

from pathlib import Path


def test_github_workflows_exist():
    assert Path('.github/workflows/ci.yml').exists()
    assert Path('.github/workflows/release.yml').exists()


def test_ci_gate_scripts_exist():
    for path in [
        'scripts/ci/check_no_score_normalized.py',
        'scripts/ci/validate_demo_outputs.py',
        'scripts/ci/check_attribution_footer.py',
        'scripts/ci/check_workflow_package_guardrails.py',
        'scripts/ci/clean_artifacts.py',
    ]:
        assert Path(path).exists()


def test_ci_workflow_has_required_gates():
    text = Path('.github/workflows/ci.yml').read_text(encoding='utf-8')
    for token in [
        'ruff check',
        'python -m pytest -q',
        'validate_demo_outputs.py',
        'check_no_score_normalized.py',
        'check_attribution_footer.py',
    ]:
        assert token in text


def test_release_workflow_has_gold_gate_and_artifact():
    text = Path('.github/workflows/release.yml').read_text(encoding='utf-8')
    assert 'tests/gold' in text
    assert 'upload-artifact' in text
    assert 'sws-snowflake-engine-release.zip' in text
