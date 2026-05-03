"""Whisper-large-v3 and Whisper-large-v3-turbo via Transformers ``pipeline``."""

from __future__ import annotations

import asyncio
from typing import Any, override

import aiofiles.os
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

import lobanov.adapters.services.hf_stt_utils as _hf_stt_utils_side_effects  # noqa: F401
from lobanov.adapters.services.hf_stt_utils import (
    build_transcript_from_text,
    ensure_hf_snapshot,
    pipeline_device_number,
    resolve_audio_path_str,
    torch_dtype_from_stt_config,
    whisper_parse_language,
)
from lobanov.domain.entities.transcript import Transcript
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


class WhisperHFSTTService(SpeechRecognitionProtocol):
    """Hugging Face Whisper via ``automatic-speech-recognition`` pipeline (e.g. openai/whisper-large-v3[-turbo])."""

    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        self._model: Any = None
        self._processor: Any = None
        self._pipeline: Any = None
        self._model_lock = asyncio.Lock()

    def _load_model_sync(self) -> None:
        local_dir = str(ensure_hf_snapshot(self._stt))
        logger.info(
            "Loading Whisper HF STT model {model!r} from {dir!r}",
            model=self._stt.model,
            dir=local_dir,
        )
        dtype = torch_dtype_from_stt_config(self._stt)

        self._processor = AutoProcessor.from_pretrained(local_dir)
        self._model = AutoModelForSpeechSeq2Seq.from_pretrained(
            local_dir,
            dtype=dtype,
            low_cpu_mem_usage=True,
            use_safetensors=True,
        )

        requested_device = self._stt.device.lower().strip()
        use_cuda = requested_device.startswith("cuda") and torch.cuda.is_available()
        if use_cuda:
            self._model = self._model.to(self._stt.device)
        elif requested_device.startswith("cuda"):
            logger.warning("CUDA requested but unavailable; Whisper HF STT falls back to CPU")

        self._apply_whisper_generation_config_safety()

        device = pipeline_device_number(self._stt.device)
        self._pipeline = pipeline(
            "automatic-speech-recognition",
            model=self._model,
            tokenizer=self._processor.tokenizer,
            feature_extractor=self._processor.feature_extractor,
            dtype=dtype,
            device=device,
        )

    def _apply_whisper_generation_config_safety(self) -> None:
        if self._model is None:
            return
        gc = self._model.generation_config
        gc.logprob_threshold = None
        gc.no_speech_threshold = None

    async def _get_pipeline(self) -> Any:
        if self._pipeline is not None:
            return self._pipeline
        async with self._model_lock:
            if self._pipeline is not None:
                return self._pipeline
            await asyncio.to_thread(self._load_model_sync)
        return self._pipeline

    def _generate_kwargs(self, language: str) -> dict[str, Any]:
        return {
            "task": "transcribe",
            "language": whisper_parse_language(language),
            "num_beams": max(1, self._stt.beam_size),
            "temperature": self._stt.temperature,
            "condition_on_prev_tokens": self._stt.condition_on_previous_text,
        }

    def _return_timestamps_arg(self) -> bool | str:
        if self._stt.word_timestamps:
            return "word"
        return False

    async def _transcribe(self, file_path: str, language: str) -> str:
        asr = await self._get_pipeline()
        result = await asyncio.to_thread(
            asr,
            file_path,
            generate_kwargs=self._generate_kwargs(language),
            return_timestamps=self._return_timestamps_arg(),
        )
        if isinstance(result, dict):
            text = result.get("text", "")
            if isinstance(text, str):
                return text
        msg = f"Unexpected Whisper HF STT result: {type(result).__name__}"
        raise SpeechRecognitionError(msg)

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        path_str = await asyncio.to_thread(resolve_audio_path_str, file_path)
        if not await aiofiles.os.path.exists(path_str):
            err_msg = f"Audio file not found: {path_str}"
            raise SpeechRecognitionError(err_msg)

        try:
            text = await self._transcribe(path_str, language)
            return build_transcript_from_text(text)
        except SpeechRecognitionError:
            raise
        except Exception as e:
            logger.exception("Failed to transcribe audio with Whisper HF")
            err_msg = f"Failed to transcribe audio with Whisper HF: {e}"
            raise SpeechRecognitionError(err_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return ["ru-RU", "ru", "en", "en-US"]
