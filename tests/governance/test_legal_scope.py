import yaml

from sws_engine.governance.legal_scope import validate_legal_scope


def test_default_legal_scope_passes_internal_use():
    rep = validate_legal_scope("config/legal_scope.yaml").as_dict()
    assert rep["status"] == "PASS"
    assert rep["usage_scope"] == "internal_personal_educational"
    assert rep["commercial_use_enabled"] is False
    assert rep["external_access_enabled"] is False


def test_external_commercial_requires_legal_review(tmp_path):
    p = tmp_path / "legal_scope.yaml"
    p.write_text(yaml.safe_dump({
        "usage_scope": "external_commercial",
        "external_access_enabled": True,
        "commercial_use_enabled": True,
        "legal_review_completed": False,
        "license_constraints_acknowledged": {
            "attribution_required": True,
            "non_commercial_required_without_separate_review": True,
            "share_alike_notice_required_for_published_derivatives": True,
            "not_investment_advice_required": True,
        },
    }), encoding="utf-8")
    rep = validate_legal_scope(p).as_dict()
    assert rep["status"] == "FAIL"
    assert any("commercial_use_enabled" in issue for issue in rep["blocking_issues"])
