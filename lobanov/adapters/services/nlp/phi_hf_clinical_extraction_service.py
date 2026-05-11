from __future__ import annotations

from typing import Any

from lobanov.adapters.services.nlp.hf_causal_lm_clinical_extraction_base import HFCausalLMClinicalExtractionService
from lobanov.infra.configs import NLPConfig


class PhiHFClinicalExtractionService(HFCausalLMClinicalExtractionService):
    """Local Phi checkpoint clinical extractor (Phi-3-mini-4k default; override ``nlp.model`` as needed)."""

    model_id_default = "microsoft/Phi-3-mini-4k-instruct"

    def __init__(self, nlp_config: NLPConfig) -> None:
        if not nlp_config.model.strip():
            nlp_config = nlp_config.model_copy(update={"model": self.model_id_default})
        # Built-in modeling avoids brittle Hub remote modules on transformers 5.x.
        nlp_config = nlp_config.model_copy(update={"trust_remote_code": False})
        super().__init__(nlp_config)

    def _extra_load_kwargs(self) -> dict[str, Any]:
        return {}
