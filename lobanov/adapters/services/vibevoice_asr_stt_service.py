"""Microsoft VibeVoice ASR via ``VibeVoiceAsrForConditionalGeneration`` (Transformers HF release)."""

from __future__ import annotations

import asyncio
from typing import Any, override

import aiofiles.os
import torch

import lobanov.adapters.services.hf_stt_utils as _hf_stt_utils_side_effects  # noqa: F401
from lobanov.adapters.services.hf_stt_utils import (
    build_transcript_from_text,
    ensure_hf_snapshot,
    resolve_audio_path_str,
    torch_dtype_from_stt_config,
)
from lobanov.domain.entities.transcript import Transcript
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


def _decode_parsed_segments(parsed: Any) -> str | None:
    if not isinstance(parsed, list):
        return None
    parts: list[str] = []
    for seg in parsed:
        if not isinstance(seg, dict):
            continue
        content = seg.get("Content") or seg.get("content") or seg.get("text")
        if isinstance(content, str) and content.strip():
            parts.append(content.strip())
    return " ".join(parts).strip() or None


def _first_decode_candidate(first: Any) -> str | None:
    if isinstance(first, str) and first.strip():
        return first.strip()
    glued = _decode_parsed_segments(first)
    if glued:
        return glued
    if isinstance(first, dict):
        txt = first.get("text") or first.get("Content") or first.get("content") or ""
        if isinstance(txt, str) and txt.strip():
            return txt.strip()
    return None


def _decode_generation(processor: Any, generated_ids: Any) -> str:
    decode_fn = getattr(processor, "decode", None)
    if decode_fn is None:
        msg = "VibeVoice processor has no decode"
        raise SpeechRecognitionError(msg)

    for fmt in ("parsed", "text"):
        try:
            out = decode_fn(generated_ids, return_format=fmt)
        except TypeError:
            out = decode_fn(generated_ids)

        first = out[0] if isinstance(out, list) and out else out
        candidate = _first_decode_candidate(first)
        if candidate:
            return candidate

    detail = "VibeVoice decode returned unrecognized structure"
    raise SpeechRecognitionError(detail)


class VibeVoiceASRSTTService(SpeechRecognitionProtocol):
    """Use ``microsoft/VibeVoice-ASR-HF`` (Transformers-native); CLI/demo often uses ``microsoft/VibeVoice-ASR``."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._model: Any = None
        self._processor: Any = None
        self._model_lock = asyncio.Lock()

    def _load_model_sync(self) -> None:
        model_id = self._stt.model.strip()
        if model_id == "microsoft/VibeVoice-ASR":
            msg = (
                "For Python Transformers set stt.model to 'microsoft/VibeVoice-ASR-HF'. "
                "See https://github.com/microsoft/VibeVoice and HF microsoft/VibeVoice-ASR-HF"
            )
            logger.warning("{msg}", msg=msg)

        local_dir = str(ensure_hf_snapshot(self._stt))
        logger.info("Loading VibeVoice ASR from {dir!r}", dir=local_dir)

        dtype = torch_dtype_from_stt_config(self._stt, default=torch.float16)

        try:
            from transformers import AutoProcessor, VibeVoiceAsrForConditionalGeneration  # noqa: PLC0415
        except ImportError as e:
            detail = (
                "This environment's Transformers does not expose VibeVoiceAsrForConditionalGeneration; "
                "upgrade Transformers per https://github.com/microsoft/VibeVoice (ASR HF release)."
            )
            raise SpeechRecognitionError(detail) from e

        self._processor = AutoProcessor.from_pretrained(local_dir)
        self._model = VibeVoiceAsrForConditionalGeneration.from_pretrained(
            local_dir,
            device_map="auto",
            torch_dtype=dtype,
        )

    async def _get_model_stack(self) -> tuple[Any, Any]:
        if self._model is not None and self._processor is not None:
            return self._model, self._processor
        async with self._model_lock:
            if self._model is not None and self._processor is not None:
                return self._model, self._processor
            await asyncio.to_thread(self._load_model_sync)
        return self._model, self._processor

    def _infer_sync(self, audio_path: str) -> str:
        model = self._model
        processor = self._processor
        if model is None or processor is None:
            msg = "VibeVoice ASR model not loaded"
            raise SpeechRecognitionError(msg)

        prompt = self._stt.initial_prompt.strip() or None

        apply_fn = getattr(processor, "apply_transcription_request", None)
        if apply_fn is None:
            detail = (
                "VibeVoice HF processor lacks apply_transcription_request; upgrade Transformers from "
                "https://github.com/microsoft/VibeVoice"
            )
            raise SpeechRecognitionError(detail)

        inputs = apply_fn(audio=audio_path, prompt=prompt)

        tgt_device = getattr(model, "device", None)
        tgt_dtype = getattr(model, "dtype", None)

        if tgt_device is not None:
            inputs = inputs.to(device=tgt_device, dtype=tgt_dtype) if tgt_dtype is not None else inputs.to(tgt_device)
        elif tgt_dtype is not None:
            inputs = inputs.to(dtype=tgt_dtype)

        output_ids = model.generate(**inputs)
        inp_len = inputs["input_ids"].shape[-1]
        generated = output_ids[:, inp_len:]

        return _decode_generation(processor, generated)

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        del language
        path_str = await asyncio.to_thread(resolve_audio_path_str, file_path)
        if not await aiofiles.os.path.exists(path_str):
            err_msg = f"Audio file not found: {path_str}"
            raise SpeechRecognitionError(err_msg)

        try:
            await self._get_model_stack()
            text = await asyncio.to_thread(self._infer_sync, path_str)
            return build_transcript_from_text(text)
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("Failed to transcribe audio with VibeVoice ASR")
            msg = f"Failed to transcribe audio with VibeVoice ASR: {e}"
            raise SpeechRecognitionError(msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["multi", "ru-RU", "ru"]
