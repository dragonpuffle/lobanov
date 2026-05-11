"""Qwen3 dense causal-LM adapter for local clinical extraction.

Default: ``Qwen/Qwen3-0.6B``. Model card:
https://huggingface.co/Qwen/Qwen3-0.6B

Uses ``apply_chat_template(..., enable_thinking=False)`` so JSON extraction is not wrapped in
thinking blocks. Loads on a single device (no ``device_map`` in this adapter).
"""

from __future__ import annotations

from typing import Any, override

from lobanov.adapters.services.nlp.hf_causal_lm_clinical_extraction_base import HFCausalLMClinicalExtractionService
from lobanov.infra.configs import NLPConfig


class Qwen3HFClinicalExtractionService(HFCausalLMClinicalExtractionService):
    """Local Qwen3 checkpoint clinical extractor via Hugging Face Transformers."""

    model_id_default = "Qwen/Qwen3-0.6B"

    def __init__(self, nlp_config: NLPConfig) -> None:
        if not nlp_config.model.strip():
            nlp_config = nlp_config.model_copy(update={"model": self.model_id_default})
        nlp_config = nlp_config.model_copy(update={"trust_remote_code": False})
        super().__init__(nlp_config)

    def _extra_load_kwargs(self) -> dict[str, Any]:
        return {}

    @override
    def _encode_messages_for_generation(
        self,
        tokenizer: Any,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        if not getattr(tokenizer, "chat_template", None):
            return super()._encode_messages_for_generation(tokenizer, messages)
        try:
            enc: Any = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
                enable_thinking=False,
            )
        except TypeError:
            enc = tokenizer.apply_chat_template(
                messages,
                add_generation_prompt=True,
                tokenize=True,
                return_dict=True,
                return_tensors="pt",
            )
        return dict(enc)
