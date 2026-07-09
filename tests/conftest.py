import copy
import json
import os

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSUMPTIONS = os.path.join(ROOT, "config", "assumptions.yaml")
SCHEMA = os.path.join(ROOT, "schemas", "output_schema.json")
FIXTURE = os.path.join(ROOT, "tests", "fixtures",
                       "demo_complete_non_financial.json")


@pytest.fixture
def assumptions_path():
    return ASSUMPTIONS


@pytest.fixture
def schema_path():
    return SCHEMA


@pytest.fixture
def demo_payload():
    with open(FIXTURE, "r", encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture
def run(assumptions_path, schema_path):
    from sws_engine import run_company_analysis

    def _run(payload):
        return run_company_analysis(payload, assumptions_path, schema_path)
    return _run


@pytest.fixture
def demo_copy(demo_payload):
    def _copy():
        return copy.deepcopy(demo_payload)
    return _copy
