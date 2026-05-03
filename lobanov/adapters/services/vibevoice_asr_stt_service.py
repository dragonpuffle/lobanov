from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast, override
from uuid import uuid4

import aiofiles.os
import torch

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionError, SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger
from lobanov.utils.stt import pick_device_string, resolve_pretrained_source

logger = get_logger(__name__)

_OFFICIAL_VIBEVOICE_ASR_IDS = frozenset(
    {"microsoft/VibeVoice-ASR", "microsoft/vibevoice-asr"},
)


def _resolve_vibevoice_hub_id(original: str) -> str:
    mid = original.strip()
    if mid in _OFFICIAL_VIBEVOICE_ASR_IDS:
        mapped = "microsoft/VibeVoice-ASR-HF"
        logger.info(
            "VibeVoice transformers: mapping Hub id {from_id!r} -> {to_id!r} (non-HF id is for repo/CLI demos).",
            from_id=mid,
            to_id=mapped,
        )
        return mapped
    return mid


def pipeline_torch_dtype(device: str, compute_type: str) -> torch.dtype:
    ct = compute_type.strip().lower()
    if ct in {"float32", "fp32", "int8", "bf16-off"}:
        return torch.float32
    if "bfloat16" in ct or ct in {"bf16", "bfp16"}:
        return torch.bfloat16 if device.startswith("cuda") else torch.float32
    if device.startswith("cuda"):
        return torch.float16
    return torch.float32


def _flatten_processor_decode_output(raw: Any) -> str:  # noqa: C901, PLR0911
    if isinstance(raw, str):
        return " ".join(raw.split())

    candidates: Any = raw
    if isinstance(raw, (list, tuple)) and raw:
        candidates = raw[0]

    if isinstance(candidates, str):
        return " ".join(candidates.split())

    if isinstance(candidates, dict):
        text = candidates.get("Content") or candidates.get("content") or candidates.get("text")
        if isinstance(text, list):
            return _flatten_processor_decode_output(text)
        if isinstance(text, str):
            return " ".join(text.split())
        transcript = candidates.get("transcript") or candidates.get("Transcript")
        if isinstance(transcript, str):
            return " ".join(transcript.split())

    if isinstance(candidates, list):
        parts: list[str] = []
        for item in candidates:
            if isinstance(item, dict):
                content = item.get("Content") or item.get("content") or item.get("text")
                if isinstance(content, str):
                    parts.append(content)
            elif isinstance(item, str):
                parts.append(item)
        return " ".join(" ".join(parts).split())

    return " ".join(str(raw).split())


try:
    from transformers import (
        AutoProcessor,
        VibeVoiceAsrForConditionalGeneration,
    )
except ImportError:
    AutoProcessor = object  # type: ignore[misc, assignment]
    VibeVoiceAsrForConditionalGeneration = None  # type: ignore[misc, assignment]


class VibeVoiceHFSTTService(SpeechRecognitionProtocol):
    """Microsoft VibeVoice ASR via transformers (``microsoft/VibeVoice-ASR-HF``).

    The official standalone inference script targets ``microsoft/VibeVoice-ASR``, while transformers weights publish
    as ``microsoft/VibeVoice-ASR-HF`` — aliases are redirected automatically here.
    """

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._model_lock = asyncio.Lock()
        self._bundle: tuple[Any, Any] | None = None

    def _effective_cfg(self) -> STTConfig:
        mapped = _resolve_vibevoice_hub_id(self._stt.model)
        if mapped.strip() != self._stt.model.strip():
            return self._stt.model_copy(update={"model": mapped})
        return self._stt

    def _load_sync(self) -> tuple[Any, Any]:
        if VibeVoiceAsrForConditionalGeneration is None:
            msg = (
                "transformers is too old or missing `VibeVoiceAsrForConditionalGeneration`; upgrade transformers "
                "to receive the microsoft/VibeVoice-ASR-HF integration."
            )
            raise SpeechRecognitionError(msg)

        cfg = self._effective_cfg()
        source, kwa = resolve_pretrained_source(cfg)

        processor = AutoProcessor.from_pretrained(source, **kwa)
        device_hint = pick_device_string(self._stt.device)
        dtype = pipeline_torch_dtype(device_hint, self._stt.compute_type)

        vv_cls = cast("Any", VibeVoiceAsrForConditionalGeneration)
        if device_hint.startswith("cuda") and torch.cuda.is_available():
            model = vv_cls.from_pretrained(
                source,
                dtype=dtype,
                device_map="auto",
                **kwa,
            )
        else:
            model = vv_cls.from_pretrained(
                source,
                dtype=dtype,
                **kwa,
            ).to("cpu")

        logger.info("Loaded VibeVoice ASR from {src!r}", src=str(source))
        return processor, model

    async def _get_bundle(self) -> tuple[Any, Any]:
        if self._bundle is not None:
            return self._bundle
        async with self._model_lock:
            if self._bundle is None:
                self._bundle = await asyncio.to_thread(self._load_sync)
        return self._bundle

    def _infer_one_sync(self, path: Path, processor: Any, model: Any) -> str:
        request_inputs = processor.apply_transcription_request(
            audio=str(path),
            prompt=None,
        )
        inputs_on_device = request_inputs.to(device=model.device, dtype=model.dtype)

        outputs = model.generate(**inputs_on_device)

        cutoff = inputs_on_device["input_ids"].shape[-1]
        sliced_ids = outputs[:, cutoff:]

        try:
            decoded = processor.decode(sliced_ids, return_format="text")
            return _flatten_processor_decode_output(decoded)
        except Exception:
            decoded = processor.decode(sliced_ids, return_format="parsed")
            return _flatten_processor_decode_output(decoded)

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        _ = language
        path_resolved = await asyncio.to_thread(lambda: Path(file_path).expanduser().resolve())
        if not await aiofiles.os.path.exists(str(path_resolved)):
            vv_miss_msg = f"Audio file not found: {path_resolved}"
            raise SpeechRecognitionError(vv_miss_msg)

        processor, model = await self._get_bundle()
        try:
            text = await asyncio.to_thread(self._infer_one_sync, path_resolved, processor, model)
            return Transcript(
                id=uuid4(),
                session_id=uuid4(),
                audio_record_id=uuid4(),
                text=text,
                language=TranscriptLanguage.RU,
                confidence_score=0.78,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("VibeVoice transcription failed")
            vv_exc_detail = str(e)
            vv_exc_msg = f"VibeVoice: {vv_exc_detail}"
            raise SpeechRecognitionError(vv_exc_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["multi", "en"]
