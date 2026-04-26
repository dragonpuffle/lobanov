import asyncio
from datetime import UTC, datetime
from math import exp
from typing import override
from uuid import uuid4

import aiofiles.os
from faster_whisper import WhisperModel

from lobanov.domain.entities.transcript import Transcript, TranscriptLanguage
from lobanov.infra.configs import STTConfig
from lobanov.protocols import SpeechRecognitionProtocol
from lobanov.utils.logging import get_logger

logger = get_logger(__name__)


class SpeechRecognitionError(Exception):
    pass


class WhisperSTTService(SpeechRecognitionProtocol):
    def __init__(self, stt_config: STTConfig):
        self._stt = stt_config
        prompt = stt_config.initial_prompt.strip()
        self.initial_prompt: str | None = prompt or None
        self._model: WhisperModel | None = None
        self._model_lock = asyncio.Lock()

    async def _get_model(self) -> WhisperModel:
        if self._model is not None:
            return self._model
        async with self._model_lock:
            if self._model is not None:
                return self._model
            logger.info(
                "Loading Whisper model {model!r} (device={device!r}); first run may download weights",
                model=self._stt.model,
                device=self._stt.device,
            )
            self._model = await asyncio.to_thread(
                WhisperModel,
                self._stt.model,
                device=self._stt.device,
                compute_type=self._stt.compute_type,
            )
        return self._model

    def _parse_language(self, language: str) -> str:
        language_map = {
            "ru-RU": "ru",
            "ru": "ru",
        }
        return language_map.get(language, language[:2])

    async def _transcribe(self, file_path: str, whisper_language: str):
        kwargs: dict[str, object] = {
            "language": whisper_language,
            "beam_size": self._stt.beam_size,
            "vad_filter": self._stt.vad_filter,
            "word_timestamps": self._stt.word_timestamps,
            "temperature": self._stt.temperature,
            "condition_on_previous_text": self._stt.condition_on_previous_text,
        }
        if self._stt.no_speech_threshold is not None:
            kwargs["no_speech_threshold"] = self._stt.no_speech_threshold

        if self.initial_prompt:
            kwargs["initial_prompt"] = self.initial_prompt

        model = await self._get_model()
        return await asyncio.to_thread(model.transcribe, file_path, **kwargs)

    @override
    async def transcribe_audio(self, file_path: str, language: str) -> Transcript:
        if not await aiofiles.os.path.exists(file_path):
            err_msg = f"Audio file not found: {file_path}"
            raise SpeechRecognitionError(err_msg)

        try:
            whisper_language = self._parse_language(language)
            segments, _ = await self._transcribe(file_path, whisper_language)
            # faster-whisper returns a generator; we need a list for len() and multiple passes
            segments = list(segments)

            full_text = "".join([segment.text for segment in segments])
            full_text = " ".join(full_text.split())
            full_text = full_text.strip()

            avg_probability = 0.0
            confidence_score = 0.0
            if segments:
                probabilities = [max(min(exp(segment.avg_logprob), 1.0), 0.0) for segment in segments]
                avg_probability = sum(probabilities) / len(probabilities)
                confidence_score = min(max(avg_probability, 0.0), 1.0)

            transcript_language = TranscriptLanguage.RU if whisper_language == "ru" else TranscriptLanguage.RU  # noqa: RUF034

            return Transcript(
                id=uuid4(),
                session_id=uuid4(),
                audio_record_id=uuid4(),
                text=full_text,
                language=transcript_language,
                confidence_score=confidence_score,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
        except Exception as e:
            logger.exception("Failed to transcribe audio")
            err_msg = f"Failed to transcribe audio: {e}"
            raise SpeechRecognitionError(err_msg) from e

    @override
    async def get_supported_languages(self) -> list[str]:
        return [
            "ru-RU",
            "ru",
        ]
