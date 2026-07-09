"""Provider profile base: providers annotate the payload with per-field
source_quality and produce degradation notes; they never invent values."""
from dataclasses import dataclass, field


@dataclass
class ProviderResult:
    payload: dict
    field_quality: dict = field(default_factory=dict)   # field -> source_quality
    degradations: list = field(default_factory=list)    # human-readable warnings


class BaseProvider:
    profile = None

    def prepare(self, payload: dict) -> ProviderResult:  # pragma: no cover
        raise NotImplementedError
