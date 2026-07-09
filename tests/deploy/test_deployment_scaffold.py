from __future__ import annotations

from pathlib import Path


def test_docker_files_exist():
    assert Path('Dockerfile').exists()
    assert Path('dashboard.Dockerfile').exists()
    assert Path('docker-compose.yml').exists()
    assert Path('.dockerignore').exists()


def test_docker_compose_has_required_services_and_volumes():
    text = Path('docker-compose.yml').read_text(encoding='utf-8')
    for token in ['api:', 'dashboard:', 'eod-refresh:', 'sws_data:', 'sws_cache:', 'sws_snapshots:']:
        assert token in text


def test_ops_scripts_and_docs_exist():
    for path in [
        'ops/backup.sh',
        'ops/monitoring.sh',
        'ops/monitoring.py',
        'ops/security.md',
        'deploy/README.md',
        'deploy/production_checklist.md',
        '.env.example',
    ]:
        assert Path(path).exists()


def test_deployment_docs_keep_model_risk_language():
    text = Path('deploy/README.md').read_text(encoding='utf-8')
    for token in ['not investment advice', 'not the live Simply Wall St model', 'UNKNOWN', 'coverage']:
        assert token.lower() in text.lower()
