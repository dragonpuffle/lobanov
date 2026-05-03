from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, override
from uuid import uuid4

import aiofiles.os
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionError, SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger
from lobanov.utils.stt import language_for_whisper, pick_device_string, resolve_pretrained_source

logger = get_logger(__name__)


class WhisperHFSTTService(SpeechRecognitionProtocol):
    """Local OpenAI Whisper via Hugging Face (e.g. ``openai/whisper-large-v3``, ``...-turbo``)."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._pipe: Any = None
        self._model_lock = asyncio.Lock()

    def _load_sync(self) -> Any:
        source, from_pretrained_kw = resolve_pretrained_source(self._stt)
        device = pick_device_string(self._stt.device)
        dtype = torch.float16 if device.startswith("cuda") else torch.float32

        model = AutoModelForSpeechSeq2Seq.from_pretrained(
            source,
            dtype=dtype,
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
            dtype=dtype,
            device=pipeline_device,
        )

    async def _get_pipe(self) -> Any:
        if self._pipe is not None:
            return self._pipe
        async with self._model_lock:
            if self._pipe is None:
                self._pipe = await asyncio.to_thread(self._load_sync)
        return self._pipe

    def _whisper_generate_kwargs(self, language: str) -> dict[str, Any]:
        return {
            "task": "transcribe",
            "language": language_for_whisper(language),
        }

    async def _run_whisper_pipe(self, path: str, gen_kw: dict[str, Any]) -> dict[str, Any]:
        pipe = await self._get_pipe()
        out = await asyncio.to_thread(
            lambda: pipe(path, return_timestamps=True, generate_kwargs=dict(gen_kw)),
        )
        if not isinstance(out, dict):
            whisper_msg_type = f"Unexpected Whisper ASR output type: {type(out).__name__}"
            raise SpeechRecognitionError(whisper_msg_type)
        return out

    async def _execute_whisper(self, path_resolved: str, language: str) -> dict[str, Any]:
        return await self._run_whisper_pipe(path_resolved, self._whisper_generate_kwargs(language))

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        path_resolved = await asyncio.to_thread(lambda: str(Path(file_path).expanduser().resolve()))
        if not await aiofiles.os.path.exists(path_resolved):
            whisper_err_missing = f"Audio file not found: {path_resolved}"
            raise SpeechRecognitionError(whisper_err_missing)

        try:
            out = await self._execute_whisper(path_resolved, language)
            text = str(out.get("text", "") or "").strip()
            if not text:
                chunks = out.get("chunks")
                if isinstance(chunks, list):
                    parts = [str(c["text"]) for c in chunks if isinstance(c, dict) and c.get("text")]
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
            logger.exception("Whisper HF transcription failed")
            whisper_err_detail = str(e)
            whisper_err_msg = f"Whisper HF: {whisper_err_detail}"
            raise SpeechRecognitionError(whisper_err_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["ru-RU", "ru"]
