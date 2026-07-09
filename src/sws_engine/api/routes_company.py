"""Company-analysis API routes."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Query

import sws_engine
from sws_engine.api.config import Settings, get_settings
from sws_engine.api.db_adapter import AXES, ApiDbAdapter
from sws_engine.api.deps import get_db_adapter
from sws_engine.api.errors import bad_request, internal_error, not_found, unprocessable
from sws_engine.api.schemas import ApiRunMetadata, ApiWrappedResponse, ChecksQueryResponse, HistoryResponse
from sws_engine.api.schemas import CompanyAnalyzeRequest
from sws_engine.api.security import require_api_key
from sws_engine.orchestration.company_run import run_company_analysis

router = APIRouter(tags=["company"], dependencies=[Depends(require_api_key)])


@router.post("/analyze/company", response_model=ApiWrappedResponse)
def analyze_company(
    request: CompanyAnalyzeRequest,
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    try:
        snapshot_dir = "validation/snapshots" if request.snapshot else None
        output = run_company_analysis(
            request.input_payload,
            settings.assumptions_path,
            settings.schema_path,
            snapshot_dir=snapshot_dir,
        )
    except KeyError as exc:
        raise unprocessable("Invalid company payload; required field is missing.", {"field": str(exc)})
    except ValueError as exc:
        raise unprocessable("Invalid company payload.", {"error": str(exc)})
    except Exception as exc:
        raise internal_error(f"Company analysis failed: {exc.__class__.__name__}")

    run_id = db.save_company_output(output, request.input_payload) if request.persist else None
    return ApiWrappedResponse(
        metadata=ApiRunMetadata(
            run_id=run_id,
            persisted=bool(request.persist),
            engine_version=sws_engine.__version__,
            api_version=settings.api_version,
            data_layer=settings.data_layer,
        ),
        output=output,
    )


@router.get("/companies/{ticker}/latest", response_model=ApiWrappedResponse)
def latest_company(
    ticker: str,
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    rec = db.get_latest_company_with_run_id(ticker)
    if not rec:
        raise not_found(f"No persisted company output found for ticker '{ticker}'.")
    return ApiWrappedResponse(
        metadata=ApiRunMetadata(
            run_id=rec["run_id"],
            persisted=True,
            engine_version=sws_engine.__version__,
            api_version=settings.api_version,
            data_layer=settings.data_layer,
        ),
        output=rec["output"],
    )


@router.get("/companies/{ticker}/audit")
def latest_company_audit(
    ticker: str,
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    from sws_engine.audit.audit_summary import build_audit_summary

    rec = db.get_latest_company_with_run_id(ticker)
    if not rec:
        raise not_found(f"No persisted company output found for ticker '{ticker}'.")
    # P0.1 computes audit artifacts on demand from the existing validated output.
    # It does not persist new tables and does not alter output_schema.json.
    summary = build_audit_summary(
        rec["output"],
        run_id=rec["run_id"],
        engine_version=sws_engine.__version__,
        output_schema_version="v3.1",
        audit_policies_path=settings.audit_policies_path,
        source_registry_path=settings.source_registry_path,
        identifier_master_path=settings.identifier_master_path,
    )
    return {
        "metadata": {
            "run_id": rec["run_id"],
            "persisted": True,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "audit": summary,
    }


@router.get("/companies/{ticker}/data-confidence")
def latest_company_data_confidence(
    ticker: str,
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    from sws_engine.audit.audit_summary import build_audit_summary

    rec = db.get_latest_company_with_run_id(ticker)
    if not rec:
        raise not_found(f"No persisted company output found for ticker '{ticker}'.")
    summary = build_audit_summary(
        rec["output"],
        run_id=rec["run_id"],
        engine_version=sws_engine.__version__,
        output_schema_version="v3.1",
        audit_policies_path=settings.audit_policies_path,
        source_registry_path=settings.source_registry_path,
        identifier_master_path=settings.identifier_master_path,
    )
    return {
        "metadata": {
            "run_id": rec["run_id"],
            "persisted": True,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "data_confidence": summary.get("data_confidence", {}),
    }


@router.get("/companies/{ticker}/model-applicability")
def latest_company_model_applicability(
    ticker: str,
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    from sws_engine.audit.audit_summary import build_audit_summary

    rec = db.get_latest_company_with_run_id(ticker)
    if not rec:
        raise not_found(f"No persisted company output found for ticker '{ticker}'.")
    summary = build_audit_summary(
        rec["output"],
        run_id=rec["run_id"],
        engine_version=sws_engine.__version__,
        output_schema_version="v3.1",
        audit_policies_path=settings.audit_policies_path,
        source_registry_path=settings.source_registry_path,
        identifier_master_path=settings.identifier_master_path,
    )
    return {
        "metadata": {
            "run_id": rec["run_id"],
            "persisted": True,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "model_applicability": summary.get("model_applicability", {}),
    }


@router.get("/companies/{ticker}/sensitivity")
def latest_company_sensitivity(
    ticker: str,
    settings: Settings = Depends(get_settings),
):
    from sws_engine.sensitivity.report import sensitivity_company_to_files

    try:
        rep = sensitivity_company_to_files(
            "out/api_sensitivity",
            db_path=settings.db_path,
            ticker=ticker,
            assumptions_path=settings.assumptions_path,
            sensitivity_config_path=settings.sensitivity_config_path,
        )
    except FileNotFoundError:
        raise not_found(f"No persisted company input/output found for ticker '{ticker}'.")
    except ValueError as exc:
        raise bad_request(str(exc))
    except Exception as exc:
        raise internal_error(f"Sensitivity analysis failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "run_id": rep["summary"].get("run_id"),
            "persisted": True,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "sensitivity": rep["summary"],
    }


@router.get("/companies/{ticker}/explain")
def latest_company_explain(
    ticker: str,
    mode: str = Query(default="analyst"),
    include_pass: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    from sws_engine.audit.audit_summary import build_audit_summary
    from sws_engine.explain.check_explainer import build_explanation_package

    if mode not in {"analyst", "plain_english"}:
        raise bad_request("mode must be analyst or plain_english")
    rec = db.get_latest_company_with_run_id(ticker)
    if not rec:
        raise not_found(f"No persisted company output found for ticker '{ticker}'.")
    summary = build_audit_summary(
        rec["output"],
        run_id=rec["run_id"],
        engine_version=sws_engine.__version__,
        output_schema_version="v3.1",
        audit_policies_path=settings.audit_policies_path,
        source_registry_path=settings.source_registry_path,
        identifier_master_path=settings.identifier_master_path,
    )
    package = build_explanation_package(
        rec["output"],
        audit_summary=summary,
        mode=mode,
        include_pass=include_pass,
        dictionary_path=settings.reason_code_dictionary_path,
    )
    return {
        "metadata": {
            "run_id": rec["run_id"],
            "persisted": True,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "explanations": package,
    }


@router.get("/companies/{ticker}/business-risks")
def latest_company_business_risks(
    ticker: str,
    settings: Settings = Depends(get_settings),
):
    from sws_engine.audit.audit_summary import build_audit_summary, load_latest_audit_context_from_db
    from sws_engine.audit.risk_signals import build_business_risk_package

    try:
        ctx = load_latest_audit_context_from_db(settings.db_path, ticker)
    except FileNotFoundError:
        raise not_found(f"No persisted company output found for ticker '{ticker}'.")
    try:
        audit = build_audit_summary(
            ctx["output"],
            run_id=ctx["run_id"],
            input_payload=ctx.get("input_payload"),
            assumptions_hash=ctx.get("assumptions_hash"),
            engine_version=ctx.get("engine_version"),
            audit_policies_path=settings.audit_policies_path,
            source_registry_path=settings.source_registry_path,
            identifier_master_path=settings.identifier_master_path,
        )
        package = build_business_risk_package(ctx.get("input_payload"), output=ctx["output"], audit_summary=audit, run_id=ctx["run_id"])
    except Exception as exc:
        raise internal_error(f"Business risk signal generation failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "run_id": ctx["run_id"],
            "persisted": True,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "business_risks": package,
    }


@router.post("/audit/watchlist")
def audit_watchlist_endpoint(
    request: dict = Body(...),
    settings: Settings = Depends(get_settings),
):
    from sws_engine.research.watchlist import audit_watchlist

    rows = request.get("watchlist") or request.get("items") or []
    if not isinstance(rows, list):
        raise bad_request("watchlist must be an array of ticker rows")
    audit_summaries = request.get("audit_summaries") or {}
    business_risks = request.get("business_risks") or {}
    try:
        package = audit_watchlist(rows, audit_summaries=audit_summaries, business_risks=business_risks)
    except Exception as exc:
        raise internal_error(f"Watchlist audit failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "persisted": False,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "watchlist_audit": package,
    }


@router.post("/audit/portfolio")
def audit_portfolio_endpoint(
    request: dict = Body(...),
    settings: Settings = Depends(get_settings),
):
    from sws_engine.audit.portfolio_audit import build_portfolio_audit

    holdings = request.get("holdings") or request.get("items") or []
    if not isinstance(holdings, list):
        raise bad_request("holdings must be an array of portfolio rows")
    try:
        package = build_portfolio_audit(
            holdings,
            audit_summaries=request.get("audit_summaries") or {},
            business_risks=request.get("business_risks") or {},
            thesis_statuses=request.get("thesis_statuses") or {},
            sensitivity_summaries=request.get("sensitivity_summaries") or {},
            portfolio_id=request.get("portfolio_id"),
            valuation_date=request.get("valuation_date"),
        )
    except Exception as exc:
        raise internal_error(f"Portfolio audit failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "persisted": False,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "portfolio_audit": package,
    }


@router.post("/research/thesis/evaluate")
def evaluate_thesis_endpoint(
    request: dict = Body(...),
    settings: Settings = Depends(get_settings),
):
    from sws_engine.research.thesis import evaluate_thesis

    thesis = request.get("thesis") or {}
    if not isinstance(thesis, dict):
        raise bad_request("thesis must be an object")
    try:
        package = evaluate_thesis(
            thesis,
            audit_summary=request.get("audit_summary"),
            business_risk=request.get("business_risk"),
            sensitivity_summary=request.get("sensitivity_summary"),
        )
    except Exception as exc:
        raise internal_error(f"Thesis evaluation failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "persisted": False,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "thesis_status": package,
    }


@router.post("/research/decision")
def decision_journal_endpoint(
    request: dict = Body(...),
    settings: Settings = Depends(get_settings),
):
    from sws_engine.research.journal import build_decision_record

    decision = request.get("decision") or {}
    if not isinstance(decision, dict):
        raise bad_request("decision must be an object")
    try:
        record = build_decision_record(
            decision,
            audit_summary=request.get("audit_summary"),
            thesis_status=request.get("thesis_status"),
        )
    except Exception as exc:
        raise internal_error(f"Decision journal record failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "persisted": False,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "decision_record": record,
    }


@router.post("/research/memo")
def generate_memo_endpoint(
    request: dict = Body(...),
    settings: Settings = Depends(get_settings),
):
    from sws_engine.reporting.investment_memo import build_investment_memo_package

    audit_summary = request.get("audit_summary") or {}
    if not isinstance(audit_summary, dict):
        raise bad_request("audit_summary must be an object")
    try:
        package = build_investment_memo_package(
            audit_summary=audit_summary,
            explanations=request.get("explanations"),
            sensitivity_summary=request.get("sensitivity_summary"),
            business_risk=request.get("business_risk"),
            thesis_status=request.get("thesis_status"),
            decision_record=request.get("decision_record"),
            portfolio_audit=request.get("portfolio_audit"),
            memo_type=request.get("memo_type") or "investment_audit",
            mode=request.get("mode") or "analyst",
        )
    except ValueError as exc:
        raise bad_request(str(exc))
    except Exception as exc:
        raise internal_error(f"Investment memo generation failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "persisted": False,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "investment_memo": package,
    }


@router.post("/research/compare-runs")
def compare_runs_endpoint(
    request: dict = Body(...),
    settings: Settings = Depends(get_settings),
):
    from sws_engine.research.run_comparison import build_run_comparison_package

    previous = request.get("previous") or request.get("previous_run") or {}
    current = request.get("current") or request.get("current_run") or {}
    if not isinstance(previous, dict):
        raise bad_request("previous must be an object")
    if not isinstance(current, dict):
        raise bad_request("current must be an object")
    try:
        package = build_run_comparison_package(
            previous,
            current,
            comparison_id=request.get("comparison_id"),
            artifact_type=request.get("artifact_type") or "audit_summary",
        )
    except Exception as exc:
        raise internal_error(f"Run comparison failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "persisted": False,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "run_comparison": package,
    }




@router.post("/research/workflow-package")
def workflow_package_endpoint(
    request: dict = Body(...),
    settings: Settings = Depends(get_settings),
):
    from sws_engine.research.workflow_package import build_workflow_package

    audit_summary = request.get("audit_summary") or {}
    if not isinstance(audit_summary, dict):
        raise bad_request("audit_summary must be an object")
    try:
        package = build_workflow_package(
            audit_summary=audit_summary,
            explanations=request.get("explanations"),
            sensitivity_summary=request.get("sensitivity_summary"),
            business_risk=request.get("business_risk"),
            thesis_status=request.get("thesis_status"),
            decision_record=request.get("decision_record"),
            portfolio_audit=request.get("portfolio_audit"),
            investment_memo=request.get("investment_memo"),
            run_comparison=request.get("run_comparison"),
            workflow_id=request.get("workflow_id"),
            mode=request.get("mode") or "analyst",
        )
    except ValueError as exc:
        raise bad_request(str(exc))
    except Exception as exc:
        raise internal_error(f"Workflow package generation failed: {exc.__class__.__name__}")
    return {
        "metadata": {
            "persisted": False,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
        },
        "workflow_package": package,
    }


@router.get("/companies/{ticker}/workflow")
def latest_company_workflow_package(
    ticker: str,
    include_optional: bool = Query(default=False),
    settings: Settings = Depends(get_settings),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    from sws_engine.audit.audit_summary import build_audit_summary
    from sws_engine.research.workflow_package import build_workflow_package

    rec = db.get_latest_company_with_run_id(ticker)
    if not rec:
        raise not_found(f"No persisted company output found for ticker '{ticker}'.")
    audit_summary = build_audit_summary(
        rec["output"],
        run_id=rec["run_id"],
        engine_version=sws_engine.__version__,
        output_schema_version="v3.1",
        audit_policies_path=settings.audit_policies_path,
        source_registry_path=settings.source_registry_path,
        identifier_master_path=settings.identifier_master_path,
    )
    package = build_workflow_package(
        audit_summary=audit_summary,
        workflow_id=f"{ticker.upper()}-{rec['run_id']}-workflow",
        mode="analyst",
    )
    return {
        "metadata": {
            "run_id": rec["run_id"],
            "persisted": True,
            "engine_version": sws_engine.__version__,
            "api_version": settings.api_version,
            "data_layer": settings.data_layer,
            "include_optional": include_optional,
        },
        "workflow_package": package,
    }


@router.get("/companies/{ticker}/history", response_model=HistoryResponse)
def company_history(
    ticker: str,
    axis: str | None = Query(default=None),
    from_date: str | None = Query(default=None),
    to_date: str | None = Query(default=None),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    if axis is not None and axis not in AXES:
        raise bad_request(f"axis must be one of {AXES}")
    points = db.get_company_history(ticker, axis=axis, from_date=from_date, to_date=to_date)
    if not points:
        raise not_found(f"No history found for ticker '{ticker}'.")
    return {"ticker": ticker, "axis": axis, "points": points}


@router.get("/companies/{ticker}/checks", response_model=ChecksQueryResponse)
def company_checks(
    ticker: str,
    axis: str | None = Query(default=None),
    result: str | None = Query(default=None),
    reason_code: str | None = Query(default=None),
    latest_only: bool = Query(default=True),
    db: ApiDbAdapter = Depends(get_db_adapter),
):
    if axis is not None and axis not in AXES:
        raise bad_request(f"axis must be one of {AXES}")
    if result is not None and result not in {"PASS", "FAIL", "UNKNOWN"}:
        raise bad_request("result must be PASS, FAIL or UNKNOWN")
    checks = db.get_company_checks(
        ticker,
        axis=axis,
        result=result,
        reason_code=reason_code,
        latest_only=latest_only,
    )
    if not checks:
        raise not_found(f"No checks found for ticker '{ticker}' with supplied filters.")
    return {"ticker": ticker, "latest_only": latest_only, "checks": checks}
