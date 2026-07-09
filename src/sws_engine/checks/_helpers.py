"""Shared helpers for check implementations."""
from sws_engine.contracts.input_contract import get_num
from sws_engine.contracts.lineage import field_lineage
from sws_engine.core.enums import (
    CheckResultValue, ReasonCode, SourceClass, SourceQuality,
)
from sws_engine.core.result import CheckResult, unknown_check


def quality_for(ctx, *fields):
    """Worst-case source_quality over the fields involved in a check."""
    order = ["exact", "approximation", "assumption", "missing"]
    worst = "exact"
    for f in fields:
        q = ctx.field_quality.get(f, "exact" if ctx.payload.get(f) is not None else "missing")
        if order.index(q) > order.index(worst):
            worst = q
    return worst


class CheckContext:
    def __init__(self, payload, assumptions, field_quality):
        self.payload = payload
        self.assumptions = assumptions
        self.field_quality = field_quality

    def num(self, field):
        return get_num(self.payload, field)

    def nested_num(self, container, key):
        c = self.payload.get(container) or {}
        v = c.get(key)
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None

    def lineage(self, *fields):
        return field_lineage(self.payload, *fields)


def binary_check(ctx, *, axis, id, name, condition_inputs, lineage_fields,
                 threshold, passes, source_class=SourceClass.E0,
                 quality_fields=None):
    """Generic PASS/FAIL/UNKNOWN check: UNKNOWN if any input is None."""
    if any(v is None for v in condition_inputs.values()):
        return unknown_check(
            axis=axis, id=id, name=name,
            reason_code=ReasonCode.MISSING_INPUT,
            inputs=condition_inputs, threshold=threshold,
            input_lineage=ctx.lineage(*lineage_fields),
            source_class=source_class,
        )
    result = CheckResultValue.PASS if passes else CheckResultValue.FAIL
    sq = quality_for(ctx, *(quality_fields or condition_inputs.keys()))
    return CheckResult(
        axis=axis, id=id, name=name, result=result,
        reason_code=ReasonCode.OK,
        source_quality=sq, source_class=source_class,
        inputs=condition_inputs, threshold=threshold,
        input_lineage=ctx.lineage(*lineage_fields),
    )
