"""sws_public_faithful_manual_inputs: curated/manual inputs, default exact."""
from sws_engine.core.enums import ProviderProfile, SourceQuality
from sws_engine.providers.base import BaseProvider, ProviderResult


class ManualInputsProvider(BaseProvider):
    profile = ProviderProfile.SWS_PUBLIC_FAITHFUL_MANUAL_INPUTS.value

    def prepare(self, payload: dict) -> ProviderResult:
        quality = {
            k: SourceQuality.EXACT.value
            for k, v in payload.items()
            if v is not None and k not in ("lineage", "provider_profile")
        }
        return ProviderResult(payload=payload, field_quality=quality, degradations=[])
