from __future__ import annotations

from pathlib import Path
from typing import Any, cast, override

from lobanov.adapters.services.nlp.hf_causal_lm_clinical_extraction_base import (
    HFCausalLMClinicalExtractionService,
    _ensure_transformers_loss_kwargs_compat,
)
from lobanov.infra.configs import NLPConfig
from lobanov.utils.llm import pick_device_string, pick_torch_dtype, resolve_pretrained_source, safe_hf_dirname
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class Gemma4E2BHFClinicalExtractionService(HFCausalLMClinicalExtractionService):
    """Clinical extractor for ``google/gemma-4-E2B`` (ImageTextToText + processor)."""

    model_id_default = "google/gemma-4-E2B"

    def __init__(self, nlp_config: NLPConfig) -> None:
        nlp_config = nlp_config.model_copy(update={"trust_remote_code": True})
        super().__init__(nlp_config)

    @staticmethod
    def _effective_context_length(model: Any, tokenizer: Any) -> int:
        inner = getattr(tokenizer, "tokenizer", tokenizer)
        return HFCausalLMClinicalExtractionService.effective_context_length(model, inner)

    @override
    def _load_sync(self) -> tuple[Any, Any]:
        _ensure_transformers_loss_kwargs_compat()
        from transformers import AutoModelForImageTextToText, AutoProcessor  # noqa: PLC0415

        source, hub_kw = resolve_pretrained_source(self._nlp)
        device_str = pick_device_string(self._nlp.device)
        dtype = pick_torch_dtype(self._nlp.compute_type, device_str)
        trust = self._nlp.trust_remote_code

        processor = AutoProcessor.from_pretrained(
            source,
            trust_remote_code=trust,
            **hub_kw,
        )

        extra = self._extra_load_kwargs()
        load_kw: dict[str, Any] = {
            "trust_remote_code": trust,
            **hub_kw,
            **extra,
        }
        if "dtype" not in load_kw:
            load_kw["dtype"] = dtype

        uses_device_map = "device_map" in load_kw
        if uses_device_map and "offload_folder" not in load_kw:
            cache_root = Path(hub_kw.get("cache_dir") or self._nlp.model_cache_dir).expanduser().resolve()
            offload = cache_root / "accelerate-offload" / safe_hf_dirname(self._nlp.model)
            offload.mkdir(parents=True, exist_ok=True)
            load_kw["offload_folder"] = str(offload)

        model = AutoModelForImageTextToText.from_pretrained(source, **load_kw)

        if not uses_device_map and device_str not in {"auto", "cpu"}:
            model = cast("Any", model).to(device_str)

        self._after_model_loaded(processor, model, str(source), hub_kw)

        logger.info(
            "Loaded Gemma4 E2B ImageTextToText {src!r} device={dev!r} dtype={dt}",
            src=str(source),
            dev=device_str,
            dt=str(dtype),
        )
        return processor, model

    def _pad_token_id_for_generate(self, tokenizer: Any) -> int | None:
        tok = getattr(tokenizer, "tokenizer", tokenizer)
        eos = getattr(tok, "eos_token_id", None)
        pad = getattr(tok, "pad_token_id", None)
        if eos is not None:
            return int(eos)
        return int(pad) if pad is not None else None

    @override
    def _encode_messages_for_generation(
        self,
        tokenizer: Any,
        messages: list[dict[str, str]],
    ) -> dict[str, Any]:
        proc = tokenizer
        # Gemma4Processor.apply_chat_template raises: chat_template is on proc.tokenizer, not the processor.
        inner = getattr(proc, "tokenizer", proc)
        if getattr(inner, "chat_template", None):
            try:
                enc: Any = inner.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                    enable_thinking=False,
                )
            except TypeError:
                enc = inner.apply_chat_template(
                    messages,
                    add_generation_prompt=True,
                    tokenize=True,
                    return_dict=True,
                    return_tensors="pt",
                )
            return dict(enc)
        return super()._encode_messages_for_generation(inner, messages)

    def _decode_continuation_ids(self, tokenizer: Any, token_ids: Any) -> str:
        return tokenizer.decode(token_ids, skip_special_tokens=True)
