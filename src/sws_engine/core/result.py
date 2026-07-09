"""CheckResult contract: every one of the 30 checks must return exactly
these fields (check_engine_contract.md / SPEC v3.1 section 5)."""
from dataclasses import dataclass, field
from typing import Any, Union

from sws_engine.core.enums import (
    Axis, CheckResultValue, ReasonCode, SourceClass, SourceQuality,
)

CONTRACT_FIELDS = (
    "axis", "id", "name", "result", "reason_code",
    "source_quality", "source_class", "inputs", "threshold", "input_lineage",
)


@dataclass
class CheckResult:
    axis: str
    id: Union[int, str]
    name: str
    result: str
    reason_code: str
    source_quality: str
    source_class: str
    inputs: dict = field(default_factory=dict)
    threshold: str = ""
    input_lineage: dict = field(default_factory=dict)

    def __post_init__(self):
        # coerce enums to raw values and validate against closed sets
        self.axis = Axis(self.axis).value
        self.result = CheckResultValue(self.result).value
        self.reason_code = ReasonCode(self.reason_code).value
        self.source_quality = SourceQuality(self.source_quality).value
        self.source_class = SourceClass(self.source_class).value

    def to_dict(self) -> dict:
        return {
            "axis": self.axis,
            "id": self.id,
            "name": self.name,
            "result": self.result,
            "reason_code": self.reason_code,
            "source_quality": self.source_quality,
            "source_class": self.source_class,
            "inputs": _jsonable(self.inputs),
            "threshold": self.threshold,
            "input_lineage": self.input_lineage,
        }


def _jsonable(d: dict) -> dict:
    out = {}
    for k, v in d.items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            out[k] = v
        elif isinstance(v, (list, tuple)):
            out[k] = list(v)
        elif isinstance(v, dict):
            out[k] = _jsonable(v)
        else:
            out[k] = str(v)
    return out


def unknown_check(axis, id, name, reason_code, inputs=None, threshold="",
                  input_lineage=None, source_quality=SourceQuality.MISSING,
                  source_class=SourceClass.E0) -> CheckResult:
    """Helper mandated by the implementation brief: UNKNOWN with full contract."""
    return CheckResult(
        axis=axis, id=id, name=name,
        result=CheckResultValue.UNKNOWN,
        reason_code=reason_code,
        source_quality=source_quality,
        source_class=source_class,
        inputs=inputs or {},
        threshold=threshold,
        input_lineage=input_lineage or {},
    )
