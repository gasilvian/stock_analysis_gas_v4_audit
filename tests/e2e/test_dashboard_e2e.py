from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from contextlib import closing

import pytest


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.bind(('127.0.0.1', 0))
        return int(sock.getsockname()[1])


def _wait_for_http(url: str, timeout: int = 60) -> bool:
    import urllib.request
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:  # nosec B310 - local test only
                if resp.status < 500:
                    return True
        except Exception:
            time.sleep(1)
    return False


@pytest.mark.e2e
def test_streamlit_dashboard_e2e_company_and_screener_pages():
    if os.getenv('SWS_RUN_E2E_TESTS') != '1':
        pytest.skip('Set SWS_RUN_E2E_TESTS=1 to run browser/dashboard E2E tests')
    pytest.importorskip('playwright.sync_api')
    from playwright.sync_api import sync_playwright

    api_port = _free_port()
    ui_port = _free_port()
    env = os.environ.copy()
    env['PYTHONPATH'] = 'src'
    env['DASHBOARD_API_URL'] = f'http://127.0.0.1:{api_port}'
    api = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'sws_engine.api.app:app', '--host', '127.0.0.1', '--port', str(api_port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
    )
    ui = subprocess.Popen(
        [sys.executable, '-m', 'streamlit', 'run', 'dashboard/app.py', '--server.address=127.0.0.1', '--server.port', str(ui_port), '--server.headless=true'],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        env=env,
        text=True,
    )
    try:
        assert _wait_for_http(f'http://127.0.0.1:{api_port}/meta/health')
        assert _wait_for_http(f'http://127.0.0.1:{ui_port}')
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f'http://127.0.0.1:{ui_port}', wait_until='networkidle')
            assert 'SWS Snowflake Engine v3.1 Dashboard' in page.text_content('body')
            assert 'Not investment advice' in page.text_content('body')
            browser.close()
    finally:
        ui.terminate()
        api.terminate()
        ui.wait(timeout=20)
        api.wait(timeout=20)
