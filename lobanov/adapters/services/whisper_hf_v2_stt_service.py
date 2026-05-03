"""Minimal Hugging Face Whisper: load model + transcribe local file path (HF card-style, no extras)."""

from __future__ import annotations

import asyncio
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override
from uuid import uuid4

import aiofiles.os
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


def _safe_hf_dirname(model_id: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "--", model_id).strip(".- ") or "model"


def _safe_revision_dirname(revision: str) -> str:
    raw = revision.strip() or "default"
    return re.sub(r'[<>:"/\\|?*]', "_", raw) or "default"


def _dir_has_model_weights(path: Path) -> bool:
    if not path.is_dir():
        return False
    if not (path / "config.json").is_file():
        return False
    return bool(
        (path / "model.safetensors").is_file()
        or (path / "pytorch_model.bin").is_file()
        or (path / "model.safetensors.index.json").is_file()
        or (path / "pytorch_model.bin.index.json").is_file()
        or bool(list(path.glob("*.safetensors")))
    )


def _project_snapshot_dir(stt: STTConfig) -> Path:
    """Same layout as ``snapshot_download(..., local_dir=...)`` / other STT adapters."""
    root = Path(stt.model_cache_dir).expanduser().resolve()
    return root / _safe_hf_dirname(stt.model) / _safe_revision_dirname(stt.revision)


def _resolve_pretrained_source(stt: STTConfig) -> tuple[str, dict[str, Any]]:
    """Prefer on-disk folder over Hub: explicit path, then project snapshot dir, else repo id + cache_dir."""
    model_id = stt.model.strip()
    explicit = Path(model_id).expanduser().resolve()
    if _dir_has_model_weights(explicit):
        logger.info("Whisper HF v2: load from explicit local dir {p!r}", p=str(explicit))
        return str(explicit), {}

    snap = _project_snapshot_dir(stt)
    if _dir_has_model_weights(snap):
        logger.info("Whisper HF v2: load from snapshot {p!r}", p=str(snap))
        return str(snap), {}

    legacy_flat = Path(stt.model_cache_dir).expanduser().resolve() / _safe_hf_dirname(stt.model)
    if _dir_has_model_weights(legacy_flat):
        logger.info("Whisper HF v2: load from legacy cache dir {p!r}", p=str(legacy_flat))
        return str(legacy_flat), {}

    cache_dir = str(Path(stt.model_cache_dir).expanduser().resolve())
    hub_kw: dict[str, Any] = {"cache_dir": cache_dir}
    if stt.revision.strip():
        hub_kw["revision"] = stt.revision.strip()
    logger.info("Whisper HF v2: load from Hub {model!r} cache_dir={c!r}", model=model_id, c=cache_dir)
    return model_id, hub_kw


def _pick_device_string(stt_device: str) -> str:
    if stt_device.lower().strip().startswith("cuda") and torch.cuda.is_available():
        return stt_device if ":" in stt_device else "cuda:0"
    return "cpu"


def _language_for_whisper(language: str) -> str:
    return {"ru": "russian", "ru-RU": "russian"}.get(language, language[:2] if language else "russian")


class WhisperHFV2STTService(SpeechRecognitionProtocol):
    """Whisper via ``pipeline`` as in the HF model card; no custom generation_config or shared STT utils."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._pipe: Any = None
        self._model_lock = asyncio.Lock()

    def _load_sync(self) -> Any:
        source, from_pretrained_kw = _resolve_pretrained_source(self._stt)
        device = _pick_device_string(self._stt.device)
        torch_dtype = torch.float16 if device.startswith("cuda") else torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            source,
            torch_dtype=torch_dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
            **from_pretrained_kw,
        )
        model.to(device)

        processor = AutoProcessor.from_pretrained(source, **from_pretrained_kw)

        if device.startswith("cuda"):
            gpu = 0
            if ":" in device:
                try:
                    gpu = int(device.rsplit(":", maxsplit=1)[1])
                except ValueError:
                    gpu = 0
            pipeline_device: int = gpu
        else:
            pipeline_device = -1

        return pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            torch_dtype=torch_dtype,
            device=pipeline_device,
        )

    async def _get_pipe(self) -> Any:
        if self._pipe is not None:
            return self._pipe
        async with self._model_lock:
            if self._pipe is None:
                self._pipe = await asyncio.to_thread(self._load_sync)
        return self._pipe

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        path_resolved = await asyncio.to_thread(lambda: str(Path(file_path).expanduser().resolve()))
        if not await aiofiles.os.path.exists(path_resolved):
            err_msg = f"Audio file not found: {path_resolved}"
            raise SpeechRecognitionError(err_msg)

        try:
            pipe = await self._get_pipe()
            gen_kw: dict[str, Any] = {
                "task": "transcribe",
                "language": _language_for_whisper(language),
            }
            # Long-form (>~30 s) Whisper requires timestamp tokens in generate(); see transformers WhisperGenerationMixin.
            out = await asyncio.to_thread(
                lambda: pipe(path_resolved, return_timestamps=True, generate_kwargs=gen_kw),
            )
            if not isinstance(out, dict):
                msg = f"Unexpected Whisper v2 output: {type(out).__name__}"
                raise SpeechRecognitionError(msg)
            text = str(out.get("text", "") or "").strip()
            if not text:
                chunks = out.get("chunks")
                if isinstance(chunks, list):
                    parts = [
                        str(c["text"])
                        for c in chunks
                        if isinstance(c, dict) and c.get("text")
                    ]
                    text = "".join(parts).strip()
            text = " ".join(text.split())

            return Transcript(
                id=uuid4(),
                session_id=uuid4(),
                audio_record_id=uuid4(),
                text=text,
                language=TranscriptLanguage.RU,
                confidence_score=0.8,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("Whisper HF v2 transcription failed")
            err_msg = f"Whisper HF v2: {e}"
            raise SpeechRecognitionError(err_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["ru-RU", "ru"]
